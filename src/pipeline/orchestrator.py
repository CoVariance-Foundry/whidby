"""End-to-end niche-scoring orchestrator (M4 -> M9) for a single metro."""

from __future__ import annotations

import logging
import time
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.classification.ai_exposure import classify_ai_exposure
from src.classification.difficulty_tier import compute_difficulty_tier
from src.classification.guidance_generator import classify_and_generate_guidance
from src.classification.serp_archetype import classify_serp_archetype
from src.clients.supabase_persistence import (
    build_seo_evidence_artifact_rows_from_cost_records,
)
from src.data.metro_db import MetroDB
from src.data.metro_db_adapter import MetroDBGeoLookup
from src.domain.entities import City
from src.domain.ports import CityDataProvider
from src.domain.services.geo_resolver import GeoResolver, ResolvedTarget
from src.pipeline.data_collection import collect_data
from src.pipeline.domain_classifier import normalize_domain
from src.pipeline.keyword_expansion import expand_keywords
from src.pipeline.report_generator import generate_report
from src.pipeline.signal_extraction import extract_signals
from src.pipeline.types import CollectionProfile
from src.scoring.benchmark_repository import SeoBenchmarkRepository
from src.scoring.engine import compute_scores
from src.scoring.v2 import compute_v2_scores

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoreNicheResult:
    """Report plus pre-derived fields for convenience on the API boundary."""

    report: dict[str, Any]
    opportunity_score: int
    evidence: list[dict[str, Any]]
    seo_evidence_artifacts: list[dict[str, Any]]
    local_pack_listing_facts: list[dict[str, Any]]


async def score_niche_for_metro(
    *,
    niche: str,
    city: str,
    state: str | None = None,
    place_id: str | None = None,
    dataforseo_location_code: int | None = None,
    cbsa_code: str | None = None,
    cbsa_name: str | None = None,
    population: int | None = None,
    strategy_profile: str = "balanced",
    collection_profile: CollectionProfile = "full",
    llm_client: Any,
    dataforseo_client: Any,
    metro_db: MetroDB | None = None,
    benchmark_repository: SeoBenchmarkRepository | None = None,
    city_data_provider: CityDataProvider | None = None,
    dry_run: bool = False,
    request_id: str | None = None,
) -> ScoreNicheResult:
    """Score a (niche, city, state?) tuple end-to-end.

    Runs M4 -> M5 -> M6 -> M7 -> M8 -> M9 against the single metro whose
    `principal_cities` (or fallback `cbsa_name`) matches `city`. If `state`
    is provided it narrows the search (useful when a city name collides
    across states). If production callers provide `cbsa_code` plus
    `dataforseo_location_code`, that explicit metro identity is preserved for
    persistence while using the supplied DFS target.
    Raises ValueError if no target can be resolved.
    """
    started = time.monotonic()
    logger.info(
        "score_niche_for_metro START request_id=%s niche=%r city=%r state=%r dry_run=%s",
        request_id,
        niche,
        city,
        state,
        dry_run,
    )
    resolved = _explicit_target(
        city=city,
        state=state,
        place_id=place_id,
        dataforseo_location_code=dataforseo_location_code,
        cbsa_code=cbsa_code,
        cbsa_name=cbsa_name,
        population=population,
    )
    if resolved is None:
        metros_db = metro_db or MetroDB.from_seed()
        geo_lookup = MetroDBGeoLookup(metros_db)
        resolver = GeoResolver(geo_lookup)
        resolved = resolver.resolve(
            city=city,
            state=state,
            place_id=place_id,
            dataforseo_location_code=dataforseo_location_code,
        )
    resolved_state = resolved.state_code

    logger.info(
        "Metro resolved: cbsa=%s name=%r state=%s",
        resolved.cbsa_code,
        resolved.metro_name,
        resolved_state,
    )

    if dry_run:
        return await _dry_run_result(
            niche=niche,
            city=city,
            state=resolved_state,
            target=resolved,
            place_id=place_id,
            dataforseo_location_code=dataforseo_location_code,
            strategy_profile=strategy_profile,
            benchmark_repository=benchmark_repository,
            city_data_provider=city_data_provider,
            started=started,
            run_id=f"score-dry-{uuid4()}",
        )

    m5_metro_input: dict[str, Any] = {
        "metro_id": resolved.cbsa_code,
        "location_code": resolved.location_code,
        "principal_city": city,
    }

    run_id = f"score-{uuid4()}"
    rid = request_id or run_id

    with _cost_capture_context(dataforseo_client, run_id):
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
            run_id,
            len(expansion.get("expanded_keywords", [])),
            expansion.get("expansion_confidence"),
            m4_ms,
        )

        # --- M5 data collection ---
        m5_start = time.monotonic()
        logger.info("[%s] M5 data collection START", run_id)
        raw = await collect_data(
            keywords=expansion["expanded_keywords"],
            metros=[m5_metro_input],
            strategy_profile=strategy_profile,
            client=dataforseo_client,
            collection_profile=collection_profile,
        )
        m5_ms = int((time.monotonic() - m5_start) * 1000)
        logger.info(
            "[%s] M5 data collection DONE — api_calls=%d cost=$%.4f duration_ms=%d",
            run_id,
            raw.meta.total_api_calls,
            raw.meta.total_cost_usd,
            m5_ms,
        )

    # --- M6 signal extraction ---
    m6_start = time.monotonic()
    logger.info("[%s] M6 signal extraction START", run_id)
    metro_result = raw.metros[resolved.cbsa_code]
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
    logger.info(
        "[%s] M7 scoring DONE — opportunity=%s duration_ms=%d",
        run_id,
        scores.get("opportunity"),
        m7_ms,
    )

    # --- M8 classification + guidance ---
    m8_start = time.monotonic()
    ai_exposure = classify_ai_exposure(signals)
    serp_archetype, _rule_id = classify_serp_archetype(signals)
    difficulty, _combined_comp, _resolved = compute_difficulty_tier(
        scores=scores,
        strategy_profile=strategy_profile,
        signals=signals,
    )

    logger.info(
        "[%s] M8 classification: ai_exposure=%s serp_archetype=%s difficulty=%s",
        run_id,
        ai_exposure,
        serp_archetype,
        difficulty,
    )

    classification_input: dict[str, Any] = {
        "niche": niche,
        "metro_name": resolved.metro_name,
        "signals": signals,
        "scores": scores,
        "strategy_profile": strategy_profile,
    }
    guidance_bundle = await classify_and_generate_guidance(
        classification_input,
        None if collection_profile == "interactive" else llm_client,
    )
    m8_ms = int((time.monotonic() - m8_start) * 1000)
    logger.info("[%s] M8 guidance generation DONE duration_ms=%d", run_id, m8_ms)

    v2_scores = None
    if benchmark_repository is not None:
        v2_scores = _compute_v2_scores_for_orchestrator(
            niche_normalized=niche.strip().lower(),
            cbsa_code=resolved.cbsa_code,
            signals=signals,
            population=resolved.population,
            benchmark_repository=benchmark_repository,
            city_data_provider=city_data_provider,
        )

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
                "cbsa_code": resolved.cbsa_code,
                "cbsa_name": resolved.metro_name,
                "population": resolved.population,
                "scores": scores,
                "confidence": scores["confidence"],
                "serp_archetype": serp_archetype,
                "ai_exposure": ai_exposure,
                "difficulty_tier": difficulty,
                "signals": signals,
                "guidance": guidance_bundle,
                **({"v2_scores": v2_scores} if v2_scores is not None else {}),
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
    current_cost_records = _cost_records_for_context(dfs_cost_log, run_id)
    evidence_artifacts = build_seo_evidence_artifact_rows_from_cost_records(current_cost_records)
    local_pack_listing_facts = _build_local_pack_listing_facts(
        report=report,
        raw_metro=metro_result,
        cbsa_code=resolved.cbsa_code,
        location_code=resolved.location_code,
        maps_evidence_artifact_ids=_maps_evidence_artifact_ids(evidence_artifacts),
    )
    m9_ms = int((time.monotonic() - m9_start) * 1000)
    logger.info(
        "[%s] M9 report assembly DONE — report_id=%s duration_ms=%d",
        run_id,
        report.get("report_id"),
        m9_ms,
    )

    elapsed = time.monotonic() - started
    _log_dfs_cost_summary(
        run_id, dfs_total_calls, dfs_total_cost, dfs_cached, dfs_breakdown, elapsed
    )
    logger.info(
        "score_niche_for_metro DONE in %.2fs — opportunity=%s request_id=%s "
        "stage_ms={m4=%d, m5=%d, m6=%d, m7=%d, m8=%d, m9=%d}",
        elapsed,
        scores.get("opportunity"),
        rid,
        m4_ms,
        m5_ms,
        m6_ms,
        m7_ms,
        m8_ms,
        m9_ms,
    )

    evidence = _build_evidence_from_signals(signals)
    return ScoreNicheResult(
        report=report,
        opportunity_score=int(round(scores["opportunity"])),
        evidence=evidence,
        seo_evidence_artifacts=evidence_artifacts,
        local_pack_listing_facts=local_pack_listing_facts,
    )


def _explicit_target(
    *,
    city: str,
    state: str | None,
    place_id: str | None,
    dataforseo_location_code: int | None,
    cbsa_code: str | None,
    cbsa_name: str | None,
    population: int | None,
) -> ResolvedTarget | None:
    """Build a production Supabase metro target without consulting the seed file."""
    cleaned_cbsa = str(cbsa_code or "").strip()
    if not cleaned_cbsa:
        return None
    if not isinstance(dataforseo_location_code, int) or dataforseo_location_code <= 0:
        raise ValueError("cbsa_code requires a positive dataforseo_location_code")
    if population is None or population <= 0:
        raise ValueError("cbsa_code requires a positive population for benchmark class resolution")

    state_code = state.strip().upper() if isinstance(state, str) and state.strip() else ""
    metro_name = str(cbsa_name or "").strip() or (f"{city}, {state_code}" if state_code else city)
    population_value = int(population)
    city_record = City(
        city_id=cleaned_cbsa,
        name=city,
        state=state_code,
        population=population_value,
        cbsa_code=cleaned_cbsa,
        dataforseo_location_codes=[dataforseo_location_code],
        principal_cities=[city],
    )
    geo_key = city.strip().lower()
    if state_code:
        geo_key = f"{geo_key}, {state_code}"
    return ResolvedTarget(
        city=city_record,
        metro_name=metro_name,
        state_code=state_code,
        location_code=dataforseo_location_code,
        cbsa_code=cleaned_cbsa,
        population=population_value,
        geo_key=geo_key,
        place_id=place_id,
        is_synthetic=False,
    )


async def _dry_run_result(
    *,
    niche: str,
    city: str,
    state: str | None,
    target: ResolvedTarget,
    place_id: str | None,
    dataforseo_location_code: int | None,
    strategy_profile: str,
    started: float,
    run_id: str,
    benchmark_repository: SeoBenchmarkRepository | None = None,
    city_data_provider: CityDataProvider | None = None,
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
        "metro_name": target.metro_name,
        "signals": signals,
        "scores": scores,
        "strategy_profile": strategy_profile,
    }
    # llm_client=None — guidance_generator safely falls back to rule-based templates.
    guidance_bundle = await classify_and_generate_guidance(classification_input, None)

    v2_scores = None
    if benchmark_repository is not None:
        v2_scores = _compute_v2_scores_for_orchestrator(
            niche_normalized=niche.strip().lower(),
            cbsa_code=target.cbsa_code,
            signals=signals,
            population=target.population,
            benchmark_repository=benchmark_repository,
            city_data_provider=city_data_provider,
        )

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
                "cbsa_name": target.metro_name,
                "population": target.population,
                "scores": scores,
                "confidence": scores["confidence"],
                "serp_archetype": serp_archetype,
                "ai_exposure": ai_exposure,
                "difficulty_tier": difficulty,
                "signals": signals,
                "guidance": guidance_bundle,
                **({"v2_scores": v2_scores} if v2_scores is not None else {}),
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
        seo_evidence_artifacts=[],
        local_pack_listing_facts=[],
    )


def _log_dfs_cost_summary(
    run_id: str,
    total_calls: int,
    total_cost: float,
    cached: int,
    breakdown: dict[str, dict[str, Any]],
    elapsed: float,
) -> None:
    parts = [f"[{run_id}] DFS COST: {total_calls} calls, ${total_cost:.4f}, {cached} cached"]
    if breakdown:
        ep_parts = []
        for ep, info in sorted(breakdown.items(), key=lambda x: -x[1]["cost"]):
            short = ep.rsplit("/", 1)[-1] if "/" in ep else ep
            ep_parts.append(f"{short}={info['calls']}/${info['cost']:.4f}")
        parts.append("breakdown: " + ", ".join(ep_parts))
    logger.info(" — ".join(parts))


def _cost_capture_context(dataforseo_client: Any, run_id: str) -> Any:
    tracker = getattr(dataforseo_client, "cost_tracker", None)
    capture_context = getattr(tracker, "capture_context", None)
    if callable(capture_context):
        return capture_context(run_id)
    return nullcontext()


def _cost_records_for_context(records: list[Any], context_id: str) -> list[Any]:
    filtered = [record for record in records if _record_context_id(record) == context_id]
    if filtered or not records:
        return filtered
    if all(_record_context_id(record) is None for record in records):
        return records
    return filtered


def _record_context_id(record: Any) -> str | None:
    if isinstance(record, dict):
        value = record.get("collection_context_id")
    else:
        value = getattr(record, "collection_context_id", None)
    return str(value) if value is not None else None


def _build_local_pack_listing_facts(
    *,
    report: dict[str, Any],
    raw_metro: Any,
    cbsa_code: str,
    location_code: int,
    maps_evidence_artifact_ids: dict[tuple[str, int], str] | None = None,
) -> list[dict[str, Any]]:
    keyword = _primary_report_keyword(report)
    generated_at = report.get("generated_at")
    local_enrichment = _local_review_enrichment_lookup(raw_metro)
    rows: list[dict[str, Any]] = []
    for maps_result in getattr(raw_metro, "serp_maps", []) or []:
        source_query = _text(maps_result.get("keyword")) or keyword
        evidence_artifact_id = (maps_evidence_artifact_ids or {}).get(
            (source_query or "", location_code)
        )
        items = maps_result.get("items") if isinstance(maps_result.get("items"), list) else []
        for index, item in enumerate(_top_ranked_items(items, limit=3), start=1):
            business_name = _text(
                item.get("business_name") or item.get("title") or item.get("name")
            )
            if not business_name:
                continue
            listing_url = _text(item.get("listing_url") or item.get("url"))
            enrichment = _local_review_enrichment_for_item(
                item,
                business_name=business_name,
                lookup=local_enrichment,
            )
            rows.append(
                {
                    "cbsa_code": cbsa_code,
                    "keyword": source_query or keyword,
                    "listing_rank": _rank_value(item) or index,
                    "business_name": business_name,
                    "cid": _text(item.get("cid")),
                    "place_id": _text(item.get("place_id")),
                    "source_query": source_query,
                    "dataforseo_location_code": location_code,
                    "result_type": _text(item.get("result_type") or item.get("type")),
                    "listing_url": listing_url,
                    "domain": normalize_domain(_text(item.get("domain")) or listing_url or ""),
                    "review_retrieval_mode": _text(
                        item.get("review_retrieval_mode")
                        or item.get("review_collection_mode")
                        or enrichment.get("review_retrieval_mode")
                    ),
                    "review_window_start": item.get("review_window_start")
                    or enrichment.get("review_window_start"),
                    "review_window_end": item.get("review_window_end")
                    or enrichment.get("review_window_end"),
                    "upstream_result_at": _first_present(
                        item,
                        maps_result,
                        keys=("upstream_result_at", "datetime", "timestamp"),
                    ),
                    "evidence_artifact_id": evidence_artifact_id,
                    "rating": item.get("rating"),
                    "review_count": _review_count_from_maps_item(item),
                    "photo_count": item.get("photo_count") or item.get("total_photos"),
                    "categories": item.get("categories") or item.get("category"),
                    "source": "dataforseo",
                    "snapshot_date": generated_at,
                    "report_id": report.get("report_id"),
                }
            )
    return rows


def _maps_evidence_artifact_ids(
    evidence_artifacts: list[dict[str, Any]],
) -> dict[tuple[str, int], str]:
    artifact_ids: dict[tuple[str, int], str] = {}
    for artifact in evidence_artifacts:
        if artifact.get("evidence_family") != "maps":
            continue
        endpoint = _text(artifact.get("endpoint_path", ""))
        if not endpoint or "serp/google/maps" not in endpoint.lower():
            continue
        artifact_id = _text(artifact.get("id"))
        params = artifact.get("normalized_request_params")
        if not artifact_id or not isinstance(params, dict):
            continue
        keyword = _text(params.get("keyword"))
        location_code = _int_or_none(params.get("location_code"))
        if keyword and location_code is not None:
            artifact_ids[(keyword, location_code)] = artifact_id
    return artifact_ids


def _local_review_enrichment_lookup(raw_metro: Any) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in getattr(raw_metro, "gbp_info", []) or []:
        if isinstance(row, dict):
            _add_local_enrichment(lookup, row, _local_enrichment_from_row(row))
    for row in getattr(raw_metro, "google_reviews", []) or []:
        if isinstance(row, dict):
            _add_local_enrichment(lookup, row, _local_enrichment_from_row(row))
    return lookup


def _local_enrichment_from_row(row: dict[str, Any]) -> dict[str, Any]:
    window_start, window_end = _review_window_from_row(row)
    return {
        "review_retrieval_mode": _text(
            row.get("review_retrieval_mode")
            or row.get("review_collection_mode")
            or row.get("preferred_identifier_mode")
        ),
        "review_window_start": window_start,
        "review_window_end": window_end,
    }


def _add_local_enrichment(
    lookup: dict[str, dict[str, Any]],
    row: dict[str, Any],
    enrichment: dict[str, Any],
) -> None:
    if not any(value is not None for value in enrichment.values()):
        return
    for key in _local_lookup_keys(row):
        existing = lookup.setdefault(key, {})
        for field, value in enrichment.items():
            if value is not None:
                existing[field] = value


def _local_review_enrichment_for_item(
    item: dict[str, Any],
    *,
    business_name: str,
    lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidate = {
        **item,
        "business_name": business_name,
    }
    for key in _local_lookup_keys(candidate):
        if key in lookup:
            return lookup[key]
    return {}


def _local_lookup_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("cid", "place_id"):
        value = _norm_text(row.get(field))
        if value:
            keys.append(f"{field}:{value}")
    name = _norm_text(row.get("business_name") or row.get("title") or row.get("name"))
    if name:
        keys.append(f"name:{name}")
    return keys


def _review_window_from_row(row: dict[str, Any]) -> tuple[Any, Any]:
    start = row.get("review_window_start") or row.get("source_window_start")
    end = row.get("review_window_end") or row.get("source_window_end")
    if start or end:
        return start, end

    timestamps = _review_timestamps_from_row(row)
    if not timestamps:
        return None, None
    parsed = [
        (parsed_at, timestamp)
        for timestamp in timestamps
        if (parsed_at := _parse_review_timestamp(timestamp)) is not None
    ]
    if parsed:
        return min(parsed, key=lambda item: item[0])[1], max(parsed, key=lambda item: item[0])[1]

    ordered = sorted(timestamps)
    return ordered[0], ordered[-1]


def _review_timestamps_from_row(row: dict[str, Any]) -> list[str]:
    timestamps: list[str] = []
    raw = row.get("review_timestamps")
    if isinstance(raw, list):
        timestamps.extend(str(value) for value in raw if value)
    items = row.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("timestamp"):
                timestamps.append(str(item["timestamp"]))
    return timestamps


def _parse_review_timestamp(value: str) -> datetime | None:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _primary_report_keyword(report: dict[str, Any]) -> str | None:
    for item in (report.get("keyword_expansion") or {}).get("expanded_keywords", []) or []:
        if isinstance(item, dict) and item.get("keyword"):
            return str(item["keyword"])
    return _text((report.get("input") or {}).get("niche_keyword"))


def _top_ranked_items(items: list[Any], *, limit: int) -> list[dict[str, Any]]:
    rows = [item for item in items if isinstance(item, dict)]
    if any(_rank_value(row) is not None for row in rows):
        rows = [
            row
            for _, row in sorted(
                enumerate(rows),
                key=lambda pair: (
                    _rank_value(pair[1]) is None,
                    _rank_value(pair[1]) if _rank_value(pair[1]) is not None else 0,
                    pair[0],
                ),
            )
        ]
    return rows[:limit]


def _rank_value(row: dict[str, Any]) -> int | None:
    for field in ("listing_rank", "rank_group", "rank", "position", "rank_absolute"):
        try:
            rank = int(row.get(field))
        except (TypeError, ValueError):
            continue
        if rank > 0:
            return rank
    return None


def _review_count_from_maps_item(item: dict[str, Any]) -> Any:
    rating = item.get("rating")
    if isinstance(rating, dict) and rating.get("votes_count") is not None:
        return rating.get("votes_count")
    return item.get("review_count") or item.get("reviews_count") or item.get("votes_count")


def _first_present(
    *sources: dict[str, Any],
    keys: tuple[str, ...],
) -> Any:
    for source in sources:
        for key in keys:
            if source.get(key) is not None:
                return source[key]
    return None


def _norm_text(value: Any) -> str:
    text = _text(value)
    return text.lower() if text else ""


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _population_class_for_benchmarks(population: int | None) -> str | None:
    if population is None or population <= 0:
        return None
    if population < 50_000:
        return "micro_under_50k"
    if population < 100_000:
        return "small_50_100k"
    if population < 300_000:
        return "medium_100_300k"
    if population < 1_000_000:
        return "large_300k_1m"
    if population < 5_000_000:
        return "metro_1m_5m"
    return "mega_5m_plus"


def _signals_for_v2_benchmarks(signals: dict[str, Any], population: int | None) -> dict[str, Any]:
    existing_population_class = str(signals.get("population_class") or "").strip() or None
    signal_population = signals.get("population")
    return {
        **signals,
        "population": signal_population if signal_population is not None else population,
        "population_class": existing_population_class
        or _population_class_for_benchmarks(population),
    }


def _compute_v2_scores_for_orchestrator(
    *,
    niche_normalized: str,
    cbsa_code: str,
    signals: dict[str, Any],
    population: int | None,
    benchmark_repository: SeoBenchmarkRepository,
    city_data_provider: CityDataProvider | None,
) -> dict[str, Any]:
    v2_signals = _signals_for_v2_benchmarks(signals, population)
    population_class = str(v2_signals.get("population_class") or "").strip()
    benchmark = None
    if population_class:
        benchmark = benchmark_repository.get(
            niche_normalized=niche_normalized,
            population_class=population_class,
        )

    naics_code = (benchmark.naics_code or "").strip() if benchmark is not None else ""
    if city_data_provider is not None and naics_code:
        density = city_data_provider.get_business_density(cbsa_code, naics_code)
        if isinstance(density, dict) and density.get("establishments") is not None:
            v2_signals["cbp_establishments"] = density["establishments"]

    return compute_v2_scores(
        niche_normalized=niche_normalized,
        cbsa_code=cbsa_code,
        metro_signals=v2_signals,
        benchmark=benchmark,
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


def _format_geo_target(city: str, state: str | None) -> str:
    cleaned_city = city.strip()
    cleaned_state = (state or "").strip()
    if cleaned_city and cleaned_state:
        return f"{cleaned_city}, {cleaned_state}"
    return cleaned_city or cleaned_state
