"""End-to-end niche-scoring orchestrator (M4 -> M9) for a single metro."""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from src.classification.ai_exposure import classify_ai_exposure
from src.classification.difficulty_tier import compute_difficulty_tier
from src.classification.guidance_generator import classify_and_generate_guidance
from src.classification.serp_archetype import classify_serp_archetype
from src.data.metro_db import Metro, MetroDB
from src.pipeline.data_collection import collect_data
from src.pipeline.keyword_expansion import expand_keywords
from src.pipeline.report_generator import generate_report
from src.pipeline.signal_extraction import extract_signals
from src.scoring.engine import compute_scores

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoreNicheResult:
    """Report plus pre-derived fields for convenience on the API boundary."""

    report: dict[str, Any]
    opportunity_score: int
    evidence: list[dict[str, Any]]


async def score_niche_for_metro(
    *,
    niche: str,
    city: str,
    state: str | None = None,
    place_id: str | None = None,
    dataforseo_location_code: int | None = None,
    strategy_profile: str = "balanced",
    llm_client: Any,
    dataforseo_client: Any,
    metro_db: MetroDB | None = None,
    dry_run: bool = False,
    request_id: str | None = None,
) -> ScoreNicheResult:
    """Score a (niche, city, state?) tuple end-to-end.

    Runs M4 -> M5 -> M6 -> M7 -> M8 -> M9 against the single metro whose
    `principal_cities` (or fallback `cbsa_name`) matches `city`. If `state`
    is provided it narrows the search (useful when a city name collides
    across states). If `dataforseo_location_code` is provided, it is used
    directly for DFS targeting (with a synthetic metro id) to support
    canonical place selections outside the static seed.
    Raises ValueError if no target can be resolved.
    """
    started = time.monotonic()
    logger.info(
        "score_niche_for_metro START request_id=%s niche=%r city=%r state=%r dry_run=%s",
        request_id, niche, city, state, dry_run,
    )
    metros_db = metro_db or MetroDB.from_seed()
    target: Metro | None = None
    resolved_state = state.strip().upper() if isinstance(state, str) and state.strip() else None

    if isinstance(dataforseo_location_code, int) and dataforseo_location_code > 0:
        synthetic_code = f"mapbox:{place_id}" if place_id else f"manual:{city.lower().replace(' ', '-')}"
        target = Metro(
            cbsa_code=synthetic_code,
            cbsa_name=city if not resolved_state else f"{city}, {resolved_state}",
            state=resolved_state or "",
            population=0,
            principal_cities=[city],
            dataforseo_location_codes=[dataforseo_location_code],
        )
    else:
        target = metros_db.find_by_city(city, state=state)
        if target is None:
            raise ValueError(f"no CBSA match for city={city!r} state={state!r}")
        resolved_state = target.state

    logger.info("Metro resolved: cbsa=%s name=%r state=%s", target.cbsa_code, target.cbsa_name, resolved_state)

    if dry_run:
        return await _dry_run_result(
            niche=niche,
            city=city,
            state=resolved_state,
            target=target,
            place_id=place_id,
            dataforseo_location_code=dataforseo_location_code,
            strategy_profile=strategy_profile,
            started=started,
            run_id=f"score-dry-{uuid4()}",
        )

    if not target.dataforseo_location_codes:
        raise ValueError(
            f"metro {target.cbsa_code} has no DataForSEO location codes"
        )
    m5_metro_input: dict[str, Any] = {
        "metro_id": target.cbsa_code,
        "location_code": target.dataforseo_location_codes[0],
        "principal_city": city,
    }

    run_id = f"score-{uuid4()}"
    rid = request_id or run_id

    # --- M4 keyword expansion ---
    m4_start = time.monotonic()
    logger.info("[%s] M4 keyword expansion START request_id=%s", run_id, rid)
    expansion = await expand_keywords(
        niche,
        llm_client=llm_client,
        dataforseo_client=dataforseo_client,
    )
    m4_ms = int((time.monotonic() - m4_start) * 1000)
    logger.info(
        "[%s] M4 keyword expansion DONE — %d keywords, confidence=%s, duration_ms=%d",
        run_id, len(expansion.get("expanded_keywords", [])),
        expansion.get("expansion_confidence"), m4_ms,
    )

    # --- M5 data collection ---
    m5_start = time.monotonic()
    logger.info("[%s] M5 data collection START", run_id)
    raw = await collect_data(
        keywords=expansion["expanded_keywords"],
        metros=[m5_metro_input],
        strategy_profile=strategy_profile,
        client=dataforseo_client,
    )
    m5_ms = int((time.monotonic() - m5_start) * 1000)
    logger.info(
        "[%s] M5 data collection DONE — api_calls=%d cost=$%.4f duration_ms=%d",
        run_id, raw.meta.total_api_calls, raw.meta.total_cost_usd, m5_ms,
    )

    # --- M6 signal extraction ---
    m6_start = time.monotonic()
    logger.info("[%s] M6 signal extraction START", run_id)
    metro_result = raw.metros[target.cbsa_code]
    metro_bundle = asdict(metro_result)
    metro_bundle.pop("metro_id", None)
    signals = extract_signals(
        raw_metro_bundle=metro_bundle,
        keyword_expansion=expansion["expanded_keywords"],
        cross_metro_domain_stats=None,
        total_metros=1,
    )
    m6_ms = int((time.monotonic() - m6_start) * 1000)
    logger.info("[%s] M6 signal extraction DONE duration_ms=%d", run_id, m6_ms)

    # --- M7 scoring ---
    m7_start = time.monotonic()
    logger.info("[%s] M7 scoring START", run_id)
    scores = compute_scores(
        metro_signals=signals,
        all_metro_signals=[signals],
        strategy_profile=strategy_profile,
    )
    m7_ms = int((time.monotonic() - m7_start) * 1000)
    logger.info("[%s] M7 scoring DONE — opportunity=%s duration_ms=%d",
                run_id, scores.get("opportunity"), m7_ms)

    # --- M8 classification + guidance ---
    m8_start = time.monotonic()
    ai_exposure = classify_ai_exposure(signals)
    serp_archetype, _rule_id = classify_serp_archetype(signals)
    difficulty, _combined_comp, _resolved = compute_difficulty_tier(
        scores=scores,
        strategy_profile=strategy_profile,
        signals=signals,
    )

    logger.info("[%s] M8 classification: ai_exposure=%s serp_archetype=%s difficulty=%s",
                run_id, ai_exposure, serp_archetype, difficulty)

    classification_input: dict[str, Any] = {
        "niche": niche,
        "metro_name": target.cbsa_name,
        "signals": signals,
        "scores": scores,
        "strategy_profile": strategy_profile,
    }
    guidance_bundle = await classify_and_generate_guidance(
        classification_input,
        llm_client,
    )
    m8_ms = int((time.monotonic() - m8_start) * 1000)
    logger.info("[%s] M8 guidance generation DONE duration_ms=%d", run_id, m8_ms)

    # --- M9 report assembly ---
    m9_start = time.monotonic()
    logger.info("[%s] M9 report assembly START", run_id)

    dfs_total_cost = getattr(dataforseo_client, "total_cost", raw.meta.total_cost_usd)
    dfs_cost_log = getattr(dataforseo_client, "cost_log", [])
    dfs_total_calls = len(dfs_cost_log) if dfs_cost_log else raw.meta.total_api_calls
    dfs_cached = sum(1 for r in dfs_cost_log if getattr(r, "cached", False))
    dfs_tracker = getattr(dataforseo_client, "cost_tracker", None)
    dfs_breakdown = dfs_tracker.cost_by_endpoint() if dfs_tracker else {}

    run_input = {
        "run_id": run_id,
        "input": {
            "niche_keyword": niche,
            "geo_scope": "city",
            "geo_target": _format_geo_target(city, resolved_state),
            **({"place_id": place_id} if place_id else {}),
            **(
                {"dataforseo_location_code": dataforseo_location_code}
                if isinstance(dataforseo_location_code, int) and dataforseo_location_code > 0
                else {}
            ),
            "report_depth": "standard",
            "strategy_profile": strategy_profile,
        },
        "keyword_expansion": expansion,
        "metros": [
            {
                "cbsa_code": target.cbsa_code,
                "cbsa_name": target.cbsa_name,
                "population": target.population,
                "scores": scores,
                "confidence": scores["confidence"],
                "serp_archetype": serp_archetype,
                "ai_exposure": ai_exposure,
                "difficulty_tier": difficulty,
                "signals": signals,
                "guidance": guidance_bundle,
            }
        ],
        "meta": {
            "total_api_calls": dfs_total_calls,
            "total_cost_usd": round(dfs_total_cost, 6),
            "dfs_cached_calls": dfs_cached,
            "dfs_cost_breakdown": dfs_breakdown,
            "processing_time_seconds": time.monotonic() - started,
        },
    }

    report = generate_report(run_input)
    m9_ms = int((time.monotonic() - m9_start) * 1000)
    logger.info("[%s] M9 report assembly DONE — report_id=%s duration_ms=%d",
                run_id, report.get("report_id"), m9_ms)

    elapsed = time.monotonic() - started
    _log_dfs_cost_summary(run_id, dfs_total_calls, dfs_total_cost, dfs_cached, dfs_breakdown, elapsed)
    logger.info(
        "score_niche_for_metro DONE in %.2fs — opportunity=%s request_id=%s "
        "stage_ms={m4=%d, m5=%d, m6=%d, m7=%d, m8=%d, m9=%d}",
        elapsed, scores.get("opportunity"), rid,
        m4_ms, m5_ms, m6_ms, m7_ms, m8_ms, m9_ms,
    )

    evidence = _build_evidence_from_signals(signals)
    return ScoreNicheResult(
        report=report,
        opportunity_score=int(round(scores["opportunity"])),
        evidence=evidence,
    )


async def _dry_run_result(
    *,
    niche: str,
    city: str,
    state: str | None,
    target: Any,
    place_id: str | None,
    dataforseo_location_code: int | None,
    strategy_profile: str,
    started: float,
    run_id: str,
) -> ScoreNicheResult:
    """Return a contract-compliant ScoreNicheResult using fixture data, no live calls.

    Loads M6 signals from the canonical test fixture bundle, then runs real M7 scoring
    and M8 classification so the returned report has the same shape as a live run.
    The LLM guidance step falls back to rule-based templates (llm_client=None is safe).
    """
    from src.pipeline.dry_run_fixtures import (  # noqa: PLC0415
        fixture_keyword_expansion,
        fixture_metro_signals,
    )

    signals = fixture_metro_signals()
    expansion = fixture_keyword_expansion(niche)

    scores = compute_scores(
        metro_signals=signals,
        all_metro_signals=[signals],
        strategy_profile=strategy_profile,
    )

    ai_exposure = classify_ai_exposure(signals)
    serp_archetype, _rule_id = classify_serp_archetype(signals)
    difficulty, _combined_comp, _resolved = compute_difficulty_tier(
        scores=scores,
        strategy_profile=strategy_profile,
        signals=signals,
    )

    classification_input: dict[str, Any] = {
        "niche": niche,
        "metro_name": target.cbsa_name,
        "signals": signals,
        "scores": scores,
        "strategy_profile": strategy_profile,
    }
    # llm_client=None — guidance_generator safely falls back to rule-based templates.
    guidance_bundle = await classify_and_generate_guidance(classification_input, None)

    run_input = {
        "run_id": run_id,
        "input": {
            "niche_keyword": niche,
            "geo_scope": "city",
            "geo_target": _format_geo_target(city, state),
            **({"place_id": place_id} if place_id else {}),
            **(
                {"dataforseo_location_code": dataforseo_location_code}
                if isinstance(dataforseo_location_code, int) and dataforseo_location_code > 0
                else {}
            ),
            "report_depth": "standard",
            "strategy_profile": strategy_profile,
        },
        "keyword_expansion": expansion,
        "metros": [
            {
                "cbsa_code": target.cbsa_code,
                "cbsa_name": target.cbsa_name,
                "population": target.population,
                "scores": scores,
                "confidence": scores["confidence"],
                "serp_archetype": serp_archetype,
                "ai_exposure": ai_exposure,
                "difficulty_tier": difficulty,
                "signals": signals,
                "guidance": guidance_bundle,
            }
        ],
        "meta": {
            "total_api_calls": 0,
            "total_cost_usd": 0.0,
            "processing_time_seconds": time.monotonic() - started,
        },
    }

    report = generate_report(run_input)
    return ScoreNicheResult(
        report=report,
        opportunity_score=int(round(scores["opportunity"])),
        evidence=_build_evidence_from_signals(signals),
    )


def _log_dfs_cost_summary(
    run_id: str,
    total_calls: int,
    total_cost: float,
    cached: int,
    breakdown: dict[str, dict[str, Any]],
    elapsed: float,
) -> None:
    parts = [
        f"[{run_id}] DFS COST: {total_calls} calls, ${total_cost:.4f}, {cached} cached"
    ]
    if breakdown:
        ep_parts = []
        for ep, info in sorted(breakdown.items(), key=lambda x: -x[1]["cost"]):
            short = ep.rsplit("/", 1)[-1] if "/" in ep else ep
            ep_parts.append(f"{short}={info['calls']}/${info['cost']:.4f}")
        parts.append("breakdown: " + ", ".join(ep_parts))
    logger.info(" — ".join(parts))


def _build_evidence_from_signals(signals: dict[str, dict]) -> list[dict[str, Any]]:
    def _read(category: str, key: str, default: float = 0.0) -> float:
        node = signals.get(category) or {}
        value = node.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    return [
        {
            "category": "demand",
            "label": "Tier-1 Transactional Volume",
            "value": _read("demand", "tier_1_volume_effective"),
            "source": "M6 demand signals",
            "is_available": True,
        },
        {
            "category": "competition",
            "label": "Median Top-10 Domain Rating",
            "value": _read("organic_competition", "median_top10_dr"),
            "source": "M6 organic competition",
            "is_available": True,
        },
        {
            "category": "monetization",
            "label": "Median Commercial CPC",
            "value": _read("monetization", "median_cpc"),
            "source": "M6 monetization",
            "is_available": True,
        },
        {
            "category": "ai_resilience",
            "label": "AI Overview Penetration",
            "value": _read("ai_resilience", "aio_rate"),
            "source": "M6 AI resilience",
            "is_available": True,
        },
    ]


def _format_geo_target(city: str, state: str | None) -> str:
    cleaned_city = city.strip()
    cleaned_state = (state or "").strip()
    if cleaned_city and cleaned_state:
        return f"{cleaned_city}, {cleaned_state}"
    return cleaned_city or cleaned_state
