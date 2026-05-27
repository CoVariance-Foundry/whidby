"""Persist M9 reports to the Supabase schema defined in 001_core_schema.sql."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from src.domain.services.explore_refresh_service import RefreshTarget
from src.pipeline.domain_classifier import is_aggregator, normalize_domain

logger = logging.getLogger(__name__)

_EVIDENCE_ARTIFACT_COLLECTION_KEYS = (
    "seo_evidence_artifacts",
    "raw_evidence_artifacts",
)
_EVIDENCE_ARTIFACT_KEYS = set(_EVIDENCE_ARTIFACT_COLLECTION_KEYS)
_PRIVATE_PERSISTENCE_KEYS = _EVIDENCE_ARTIFACT_KEYS | {"local_pack_listing_facts"}
_ALLOWED_EVIDENCE_FAMILIES = {
    "serp",
    "maps",
    "reviews",
    "backlinks",
    "lighthouse",
    "keyword_volume",
    "keyword_overview",
}
_ALLOWED_CACHE_STATUSES = {"hit", "miss", "bypass", "replay", "unknown"}


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any: ...


_EXPLORE_TARGET_SELECT = (
    "id,policy_id,niche_keyword,niche_normalized,cbsa_code,cbsa_name,state,"
    "latest_report_id,latest_scored_at,next_refresh_at,active,priority,created_at,updated_at"
)


def _raise_on_error(result: Any) -> None:
    error = getattr(result, "error", None)
    if error:
        message = getattr(error, "message", None) or str(error)
        raise RuntimeError(f"Supabase request failed: {message}")


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _iso_dt(value: datetime) -> str:
    return value.isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result_data(result: Any) -> Any:
    _raise_on_error(result)
    return getattr(result, "data", None)


def _result_rows(result: Any) -> list[dict[str, Any]]:
    data = _result_data(result)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise RuntimeError(f"Unexpected Supabase response data: {data!r}")


def _score_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("score")
    if value is None:
        return None
    numeric = float(value)
    if 0 <= numeric <= 1:
        numeric *= 100
    return int(round(numeric))


def _target_from_row(row: dict[str, Any]) -> RefreshTarget:
    latest_opportunity_score = row.get("latest_opportunity_score")
    return RefreshTarget(
        id=str(row["id"]),
        policy_id=str(row["policy_id"]),
        niche_keyword=str(row["niche_keyword"]),
        niche_normalized=str(row["niche_normalized"]),
        cbsa_code=str(row["cbsa_code"]),
        cbsa_name=str(row["cbsa_name"]),
        state=row.get("state"),
        latest_report_id=row.get("latest_report_id"),
        latest_scored_at=_parse_dt(row.get("latest_scored_at")),
        next_refresh_at=_parse_dt(row.get("next_refresh_at")),
        latest_opportunity_score=(
            int(latest_opportunity_score) if latest_opportunity_score is not None else None
        ),
    )


def _non_empty_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item not in (None, "")]
    return [value] if value != "" else []


def _matching_metro(report: dict[str, Any], cbsa_code: str) -> dict[str, Any] | None:
    for metro in report.get("metros", []):
        if str(metro.get("cbsa_code")) == str(cbsa_code):
            return metro
    return None


def _expanded_keywords(report: dict[str, Any]) -> list[dict[str, Any]]:
    keyword_expansion = report.get("keyword_expansion") or {}
    keywords = keyword_expansion.get("expanded_keywords", [])
    return keywords if isinstance(keywords, list) else []


def _flatten_signal_buckets(signals: dict[str, Any]) -> dict[str, Any]:
    flattened = dict(signals)
    for key in (
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
    ):
        value = signals.get(key)
        if isinstance(value, dict):
            flattened.update(value)
    return flattened


def _niche_normalized(report: dict[str, Any], metro: dict[str, Any] | None = None) -> str:
    v2_scores = (metro or {}).get("v2_scores") or {}
    v2_niche = v2_scores.get("niche_normalized")
    if isinstance(v2_niche, str) and v2_niche.strip():
        return v2_niche.strip().lower()
    return str(report.get("input", {}).get("niche_keyword", "")).strip().lower()


def _snapshot_date(report: dict[str, Any]) -> str | None:
    try:
        parsed = _parse_dt(report.get("generated_at"))
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date().isoformat()


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _json_object_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bool_or_false(value: Any) -> bool:
    return bool(value) if value is not None else False


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return bool(value)


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [
        text
        for item in _list_or_empty(value)
        if (text := _str_or_none(item))
    ]


def _categories_from_item(item: dict[str, Any]) -> list[str]:
    categories: list[str] = []
    for key in ("categories", "additional_categories", "services"):
        for category in _list_or_empty(item.get(key)):
            text = _str_or_none(category)
            if text:
                categories.append(text)

    category = _str_or_none(item.get("category"))
    if category:
        categories.append(category)

    return list(dict.fromkeys(categories))


def _rank_or_index(item: dict[str, Any], index: int, *keys: str) -> int:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        try:
            rank = int(value)
        except (TypeError, ValueError):
            continue
        if rank > 0:
            return rank
    return index


def _rating_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    return _float_or_none(value)


def _review_count(item: dict[str, Any]) -> int | None:
    rating = item.get("rating")
    if isinstance(rating, dict) and rating.get("votes_count") is not None:
        return _int_or_none(rating.get("votes_count"))
    return _int_or_none(
        item.get(
            "review_count",
            item.get("reviews_count", item.get("votes_count")),
        )
    )


def _domain_from_item(item: dict[str, Any]) -> str | None:
    domain = normalize_domain(
        str(
            item.get("domain")
            or item.get("listing_url")
            or item.get("url")
            or item.get("target")
            or ""
        )
    )
    return domain or None


def _source_fact_items(
    sources: list[Any],
    *,
    default_keyword: str | None,
    accepted_types: set[str] | None = None,
) -> list[tuple[dict[str, Any], str | None]]:
    items: list[tuple[dict[str, Any], str | None]] = []
    for source in sources:
        if isinstance(source, dict) and isinstance(source.get("items"), list):
            source_keyword = _str_or_none(source.get("keyword")) or default_keyword
            for item in source["items"]:
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("type", "")).lower()
                if accepted_types and item_type and item_type not in accepted_types:
                    continue
                items.append((item, _str_or_none(item.get("keyword")) or source_keyword))
        elif isinstance(source, dict):
            item_type = str(source.get("type", "")).lower()
            if accepted_types and item_type and item_type not in accepted_types:
                continue
            items.append((source, _str_or_none(source.get("keyword")) or default_keyword))
        elif isinstance(source, list):
            items.extend(
                _source_fact_items(
                    source,
                    default_keyword=default_keyword,
                    accepted_types=accepted_types,
                )
            )
    return items


def _artifact_sources(report: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for key in _EVIDENCE_ARTIFACT_COLLECTION_KEYS:
        value = report.get(key)
        if isinstance(value, list):
            artifacts.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            artifacts.append(value)

    for metro in report.get("metros", []):
        if not isinstance(metro, dict):
            continue
        for key in _EVIDENCE_ARTIFACT_COLLECTION_KEYS:
            value = metro.get(key)
            if isinstance(value, list):
                artifacts.extend(item for item in value if isinstance(item, dict))
            elif isinstance(value, dict):
                artifacts.append(value)

    return artifacts


def _artifact_endpoint_path(artifact: dict[str, Any]) -> str | None:
    return _str_or_none(
        artifact.get(
            "endpoint_path",
            artifact.get("endpoint", artifact.get("path")),
        )
    )


def _artifact_evidence_family(artifact: dict[str, Any]) -> str | None:
    return _str_or_none(
        artifact.get(
            "evidence_family",
            artifact.get("family", artifact.get("artifact_type")),
        )
    )


def _artifact_request_params(artifact: dict[str, Any]) -> dict[str, Any]:
    return _json_object_or_empty(
        artifact.get(
            "normalized_request_params",
            artifact.get("request_params", artifact.get("params")),
        )
    )


def _artifact_response_payload(artifact: dict[str, Any]) -> Any:
    for key in ("response_payload", "payload", "response"):
        if key in artifact:
            return artifact[key]
    return None


def _normalize_evidence_family(
    value: Any,
    endpoint_path: str | None,
) -> str | None:
    text = _str_or_none(value)
    if text:
        normalized = text.strip().lower().replace("-", "_")
        if normalized in _ALLOWED_EVIDENCE_FAMILIES:
            return normalized
    return evidence_family_from_endpoint(endpoint_path)


def _normalize_cache_status(value: Any) -> str:
    text = _str_or_none(value)
    if not text:
        return "unknown"
    normalized = text.strip().lower().replace("-", "_")
    return normalized if normalized in _ALLOWED_CACHE_STATUSES else "unknown"


def _record_value(record: Any, key: str) -> Any:
    if isinstance(record, dict):
        return record.get(key)
    return getattr(record, key, None)


def evidence_family_from_endpoint(endpoint_path: str | None) -> str | None:
    """Map known DataForSEO endpoint paths to benchmark evidence families."""
    endpoint = (endpoint_path or "").strip().lower().lstrip("/")
    if not endpoint:
        return None
    if "keywords_data/google/search_volume" in endpoint:
        return "keyword_volume"
    if (
        "dataforseo_labs/google/keyword" in endpoint
        or "keyword_overview" in endpoint
        or "keywords_data/google_trends" in endpoint
    ):
        return "keyword_overview"
    if "serp/google/maps" in endpoint:
        return "maps"
    if "serp/google/organic" in endpoint:
        return "serp"
    if "business_data/google/reviews" in endpoint:
        return "reviews"
    if endpoint.startswith("backlinks/") or "/backlinks/" in endpoint:
        return "backlinks"
    if "on_page/lighthouse" in endpoint:
        return "lighthouse"
    if (
        "business_data/google/my_business_info" in endpoint
        or "business_data/business_listings" in endpoint
    ):
        return "maps"
    return None


def _primary_keyword(report: dict[str, Any]) -> str | None:
    keywords = _expanded_keywords(report)
    if keywords:
        return _str_or_none(keywords[0].get("keyword"))
    return _str_or_none(report.get("input", {}).get("niche_keyword"))


def _require_upsert(table: Any, table_name: str) -> Any:
    if not hasattr(table, "upsert"):
        raise RuntimeError(
            f"Cannot persist {table_name}: Supabase table client lacks upsert; "
            "idempotent writes are required."
        )
    return table


def _keyword_tier(value: Any) -> int:
    try:
        tier = int(value)
    except (TypeError, ValueError):
        return 3
    return tier if tier in {1, 2, 3} else 3


def _keyword_intent(value: Any) -> str:
    if isinstance(value, str):
        intent = value.strip().lower()
        if intent in {"transactional", "commercial", "informational"}:
            return intent
    return "informational"


def _score_value(v2_scores: dict[str, Any], dimension: str) -> Any:
    dimension_score = (v2_scores.get("scores") or {}).get(dimension) or {}
    if isinstance(dimension_score, dict):
        return dimension_score.get("value")
    return None


def _without_artifact_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_artifact_keys(item)
            for key, item in value.items()
            if key not in _PRIVATE_PERSISTENCE_KEYS
        }
    if isinstance(value, list):
        return [_without_artifact_keys(item) for item in value]
    return deepcopy(value)


def build_report_row(report: dict[str, Any]) -> dict[str, Any]:
    run_input = report["input"]
    return {
        "id": report["report_id"],
        "created_at": report["generated_at"],
        "spec_version": report["spec_version"],
        "niche_keyword": run_input["niche_keyword"],
        "geo_scope": run_input["geo_scope"],
        "geo_target": run_input["geo_target"],
        "report_depth": run_input.get("report_depth", "standard"),
        "strategy_profile": run_input.get("strategy_profile", "balanced"),
        "resolved_weights": (
            report["metros"][0]["scores"].get("resolved_weights") if report["metros"] else None
        ),
        "keyword_expansion": _without_artifact_keys(report["keyword_expansion"]),
        "metros": _without_artifact_keys(report["metros"]),
        "meta": _without_artifact_keys(report["meta"]),
        "feedback_log_id": report["meta"].get("feedback_log_id"),
        "owner_account_id": report.get("owner_account_id"),
        "created_by_user_id": report.get("created_by_user_id"),
        "access_scope": report.get(
            "access_scope",
            "account" if report.get("owner_account_id") else "cached",
        ),
    }


def build_keyword_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    keywords = _expanded_keywords(report)
    rows: list[dict[str, Any]] = []
    for kw in keywords:
        rows.append(
            {
                "report_id": report_id,
                "keyword": kw["keyword"],
                "tier": int(kw.get("tier", 3)),
                "intent": kw.get("intent", "informational"),
                "source": kw.get("source", "llm"),
                "aio_risk": kw.get("aio_risk", "low"),
                "search_volume": kw.get("search_volume"),
                "cpc": kw.get("cpc"),
            }
        )
    return rows


def build_metro_signal_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    for metro in report["metros"]:
        signals = metro.get("signals") or {}
        rows.append(
            {
                "report_id": report_id,
                "cbsa_code": metro["cbsa_code"],
                "cbsa_name": metro["cbsa_name"],
                "demand": signals.get("demand"),
                "organic_competition": signals.get("organic_competition"),
                "local_competition": signals.get("local_competition"),
                "ai_resilience": signals.get("ai_resilience"),
                "monetization": signals.get("monetization"),
            }
        )
    return rows


def build_metro_score_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build metro_scores rows matching 001_core_schema.sql:55-71.

    Schema columns (adjusted from plan draft):
      - confidence_score INT  (plan used 'confidence' float — converted to int 0-100)
      - confidence_flags JSONB  (plan omitted — populated from scores if present)
      - guidance JSONB  (plan omitted — populated from metro.guidance)
    """
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    for metro in report["metros"]:
        scores = metro["scores"]
        raw_confidence = scores.get("confidence", {})
        if isinstance(raw_confidence, dict):
            confidence_score = int(round(float(raw_confidence.get("score", 0))))
            confidence_flags = raw_confidence.get("flags")
        else:
            confidence_score = int(round(float(raw_confidence) * 100))
            confidence_flags = scores.get("confidence_flags")
        rows.append(
            {
                "report_id": report_id,
                "cbsa_code": metro["cbsa_code"],
                "demand_score": int(round(scores["demand"])),
                "organic_competition_score": int(round(scores["organic_competition"])),
                "local_competition_score": int(round(scores["local_competition"])),
                "monetization_score": int(round(scores["monetization"])),
                "ai_resilience_score": int(round(scores["ai_resilience"])),
                "opportunity_score": int(round(scores["opportunity"])),
                "confidence_score": confidence_score,
                "confidence_flags": confidence_flags,
                "serp_archetype": metro["serp_archetype"],
                "ai_exposure": metro["ai_exposure"],
                "difficulty_tier": metro["difficulty_tier"],
                "guidance": metro.get("guidance"),
            }
        )
    return rows


def build_metro_score_v2_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build rows for public.metro_score_v2 from attached V2 score vectors."""
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    dimensions = (
        "demand_strength",
        "organic_difficulty",
        "local_difficulty",
        "monetization_signal",
        "ai_resilience",
    )
    for metro in report.get("metros", []):
        v2_scores = metro.get("v2_scores")
        if not isinstance(v2_scores, dict):
            continue

        row: dict[str, Any] = {
            "report_id": report_id,
            "niche_normalized": _niche_normalized(report, metro),
            "cbsa_code": v2_scores.get("cbsa_code") or metro.get("cbsa_code"),
            "serp_archetype": metro.get("serp_archetype"),
            "ai_exposure": metro.get("ai_exposure"),
            "spec_version": v2_scores.get("spec_version", "2.0"),
        }

        score_map = v2_scores.get("scores") or {}
        for dimension in dimensions:
            row[dimension] = _score_value(v2_scores, dimension)
            dimension_score = score_map.get(dimension) or {}
            if (
                isinstance(dimension_score, dict)
                and "higher_is_better" in dimension_score
            ):
                row[f"{dimension}_higher_is_better"] = bool(
                    dimension_score["higher_is_better"]
                )

        benchmark = v2_scores.get("benchmark") or {}
        if isinstance(benchmark, dict):
            row["benchmark_population_class"] = benchmark.get("population_class")
            row["benchmark_confidence"] = benchmark.get("confidence_label")
            row["benchmark_sample_size"] = benchmark.get("sample_size")

        flags = v2_scores.get("flags") or {}
        if isinstance(flags, dict):
            row["no_local_pack_detected"] = bool(
                flags.get("no_local_pack_detected", False)
            )
            row["benchmark_undersampled"] = bool(
                flags.get("benchmark_undersampled", False)
            )
            row["cbp_data_missing"] = bool(flags.get("cbp_data_missing", False))

        rows.append(row)
    return rows


def build_seo_fact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build denormalized keyword-level facts for public.seo_facts."""
    report_id = report["report_id"]
    niche_keyword = report.get("input", {}).get("niche_keyword")
    snapshot_date = _snapshot_date(report)
    rows: list[dict[str, Any]] = []

    for metro in report.get("metros", []):
        if not isinstance(metro.get("v2_scores"), dict):
            continue
        if snapshot_date is None:
            raise ValueError("generated_at is required for seo_facts snapshot_date")
        signals = _flatten_signal_buckets(metro.get("signals") or {})
        niche_normalized = _niche_normalized(report, metro)
        for keyword in _expanded_keywords(report):
            row = {
                "niche_keyword": niche_keyword,
                "niche_normalized": niche_normalized,
                "cbsa_code": metro.get("cbsa_code"),
                "keyword": keyword["keyword"],
                "keyword_tier": _keyword_tier(keyword.get("tier")),
                "intent": _keyword_intent(keyword.get("intent")),
                "search_volume_monthly": keyword.get("search_volume"),
                "cpc_usd": keyword.get("cpc"),
                "aio_present": signals.get("aio_present"),
                "local_pack_present": signals.get("local_pack_present"),
                "local_pack_position": signals.get("local_pack_position"),
                "aggregator_count_top10": _int_or_none(
                    signals.get("aggregator_count_top10", signals.get("aggregator_count"))
                ),
                "local_biz_count_top10": _int_or_none(
                    signals.get("local_biz_count_top10", signals.get("local_biz_count"))
                ),
                "featured_snippet_present": signals.get("featured_snippet_present"),
                "paa_count": signals.get("paa_count"),
                "ads_present": signals.get("ads_present", signals.get("ads_top_present")),
                "lsa_present": signals.get("lsa_present"),
                "top3_review_count_min": _int_or_none(
                    signals.get("top3_review_count_min")
                ),
                "top3_review_count_avg": _int_or_none(
                    signals.get(
                        "top3_review_count_avg",
                        signals.get("local_pack_review_count_avg"),
                    )
                ),
                "top3_review_velocity_avg": signals.get("top3_review_velocity_avg"),
                "top3_rating_avg": signals.get("top3_rating_avg"),
                "avg_top5_da": _float_or_none(signals.get("avg_top5_da")),
                "avg_top5_lighthouse": _float_or_none(
                    signals.get("avg_top5_lighthouse")
                ),
                "top5_da_coverage": _float_or_none(signals.get("top5_da_coverage")),
                "top5_lighthouse_coverage": _float_or_none(
                    signals.get("top5_lighthouse_coverage")
                ),
                "top5_organic_data_confidence": signals.get(
                    "top5_organic_data_confidence"
                ),
                "snapshot_date": snapshot_date,
                "report_id": report_id,
                "source": "orchestrator",
            }
            rows.append(row)

    return rows


def build_seo_evidence_artifact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build raw benchmark evidence artifacts from optional provenance payloads."""
    rows: list[dict[str, Any]] = []
    for artifact in _artifact_sources(report):
        endpoint_path = _artifact_endpoint_path(artifact)
        evidence_family = _normalize_evidence_family(
            _artifact_evidence_family(artifact),
            endpoint_path,
        )
        if not endpoint_path or not evidence_family:
            continue

        provider = _str_or_none(artifact.get("provider")) or "dataforseo"
        normalized_request_params = _artifact_request_params(artifact)
        request_hash = _str_or_none(artifact.get("request_hash"))
        if request_hash is None:
            request_hash = _sha256_json(
                {
                    "provider": provider,
                    "endpoint_path": endpoint_path,
                    "normalized_request_params": normalized_request_params,
                }
            )

        response_payload = _artifact_response_payload(artifact)
        response_hash = _str_or_none(artifact.get("response_hash"))
        if response_hash is None and response_payload is not None:
            response_hash = _sha256_json(response_payload)

        row: dict[str, Any] = {
            "provider": provider,
            "endpoint_path": endpoint_path,
            "evidence_family": evidence_family,
            "normalized_request_params": normalized_request_params,
            "request_hash": request_hash,
            "response_hash": response_hash,
            "response_storage_uri": _str_or_none(
                artifact.get(
                    "response_storage_uri",
                    artifact.get("storage_uri", artifact.get("response_uri")),
                )
            ),
            "response_payload": response_payload,
            "cache_status": _normalize_cache_status(artifact.get("cache_status")),
        }

        artifact_id = _str_or_none(artifact.get("id", artifact.get("artifact_id")))
        if artifact_id:
            row["id"] = artifact_id
        else:
            row["id"] = _deterministic_evidence_artifact_id(
                provider,
                endpoint_path,
                request_hash,
            )

        cost_usd = artifact.get("cost_usd", artifact.get("cost"))
        if cost_usd is not None:
            row["cost_usd"] = _float_or_none(cost_usd)

        for source_key, destination_key in (
            ("collection_timestamp", "collected_at"),
            ("collected_at", "collected_at"),
            ("source_window_start", "source_window_start"),
            ("source_window_end", "source_window_end"),
        ):
            if source_key in artifact and artifact[source_key] is not None:
                row[destination_key] = artifact[source_key]

        rows.append(row)

    return rows


def build_seo_evidence_artifact_rows_from_cost_records(
    cost_records: Sequence[Any],
) -> list[dict[str, Any]]:
    """Build raw evidence metadata rows from DataForSEO cost records."""
    artifacts: list[dict[str, Any]] = []
    for record in cost_records:
        endpoint_path = _str_or_none(_record_value(record, "endpoint"))
        evidence_family = evidence_family_from_endpoint(endpoint_path)
        if endpoint_path is None or evidence_family is None:
            continue

        cached = _record_value(record, "cached")
        if cached is True:
            cache_status = "hit"
        elif cached is False:
            cache_status = "miss"
        else:
            cache_status = "unknown"

        artifact: dict[str, Any] = {
            "provider": "dataforseo",
            "endpoint_path": endpoint_path,
            "evidence_family": evidence_family,
            "normalized_request_params": _json_object_or_empty(
                _record_value(record, "parameters")
            ),
            "cache_status": cache_status,
        }

        cost = _record_value(record, "cost")
        if cost is not None:
            artifact["cost_usd"] = cost

        collected_at = _record_value(record, "collected_at")
        if collected_at is not None:
            artifact["collected_at"] = collected_at

        collection_context_id = _record_value(record, "collection_context_id")
        if collection_context_id is not None:
            artifact["collection_context_id"] = collection_context_id

        response_hash = _record_value(record, "response_hash")
        if response_hash is not None:
            artifact["response_hash"] = response_hash

        response_storage_uri = _record_value(record, "response_storage_uri")
        if response_storage_uri is not None:
            artifact["response_storage_uri"] = response_storage_uri

        response_payload = _record_value(record, "response_payload")
        if response_payload is not None:
            artifact["response_payload"] = response_payload

        artifacts.append(artifact)

    rows = build_seo_evidence_artifact_rows({"seo_evidence_artifacts": artifacts})
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["provider"], row["endpoint_path"], row["request_hash"])
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = row
            continue
        existing_cost = _float_or_none(existing.get("cost_usd")) or 0.0
        row_cost = _float_or_none(row.get("cost_usd")) or 0.0
        if existing.get("cache_status") == "hit" and row.get("cache_status") == "miss":
            deduped[key] = row
        elif existing_cost == 0.0 and row_cost > 0.0:
            deduped[key] = row

    return list(deduped.values())


def _deterministic_evidence_artifact_id(
    provider: str,
    endpoint_path: str,
    request_hash: str,
) -> str:
    return str(uuid5(NAMESPACE_URL, f"seo-evidence:{provider}:{endpoint_path}:{request_hash}"))


def build_organic_competitor_fact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build top organic competitor read-model facts from compact report payloads."""
    report_id = report["report_id"]
    snapshot_date = _snapshot_date(report)
    default_keyword = _primary_keyword(report)
    rows: list[dict[str, Any]] = []

    for metro in report.get("metros", []):
        signals = metro.get("signals") or {}
        organic_signals = signals.get("organic_competition") or {}
        sources = [
            metro.get("organic_competitor_facts"),
            metro.get("organic_competitors"),
            metro.get("organic_results"),
            organic_signals.get("organic_competitor_facts"),
            organic_signals.get("organic_competitors"),
            organic_signals.get("top_organic_results"),
            organic_signals.get("organic_results"),
        ]
        items = _source_fact_items(
            sources,
            default_keyword=default_keyword,
            accepted_types={"organic", "featured_snippet"},
        )
        if items and snapshot_date is None:
            raise ValueError(
                "generated_at is required for organic_competitor_facts snapshot_date"
            )

        niche_normalized = _niche_normalized(report, metro)
        for index, (item, item_keyword) in enumerate(items, start=1):
            keyword = item_keyword or default_keyword
            if not keyword:
                continue

            domain = _domain_from_item(item)
            result_type = _str_or_none(item.get("type")) or "organic"
            evidence = {
                key: item[key]
                for key in ("breadcrumb", "description", "snippet")
                if item.get(key) not in (None, "")
            }
            rows.append(
                {
                    "cbsa_code": metro.get("cbsa_code"),
                    "niche_normalized": niche_normalized,
                    "keyword": keyword,
                    "result_rank": _rank_or_index(
                        item,
                        index,
                        "result_rank",
                        "rank_group",
                        "rank_absolute",
                        "position",
                        "rank",
                    ),
                    "title": _str_or_none(item.get("title")),
                    "domain": domain,
                    "url": _str_or_none(item.get("url")),
                    "result_type": result_type,
                    "domain_authority": _float_or_none(
                        item.get("domain_authority", item.get("da"))
                    ),
                    "backlinks_count": _int_or_none(
                        item.get(
                            "backlinks_count",
                            item.get("backlink_count", item.get("backlinks")),
                        )
                    ),
                    "referring_domains_count": _int_or_none(
                        item.get(
                            "referring_domains_count",
                            item.get("referring_domains", item.get("referringDomains")),
                        )
                    ),
                    "lighthouse_score": _float_or_none(
                        item.get(
                            "lighthouse_score",
                            item.get("performance_score", item.get("performance")),
                        )
                    ),
                    "has_localbusiness_schema": _bool_or_none(
                        item.get(
                            "has_localbusiness_schema",
                            item.get("schema_adoption", item.get("has_schema")),
                        )
                    ),
                    "schema_types": _string_list(
                        item.get("schema_types", item.get("schemaTypes"))
                    ),
                    "title_keyword_match": _bool_or_none(
                        item.get("title_keyword_match")
                    ),
                    "is_aggregator": _bool_or_false(
                        item.get("is_aggregator")
                    ) or is_aggregator(domain),
                    "is_local_business": _bool_or_false(item.get("is_local_business")),
                    "evidence": evidence,
                    "source": _str_or_none(item.get("source")) or "dataforseo",
                    "snapshot_date": snapshot_date,
                    "report_id": report_id,
                }
            )

    return rows


def build_local_pack_listing_fact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build local pack listing facts without reading the raw API cache table."""
    report_id = report["report_id"]
    snapshot_date = _snapshot_date(report)
    default_keyword = _primary_keyword(report)
    rows: list[dict[str, Any]] = []

    for metro in report.get("metros", []):
        cbsa_code = metro.get("cbsa_code")
        top_level_listing_facts = [
            item
            for item in report.get("local_pack_listing_facts", [])
            if isinstance(item, dict) and item.get("cbsa_code") == cbsa_code
        ]
        signals = metro.get("signals") or {}
        local_signals = signals.get("local_competition") or {}
        sources = [
            top_level_listing_facts,
            metro.get("local_pack_listing_facts"),
            metro.get("local_pack_listings"),
            metro.get("serp_maps"),
            local_signals.get("local_pack_listing_facts"),
            local_signals.get("local_pack_listings"),
            local_signals.get("top_local_pack_items"),
            local_signals.get("serp_maps"),
        ]
        items = _source_fact_items(
            sources,
            default_keyword=default_keyword,
            accepted_types={"local_pack", "maps_search", "google_business_info"},
        )
        if items and snapshot_date is None:
            raise ValueError(
                "generated_at is required for local_pack_listing_facts snapshot_date"
            )

        niche_normalized = _niche_normalized(report, metro)
        for index, (item, item_keyword) in enumerate(items, start=1):
            keyword = item_keyword or default_keyword
            business_name = _str_or_none(
                item.get("business_name", item.get("title", item.get("name")))
            )
            if not keyword or not business_name:
                continue

            photos = item.get("photos")
            listing_url = _str_or_none(item.get("listing_url", item.get("url")))
            rows.append(
                {
                    "cbsa_code": cbsa_code,
                    "niche_normalized": niche_normalized,
                    "keyword": keyword,
                    "listing_rank": _rank_or_index(
                        item,
                        index,
                        "listing_rank",
                        "rank_group",
                        "rank_absolute",
                        "position",
                        "rank",
                    ),
                    "business_name": business_name,
                    "cid": _str_or_none(item.get("cid")),
                    "place_id": _str_or_none(item.get("place_id")),
                    "source_query": _str_or_none(item.get("source_query")),
                    "dataforseo_location_code": _int_or_none(
                        item.get(
                            "dataforseo_location_code",
                            item.get("location_code"),
                        )
                    ),
                    "result_type": _str_or_none(
                        item.get("result_type", item.get("type"))
                    ),
                    "listing_url": listing_url,
                    "domain": _domain_from_item(item),
                    "review_retrieval_mode": _str_or_none(
                        item.get(
                            "review_retrieval_mode",
                            item.get("review_collection_mode"),
                        )
                    ),
                    "review_window_start": item.get("review_window_start"),
                    "review_window_end": item.get("review_window_end"),
                    "upstream_result_at": item.get("upstream_result_at"),
                    "evidence_artifact_id": _str_or_none(
                        item.get(
                            "evidence_artifact_id",
                            item.get("seo_evidence_artifact_id"),
                        )
                    ),
                    "exact_match_name": _bool_or_false(item.get("exact_match_name")),
                    "review_count": _review_count(item),
                    "review_velocity_monthly": _float_or_none(
                        item.get(
                            "review_velocity_monthly",
                            item.get("review_velocity_avg"),
                        )
                    ),
                    "rating": _rating_value(item.get("rating")),
                    "gbp_completeness": _float_or_none(item.get("gbp_completeness")),
                    "photo_count": _int_or_none(
                        item.get(
                            "photo_count",
                            item.get(
                                "total_photos",
                                len(photos) if isinstance(photos, list) else None,
                            ),
                        )
                    ),
                    "has_recent_post": item.get("has_recent_post"),
                    "categories": _categories_from_item(item),
                    "source": _str_or_none(item.get("source")) or "dataforseo",
                    "snapshot_date": snapshot_date,
                    "report_id": report_id,
                }
            )

    return rows


class SupabaseExploreRefreshStore:
    """Supabase-backed persistence for Explore refresh orchestration."""

    def __init__(self, *, client: _SupabaseLike) -> None:
        self._client = client

    def _targets_from_rows(self, rows: list[dict[str, Any]]) -> list[RefreshTarget]:
        if not rows:
            return []

        scores_by_target = self._latest_opportunity_scores(
            [str(row["id"]) for row in rows]
        )
        enriched_rows: list[dict[str, Any]] = []
        for row in rows:
            target_id = str(row["id"])
            row_with_score = dict(row)
            if target_id in scores_by_target:
                row_with_score["latest_opportunity_score"] = scores_by_target[target_id]
            enriched_rows.append(row_with_score)
        return [_target_from_row(row) for row in enriched_rows]

    def _latest_opportunity_scores(self, target_ids: Sequence[str]) -> dict[str, int | None]:
        if not target_ids:
            return {}

        result = (
            self._client.table("explore_latest_target_scores")
            .select("target_id,opportunity_score")
            .in_("target_id", list(target_ids))
            .execute()
        )
        rows = _result_rows(result)
        return {
            str(row["target_id"]): (
                int(row["opportunity_score"])
                if row.get("opportunity_score") is not None
                else None
            )
            for row in rows
        }

    def list_due_targets(self, now: datetime, limit: int) -> list[RefreshTarget]:
        if limit <= 0:
            return []
        result = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .eq("active", True)
            .lte("next_refresh_at", _iso_dt(now))
            .order("priority", desc=False)
            .limit(limit)
            .execute()
        )
        return self._targets_from_rows(_result_rows(result))

    def create_run(self, payload: dict[str, Any]) -> str:
        result = self._client.table("explore_refresh_runs").insert(payload).execute()
        rows = _result_rows(result)
        if not rows or not rows[0].get("id"):
            raise RuntimeError("Supabase create_run returned no run id")
        return str(rows[0]["id"])

    def create_run_items(
        self,
        run_id: str,
        targets: Sequence[RefreshTarget],
    ) -> None:
        rows = [
            {
                "run_id": run_id,
                "target_id": target.id,
                "old_report_id": target.latest_report_id,
                "status": "queued",
            }
            for target in targets
        ]
        if not rows:
            return
        result = self._client.table("explore_refresh_run_items").insert(rows).execute()
        _raise_on_error(result)

    def mark_run_running(self, run_id: str) -> None:
        result = (
            self._client.table("explore_refresh_runs")
            .update(
                {
                    "status": "running",
                    "started_at": _now_iso(),
                }
            )
            .eq("id", run_id)
            .execute()
        )
        _raise_on_error(result)

    def mark_item_succeeded(self, payload: dict[str, Any]) -> None:
        result = (
            self._client.table("explore_refresh_run_items")
            .update(
                {
                    "status": "succeeded",
                    "old_report_id": payload.get("old_report_id"),
                    "new_report_id": payload.get("new_report_id"),
                    "opportunity_before": payload.get("opportunity_before"),
                    "opportunity_after": payload.get("opportunity_after"),
                    "score_delta": payload.get("score_delta"),
                    "completed_at": _now_iso(),
                }
            )
            .eq("run_id", payload["run_id"])
            .eq("target_id", payload["target_id"])
            .execute()
        )
        _raise_on_error(result)

    def mark_item_failed(self, payload: dict[str, Any]) -> None:
        result = (
            self._client.table("explore_refresh_run_items")
            .update(
                {
                    "status": "failed",
                    "old_report_id": payload.get("old_report_id"),
                    "error_message": payload.get("error_message"),
                    "completed_at": _now_iso(),
                }
            )
            .eq("run_id", payload["run_id"])
            .eq("target_id", payload["target_id"])
            .execute()
        )
        _raise_on_error(result)

    def mark_run_complete(
        self,
        run_id: str,
        success_count: int,
        failure_count: int,
    ) -> None:
        if failure_count == 0:
            status = "succeeded"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial_failed"

        result = (
            self._client.table("explore_refresh_runs")
            .update(
                {
                    "status": status,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "completed_at": _now_iso(),
                }
            )
            .eq("id", run_id)
            .execute()
        )
        _raise_on_error(result)

    def upsert_target_after_success(
        self,
        *,
        target_id: str,
        policy_id: str,
        niche_keyword: str,
        niche_normalized: str,
        cbsa_code: str,
        cbsa_name: str,
        state: str | None,
        latest_report_id: str,
        latest_scored_at: datetime,
        next_refresh_at: datetime,
        latest_opportunity_score: int,
        opportunity_before: int | None,
        opportunity_after: int,
        score_delta: int | None,
        strategy_profile: str,
    ) -> None:
        result = (
            self._client.table("explore_refresh_targets")
            .update(
                {
                    "policy_id": policy_id,
                    "niche_keyword": niche_keyword,
                    "niche_normalized": niche_normalized,
                    "cbsa_code": cbsa_code,
                    "cbsa_name": cbsa_name,
                    "state": state,
                    "latest_report_id": latest_report_id,
                    "latest_scored_at": _iso_dt(latest_scored_at),
                    "next_refresh_at": _iso_dt(next_refresh_at),
                    "updated_at": _now_iso(),
                }
            )
            .eq("id", target_id)
            .execute()
        )
        _raise_on_error(result)

    def record_snapshot_from_report(
        self,
        *,
        run_id: str,
        target_id: str,
        report_id: str,
        report: dict[str, Any],
        niche_keyword: str,
        niche_normalized: str,
        cbsa_code: str,
        cbsa_name: str,
        state: str | None,
        strategy_profile: str,
        scored_at: datetime,
        opportunity_before: int | None,
        opportunity_after: int,
        score_delta: int | None,
    ) -> None:
        metro = _matching_metro(report, cbsa_code)
        scores = metro.get("scores", {}) if metro else {}
        meta = {
            "opportunity_before": opportunity_before,
            "opportunity_after": opportunity_after,
            "score_delta": score_delta,
            "source_report_id": report.get("report_id", report_id),
            "matched_metro": metro is not None,
        }
        if isinstance(report.get("meta"), dict):
            meta["report_meta"] = report["meta"]

        opportunity_score = _score_int(scores.get("opportunity"))
        if opportunity_score is None:
            opportunity_score = opportunity_after

        result = (
            self._client.table("explore_report_snapshots")
            .insert(
                {
                    "report_id": report_id,
                    "run_id": run_id,
                    "target_id": target_id,
                    "niche_keyword": niche_keyword,
                    "niche_normalized": niche_normalized,
                    "cbsa_code": cbsa_code,
                    "cbsa_name": cbsa_name,
                    "state": state,
                    "strategy_profile": strategy_profile,
                    "scored_at": _iso_dt(scored_at),
                    "opportunity_score": opportunity_score,
                    "demand_score": _score_int(scores.get("demand")),
                    "organic_competition_score": _score_int(
                        scores.get("organic_competition")
                    ),
                    "local_competition_score": _score_int(scores.get("local_competition")),
                    "monetization_score": _score_int(scores.get("monetization")),
                    "ai_resilience_score": _score_int(scores.get("ai_resilience")),
                    "confidence_score": _score_int(scores.get("confidence")),
                    "serp_archetype": metro.get("serp_archetype") if metro else None,
                    "ai_exposure": metro.get("ai_exposure") if metro else None,
                    "difficulty_tier": metro.get("difficulty_tier") if metro else None,
                    "meta": meta,
                }
            )
            .execute()
        )
        _raise_on_error(result)

    def list_targets_by_ids(self, target_ids: Sequence[str]) -> list[RefreshTarget]:
        if not target_ids:
            return []
        result = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .in_("id", list(target_ids))
            .execute()
        )
        return self._targets_from_rows(_result_rows(result))

    def list_targets_by_report_ids(
        self,
        report_ids: Sequence[str],
    ) -> list[RefreshTarget]:
        if not report_ids:
            return []
        result = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .in_("latest_report_id", list(report_ids))
            .execute()
        )
        return self._targets_from_rows(_result_rows(result))

    def list_targets_for_filters(
        self,
        filters: dict[str, Any],
        limit: int,
    ) -> list[RefreshTarget]:
        if limit <= 0:
            return []
        query = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .eq("active", True)
        )

        if filters.get("state"):
            query = query.eq("state", filters["state"])
        states = _non_empty_values(filters.get("states"))
        if states:
            query = query.in_("state", states)
        if filters.get("niche_normalized"):
            query = query.eq("niche_normalized", filters["niche_normalized"])
        if filters.get("niche"):
            query = query.eq("niche_keyword", filters["niche"])
        if filters.get("service"):
            query = query.eq("niche_keyword", filters["service"])
        if filters.get("cbsa_code"):
            query = query.eq("cbsa_code", filters["cbsa_code"])
        cbsa_codes = _non_empty_values(filters.get("cbsa_codes"))
        if cbsa_codes:
            query = query.in_("cbsa_code", cbsa_codes)

        result = query.order("priority", desc=False).limit(limit).execute()
        return self._targets_from_rows(_result_rows(result))

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        run_result = (
            self._client.table("explore_refresh_runs")
            .select("*")
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        run_rows = _result_rows(run_result)
        if not run_rows:
            return {"id": run_id, "status": "missing", "items": []}

        item_result = (
            self._client.table("explore_refresh_run_items")
            .select("*")
            .eq("run_id", run_id)
            .order("created_at", desc=False)
            .execute()
        )
        return {**run_rows[0], "items": _result_rows(item_result)}


class SupabasePersistence:
    """Writes an M9 report and its normalized children to Supabase."""

    def __init__(self, *, client: _SupabaseLike | None = None) -> None:
        if client is None:
            from supabase import create_client

            url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                missing = [v for v in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
                           if not os.environ.get(v)]
                raise RuntimeError(
                    f"Cannot persist report — missing env var(s): {', '.join(missing)}"
                )
            client = create_client(url, key)
        self._client = client

    @property
    def client(self) -> _SupabaseLike:
        return self._client

    def persist_report(self, report: dict[str, Any]) -> str:
        report_id = report["report_id"]
        persist_start = time.monotonic()
        logger.info("persist_report START report_id=%s", report_id)

        report_row = build_report_row(report)
        keyword_rows = build_keyword_rows(report)
        signal_rows = build_metro_signal_rows(report)
        score_rows = build_metro_score_rows(report)
        score_v2_rows = build_metro_score_v2_rows(report)
        fact_rows = build_seo_fact_rows(report)
        evidence_artifact_rows = build_seo_evidence_artifact_rows(report)
        organic_competitor_rows = build_organic_competitor_fact_rows(report)
        local_pack_rows = build_local_pack_listing_fact_rows(report)
        facts_table = None
        evidence_artifact_table = None
        organic_competitor_table = None
        local_pack_table = None
        if fact_rows:
            facts_table = _require_upsert(self._client.table("seo_facts"), "seo_facts")
        if evidence_artifact_rows:
            evidence_artifact_table = _require_upsert(
                self._client.table("seo_evidence_artifacts"),
                "seo_evidence_artifacts",
            )
        if organic_competitor_rows:
            organic_competitor_table = _require_upsert(
                self._client.table("organic_competitor_facts"),
                "organic_competitor_facts",
            )
        if local_pack_rows:
            local_pack_table = _require_upsert(
                self._client.table("local_pack_listing_facts"),
                "local_pack_listing_facts",
            )

        t0 = time.monotonic()
        self._client.table("reports").insert(report_row).execute()
        reports_ms = int((time.monotonic() - t0) * 1000)
        logger.info("persist_report inserted reports row for %s duration_ms=%d",
                     report_id, reports_ms)

        if keyword_rows:
            t0 = time.monotonic()
            self._client.table("report_keywords").insert(keyword_rows).execute()
            kw_ms = int((time.monotonic() - t0) * 1000)
            logger.info("persist_report inserted %d report_keywords rows duration_ms=%d",
                        len(keyword_rows), kw_ms)

        if signal_rows:
            t0 = time.monotonic()
            self._client.table("metro_signals").insert(signal_rows).execute()
            sig_ms = int((time.monotonic() - t0) * 1000)
            logger.info("persist_report inserted %d metro_signals rows duration_ms=%d",
                        len(signal_rows), sig_ms)

        if score_rows:
            t0 = time.monotonic()
            self._client.table("metro_scores").insert(score_rows).execute()
            score_ms = int((time.monotonic() - t0) * 1000)
            logger.info("persist_report inserted %d metro_scores rows duration_ms=%d",
                        len(score_rows), score_ms)

        if score_v2_rows:
            t0 = time.monotonic()
            self._client.table("metro_score_v2").upsert(
                score_v2_rows,
                on_conflict="report_id,cbsa_code",
            ).execute()
            score_v2_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "persist_report upserted %d metro_score_v2 rows duration_ms=%d",
                len(score_v2_rows),
                score_v2_ms,
            )

        if fact_rows:
            t0 = time.monotonic()
            if facts_table is None:
                raise RuntimeError(
                    "Cannot persist seo_facts: facts_table client was not initialized. "
                    "This is a bug; please report it."
                )
            facts_table.upsert(
                fact_rows,
                on_conflict="niche_normalized,cbsa_code,keyword,snapshot_date",
            ).execute()
            facts_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "persist_report upserted %d seo_facts rows duration_ms=%d",
                len(fact_rows),
                facts_ms,
            )

        if evidence_artifact_rows:
            t0 = time.monotonic()
            if evidence_artifact_table is None:
                raise RuntimeError(
                    "Cannot persist seo_evidence_artifacts: table client was not "
                    "initialized. This is a bug; please report it."
                )
            evidence_artifact_table.upsert(
                evidence_artifact_rows,
                on_conflict="provider,endpoint_path,request_hash",
                ignore_duplicates=True,
            ).execute()
            evidence_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "persist_report upserted %d seo_evidence_artifacts rows "
                "duration_ms=%d",
                len(evidence_artifact_rows),
                evidence_ms,
            )

        if organic_competitor_rows:
            t0 = time.monotonic()
            if organic_competitor_table is None:
                raise RuntimeError(
                    "Cannot persist organic_competitor_facts: table client was not "
                    "initialized. This is a bug; please report it."
                )
            organic_competitor_table.upsert(
                organic_competitor_rows,
                on_conflict=(
                    "cbsa_code,niche_normalized,keyword,result_rank,result_type,snapshot_date"
                ),
            ).execute()
            organic_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "persist_report upserted %d organic_competitor_facts rows "
                "duration_ms=%d",
                len(organic_competitor_rows),
                organic_ms,
            )

        if local_pack_rows:
            t0 = time.monotonic()
            if local_pack_table is None:
                raise RuntimeError(
                    "Cannot persist local_pack_listing_facts: table client was not "
                    "initialized. This is a bug; please report it."
                )
            local_pack_table.upsert(
                local_pack_rows,
                on_conflict=(
                    "cbsa_code,niche_normalized,keyword,listing_rank,snapshot_date"
                ),
            ).execute()
            local_pack_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "persist_report upserted %d local_pack_listing_facts rows duration_ms=%d",
                len(local_pack_rows),
                local_pack_ms,
            )

        total_ms = int((time.monotonic() - persist_start) * 1000)
        logger.info("persist_report DONE report_id=%s total_ms=%d", report_id, total_ms)
        return report_id
