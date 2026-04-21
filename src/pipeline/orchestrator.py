"""End-to-end niche-scoring orchestrator (M4 -> M9) for a single metro."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from src.classification.ai_exposure import classify_ai_exposure
from src.classification.difficulty_tier import compute_difficulty_tier
from src.classification.guidance_generator import classify_and_generate_guidance
from src.classification.serp_archetype import classify_serp_archetype
from src.data.metro_db import MetroDB
from src.pipeline.data_collection import collect_data
from src.pipeline.keyword_expansion import expand_keywords
from src.pipeline.report_generator import generate_report
from src.pipeline.signal_extraction import extract_signals
from src.scoring.engine import compute_scores


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
    strategy_profile: str = "balanced",
    llm_client: Any,
    dataforseo_client: Any,
    metro_db: MetroDB | None = None,
    dry_run: bool = False,
) -> ScoreNicheResult:
    """Score a (niche, city, state?) tuple end-to-end.

    Runs M4 -> M5 -> M6 -> M7 -> M8 -> M9 against the single metro whose
    `principal_cities` (or fallback `cbsa_name`) matches `city`. If `state`
    is provided it narrows the search (useful when a city name collides
    across states). Raises ValueError if no metro in the seed matches.
    """
    started = time.monotonic()
    metros_db = metro_db or MetroDB.from_seed()
    target = metros_db.find_by_city(city, state=state)
    if target is None:
        raise ValueError(f"no CBSA match for city={city!r} state={state!r}")
    resolved_state = target.state

    if dry_run:
        return await _dry_run_result(
            niche=niche,
            city=city,
            state=resolved_state,
            target=target,
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

    expansion = await expand_keywords(
        niche,
        llm_client=llm_client,
        dataforseo_client=dataforseo_client,
    )

    raw = await collect_data(
        keywords=expansion["keywords"],
        metros=[m5_metro_input],
        strategy_profile=strategy_profile,
        client=dataforseo_client,
    )

    metro_result = raw.metros[target.cbsa_code]
    metro_bundle = asdict(metro_result)
    metro_bundle.pop("metro_id", None)
    signals = extract_signals(
        raw_metro_bundle=metro_bundle,
        keyword_expansion=expansion["keywords"],
        cross_metro_domain_stats=None,
        total_metros=1,
    )

    scores = compute_scores(
        metro_signals=signals,
        all_metro_signals=[signals],
        strategy_profile=strategy_profile,
    )

    # M8 classification — unpack tuple returns from classify_serp_archetype and
    # compute_difficulty_tier; classify_and_generate_guidance is async and takes
    # a ClassificationInput envelope.
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
    guidance_bundle = await classify_and_generate_guidance(
        classification_input,
        llm_client,
    )

    run_input = {
        "run_id": run_id,
        "input": {
            "niche_keyword": niche,
            "geo_scope": "city",
            "geo_target": f"{city}, {resolved_state}",
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
            "total_api_calls": raw.meta.total_api_calls,
            "total_cost_usd": raw.meta.total_cost_usd,
            "processing_time_seconds": time.monotonic() - started,
        },
    }

    report = generate_report(run_input)

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
    state: str,
    target: Any,
    strategy_profile: str,
    started: float,
    run_id: str,
) -> ScoreNicheResult:
    """Return a contract-compliant ScoreNicheResult using fixture data, no live calls.

    Loads M6 signals from the canonical test fixture bundle, then runs real M7 scoring
    and M8 classification so the returned report has the same shape as a live run.
    The LLM guidance step falls back to rule-based templates (llm_client=None is safe).
    """
    # Lazy import so the test-fixture dependency is only loaded in dry_run=True path.
    from tests.fixtures.m6_signal_extraction_fixtures import (  # noqa: PLC0415
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
            "geo_target": f"{city}, {state}",
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
