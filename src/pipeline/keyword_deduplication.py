"""Keyword normalization and deduplication utilities for M4."""

from __future__ import annotations

import re
import string
from typing import TypedDict

from src.config.constants import M4_ALLOWED_SOURCES


class CandidateKeyword(TypedDict, total=False):
    """Internal candidate payload before final M4 classification."""

    keyword: str
    source: str
    intent: str
    tier: int
    aio_risk: str


def normalize_keyword(keyword: str) -> str:
    """Normalize a keyword for deterministic deduplication."""
    normalized = keyword.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)

    # Remove punctuation-only suffixes (e.g. "plumber!!!" -> "plumber").
    while normalized and normalized[-1] in string.punctuation:
        normalized = normalized[:-1]
    return normalized.strip()


def dedupe_candidate_keywords(candidates: list[CandidateKeyword]) -> list[CandidateKeyword]:
    """Deduplicate candidate keywords by normalized text.

    If a keyword appears from multiple sources, collapse to one record and mark
    source as ``merged`` for traceability.
    """
    deduped: dict[str, CandidateKeyword] = {}
    source_rank = {source: idx for idx, source in enumerate(M4_ALLOWED_SOURCES)}

    for candidate in candidates:
        raw_keyword = candidate.get("keyword", "")
        normalized = normalize_keyword(raw_keyword)
        if not normalized:
            continue

        source = candidate.get("source", "merged")
        if source not in M4_ALLOWED_SOURCES:
            source = "merged"

        current: CandidateKeyword = {
            "keyword": normalized,
            "source": source,
        }
        if "intent" in candidate:
            current["intent"] = candidate["intent"]
        if "tier" in candidate:
            current["tier"] = candidate["tier"]
        if "aio_risk" in candidate:
            current["aio_risk"] = candidate["aio_risk"]

        existing = deduped.get(normalized)
        if existing is None:
            deduped[normalized] = current
            continue

        # Merge source traceability when multiple discovery paths produce
        # the same canonical keyword.
        if existing.get("source") != source:
            existing["source"] = "merged"
        else:
            # Keep deterministic source if both equal; no-op.
            existing["source"] = existing.get("source", source)

        # Keep any explicit metadata from either side, preferring the entry with
        # the "earlier" source rank to preserve stable outcomes.
        existing_rank = source_rank.get(existing.get("source", "merged"), len(source_rank))
        current_rank = source_rank.get(source, len(source_rank))
        preferred = existing if existing_rank <= current_rank else current
        for key in ("intent", "tier", "aio_risk"):
            if key not in existing and key in current:
                existing[key] = current[key]  # type: ignore[assignment]
            elif key in existing and key in current:
                existing[key] = preferred.get(key, existing[key])  # type: ignore[assignment]

    return list(deduped.values())
