"""M4 keyword expansion orchestration."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TypedDict

from src.clients.dataforseo.types import APIResponse
from src.config.constants import (
    DFS_DEFAULT_LOCATION_NAME,
    M4_ALLOWED_AIO_RISK,
    M4_ALLOWED_CONFIDENCE,
    M4_ALLOWED_INTENTS,
    M4_ALLOWED_SOURCES,
    M4_ALLOWED_TIERS,
    M4_CONFIDENCE_HIGH_THRESHOLD,
    M4_CONFIDENCE_LOW_THRESHOLD,
    M4_INTENT_PRIORITY,
    M4_INTERACTIVE_TIMEOUT_SECONDS,
    M4_MAX_KEYWORDS,
)

from .intent_classifier import (
    aio_risk_for_intent,
    infer_intent_from_rules,
    is_actionable_intent,
)
from .keyword_deduplication import CandidateKeyword, dedupe_candidate_keywords, normalize_keyword

logger = logging.getLogger(__name__)


class ExpandedKeyword(TypedDict):
    """Public contract for one expanded keyword row."""

    keyword: str
    tier: int
    intent: str
    source: str
    aio_risk: str
    actionable: bool


class KeywordExpansion(TypedDict):
    """Public M4 output contract consumed by downstream modules."""

    niche: str
    expanded_keywords: list[ExpandedKeyword]
    total_keywords: int
    actionable_keywords: int
    informational_keywords_excluded: int
    expansion_confidence: str


def _extract_dfs_keywords(response: APIResponse) -> list[str]:
    """Extract keyword strings from DataForSEO keyword suggestions payload."""
    if response.status != "ok" or response.data is None:
        return []

    keywords: list[str] = []
    if not isinstance(response.data, list):
        return keywords

    for block in response.data:
        if not isinstance(block, dict):
            continue
        items = block.get("items", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            keyword = item.get("keyword")
            if isinstance(keyword, str) and keyword.strip():
                keywords.append(keyword)
    return keywords


def _confidence_from_overlap(
    llm_terms: set[str],
    dfs_terms: set[str],
    *,
    llm_success: bool,
    dfs_success: bool,
) -> str:
    """Map source overlap to confidence buckets."""
    if not llm_success or not dfs_success:
        return "low"
    if not llm_terms:
        return "low"

    overlap = len(llm_terms & dfs_terms) / len(llm_terms)
    if overlap < M4_CONFIDENCE_LOW_THRESHOLD:
        return "low"
    if overlap < M4_CONFIDENCE_HIGH_THRESHOLD:
        return "medium"
    return "high"


def _infer_tier(keyword: str, niche: str) -> int:
    """Deterministically infer a tier when no explicit tier exists."""
    normalized = normalize_keyword(keyword)
    niche_norm = normalize_keyword(niche)
    if normalized == niche_norm or "near me" in normalized:
        return 1

    tier_2_hints = ("emergency", "repair", "services", "service", "installation", "install")
    if any(hint in normalized for hint in tier_2_hints):
        return 2
    return 3


async def _load_llm_candidates(
    niche: str,
    llm_client: object | None,
) -> tuple[list[CandidateKeyword], bool, int]:
    """Load and normalize the structured LLM expansion source."""
    started = time.monotonic()
    candidates: list[CandidateKeyword] = []
    if llm_client is None or not hasattr(llm_client, "keyword_expansion"):
        return candidates, False, 0

    try:
        result = await llm_client.keyword_expansion(niche)
        data = getattr(result, "data", None)
        if not getattr(result, "success", False) or not isinstance(data, dict):
            return candidates, False, int((time.monotonic() - started) * 1000)

        raw_keywords = data.get("expanded_keywords", [])
        if isinstance(raw_keywords, list):
            for item in raw_keywords:
                if not isinstance(item, dict):
                    continue
                keyword = item.get("keyword")
                if not isinstance(keyword, str) or not keyword.strip():
                    continue
                candidate: CandidateKeyword = {"keyword": keyword, "source": "llm"}
                if item.get("intent") in M4_ALLOWED_INTENTS:
                    candidate["intent"] = item["intent"]
                if item.get("tier") in M4_ALLOWED_TIERS:
                    candidate["tier"] = item["tier"]
                if item.get("aio_risk") in M4_ALLOWED_AIO_RISK:
                    candidate["aio_risk"] = item["aio_risk"]
                candidates.append(candidate)
        return candidates, True, int((time.monotonic() - started) * 1000)
    except Exception:
        logger.warning("M4 LLM expansion source failed", exc_info=True)
        return [], False, int((time.monotonic() - started) * 1000)


async def _load_dfs_keywords(
    niche: str,
    dataforseo_client: object | None,
    *,
    location_name: str,
    suggestions_limit: int,
) -> tuple[list[str], bool, int]:
    """Load and normalize the DataForSEO suggestions source."""
    started = time.monotonic()
    if dataforseo_client is None or not hasattr(dataforseo_client, "keyword_suggestions"):
        return [], False, 0

    try:
        response = await dataforseo_client.keyword_suggestions(
            keyword=niche,
            location_name=location_name,
            limit=suggestions_limit,
        )
        return (
            _extract_dfs_keywords(response),
            response.status == "ok",
            int((time.monotonic() - started) * 1000),
        )
    except Exception:
        logger.warning("M4 DataForSEO suggestions source failed", exc_info=True)
        return [], False, int((time.monotonic() - started) * 1000)


async def expand_keywords(
    niche: str,
    *,
    llm_client: object | None,
    dataforseo_client: object | None,
    location_name: str = DFS_DEFAULT_LOCATION_NAME,
    suggestions_limit: int = 50,
) -> KeywordExpansion:
    """Expand one niche keyword into a deterministic keyword set."""
    niche_norm = normalize_keyword(niche)
    if not niche_norm:
        raise ValueError("niche must be a non-empty string")

    llm_task = asyncio.create_task(_load_llm_candidates(niche_norm, llm_client))
    dfs_task = asyncio.create_task(
        _load_dfs_keywords(
            niche_norm,
            dataforseo_client,
            location_name=location_name,
            suggestions_limit=suggestions_limit,
        )
    )
    done, pending = await asyncio.wait(
        {llm_task, dfs_task},
        timeout=M4_INTERACTIVE_TIMEOUT_SECONDS,
    )
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    llm_candidates: list[CandidateKeyword] = []
    llm_success = False
    llm_ms = int(M4_INTERACTIVE_TIMEOUT_SECONDS * 1000) if llm_task in pending else 0
    if llm_task in done:
        llm_candidates, llm_success, llm_ms = llm_task.result()

    dfs_keywords: list[str] = []
    dfs_success = False
    dfs_ms = int(M4_INTERACTIVE_TIMEOUT_SECONDS * 1000) if dfs_task in pending else 0
    if dfs_task in done:
        dfs_keywords, dfs_success, dfs_ms = dfs_task.result()

    dfs_candidates: list[CandidateKeyword] = [
        {"keyword": keyword, "source": "dataforseo_suggestions"} for keyword in dfs_keywords
    ]
    seed_candidate: CandidateKeyword = {"keyword": niche_norm, "source": "input", "tier": 1}
    deduped = dedupe_candidate_keywords([seed_candidate, *llm_candidates, *dfs_candidates])

    intent_start = time.monotonic()
    expanded_keywords: list[ExpandedKeyword] = []
    for candidate in deduped:
        keyword = normalize_keyword(candidate.get("keyword", ""))
        if not keyword:
            continue

        intent = candidate.get("intent")
        if intent not in M4_ALLOWED_INTENTS:
            intent = infer_intent_from_rules(keyword) or "commercial"
        if intent not in M4_ALLOWED_INTENTS:
            intent = "commercial"

        tier = candidate.get("tier")
        if tier not in M4_ALLOWED_TIERS:
            tier = _infer_tier(keyword, niche_norm)

        source = candidate.get("source", "merged")
        if source not in M4_ALLOWED_SOURCES:
            source = "merged"

        aio_risk = candidate.get("aio_risk")
        if aio_risk not in M4_ALLOWED_AIO_RISK:
            aio_risk = aio_risk_for_intent(intent)

        expanded_keywords.append(
            {
                "keyword": keyword,
                "tier": tier,
                "intent": intent,
                "source": source,
                "aio_risk": aio_risk,
                "actionable": is_actionable_intent(intent),
            }
        )
    intent_ms = int((time.monotonic() - intent_start) * 1000)

    expanded_keywords.sort(
        key=lambda kw: (
            kw["tier"],
            M4_INTENT_PRIORITY.get(kw["intent"], 99),
            kw["keyword"],
        )
    )
    expanded_keywords = expanded_keywords[:M4_MAX_KEYWORDS]

    actionable_keywords = sum(1 for kw in expanded_keywords if kw["actionable"])
    informational_keywords_excluded = sum(
        1 for kw in expanded_keywords if kw["intent"] == "informational"
    )
    total_keywords = len(expanded_keywords)

    llm_terms = {normalize_keyword(kw.get("keyword", "")) for kw in llm_candidates}
    llm_terms = {term for term in llm_terms if term}
    dfs_terms = {normalize_keyword(term) for term in dfs_keywords if normalize_keyword(term)}
    confidence = _confidence_from_overlap(
        llm_terms,
        dfs_terms,
        llm_success=llm_success,
        dfs_success=dfs_success,
    )
    if confidence not in M4_ALLOWED_CONFIDENCE:
        confidence = "low"

    logger.info(
        "M4 expand_keywords DONE niche=%r total=%d deduped=%d "
        "llm_ok=%s dfs_ok=%s llm_ms=%d dfs_ms=%d intent_ms=%d",
        niche_norm,
        total_keywords,
        len(deduped),
        llm_success,
        dfs_success,
        llm_ms,
        dfs_ms,
        intent_ms,
    )

    return {
        "niche": niche_norm,
        "expanded_keywords": expanded_keywords,
        "total_keywords": total_keywords,
        "actionable_keywords": actionable_keywords,
        "informational_keywords_excluded": informational_keywords_excluded,
        "expansion_confidence": confidence,
    }
