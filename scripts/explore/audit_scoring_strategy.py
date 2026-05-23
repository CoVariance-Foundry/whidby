"""Comprehensive read-only scoring strategy coverage audit.

The audit builds an intended city-size x service matrix, overlays persisted
facts, V2 scores, benchmark cells, legacy scores, and Explore visibility, then
reports which scoring signals are reliable enough for production scoring.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAGE_SIZE = 1000
PRODUCTION_API_URL = "https://whidby-1.onrender.com"

DEFAULT_SERVICES = (
    "roofing",
    "plumbing",
    "hvac",
    "tree service",
    "auto repair",
    "water damage restoration",
    "electrician",
    "locksmith",
)
DEFAULT_POPULATION_CLASSES = (
    "medium_100_300k",
    "large_300k_1m",
    "metro_1m_5m",
    "mega_5m_plus",
)

REQUIRED_COLUMNS = {
    "metros": (
        "cbsa_code",
        "cbsa_name",
        "population",
        "population_class",
    ),
    "niche_naics_mapping": ("niche_normalized", "niche_keyword", "naics_code"),
    "seo_facts": (
        "cbsa_code",
        "niche_normalized",
        "intent",
        "search_volume_monthly",
        "cpc_usd",
        "aio_present",
        "local_pack_present",
        "aggregator_count_top10",
        "local_biz_count_top10",
        "paa_count",
        "ads_present",
        "lsa_present",
        "top3_review_count_min",
        "top3_review_velocity_avg",
        "avg_top5_da",
        "avg_top5_lighthouse",
        "top5_da_coverage",
        "top5_lighthouse_coverage",
        "report_id",
    ),
    "seo_benchmarks": (
        "niche_normalized",
        "population_class",
        "sample_size_metros",
        "confidence_label",
        "median_total_volume_per_capita",
        "median_avg_cpc",
        "median_aggregator_count",
        "median_local_biz_count",
        "median_top3_review_count_min",
        "median_top3_review_velocity",
        "median_establishments_per_100k",
        "median_lsa_present_rate",
        "median_ads_present_rate",
        "median_aio_trigger_rate",
    ),
    "metro_score_v2": (
        "niche_normalized",
        "cbsa_code",
        "report_id",
        "demand_strength",
        "organic_difficulty",
        "local_difficulty",
        "monetization_signal",
        "ai_resilience",
        "benchmark_confidence",
        "benchmark_sample_size",
        "no_local_pack_detected",
        "benchmark_undersampled",
        "cbp_data_missing",
    ),
    "explore_market_cells": (
        "cbsa_code",
        "niche_normalized",
        "report_id",
        "score_system",
        "benchmark_confidence",
        "demand_strength",
        "organic_difficulty",
        "local_difficulty",
        "monetization_signal",
        "ai_resilience_score",
        "business_density_per_1k",
    ),
    "reports": ("id", "niche_keyword"),
    "metro_scores": ("report_id", "cbsa_code", "opportunity_score"),
}

COMMERCIAL_INTENTS = {"transactional", "commercial"}
RELIABLE_STATUS = "reliable"
SPARSE_STATUS = "sparse"
MISSING_STATUS = "missing"
UNDERSAMPLED_STATUS = "undersampled"


def load_env(env_path: Path | None = None) -> None:
    """Load root .env values without overwriting already-exported values."""
    path = env_path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def supabase_project_ref(supabase_url: str) -> str | None:
    """Extract a project ref only from exact https://<ref>.supabase.co hosts."""
    parsed = urlparse(supabase_url.strip())
    if parsed.scheme != "https" or parsed.hostname is None:
        return None
    suffix = ".supabase.co"
    if not parsed.hostname.endswith(suffix):
        return None
    project_ref = parsed.hostname[: -len(suffix)]
    if not project_ref or "." in project_ref:
        return None
    return project_ref


def validate_expected_project_ref(expected_project_ref: str | None) -> None:
    """Fail closed before any production read/write if the project ref is wrong."""
    if not expected_project_ref:
        return
    actual_project_ref = supabase_project_ref(os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
    if actual_project_ref != expected_project_ref:
        actual = actual_project_ref or "<unknown>"
        raise RuntimeError(
            "Supabase project ref mismatch: "
            f"expected {expected_project_ref}, got {actual} from NEXT_PUBLIC_SUPABASE_URL"
        )


def supabase_client() -> Any:
    """Create a Supabase service-role client from local environment."""
    from supabase import create_client

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    missing = [
        name
        for name, value in (
            ("NEXT_PUBLIC_SUPABASE_URL", url),
            ("SUPABASE_SERVICE_ROLE_KEY", key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing Supabase environment variable(s): " + ", ".join(missing)
        )
    return create_client(url, key)


def fetch_pages(supabase: Any, table: str, columns: tuple[str, ...]) -> list[dict[str, Any]]:
    """Fetch a table using paginated select calls and surface schema drift clearly."""
    rows: list[dict[str, Any]] = []
    offset = 0
    select_columns = ",".join(columns)
    while True:
        try:
            response = (
                supabase.table(table)
                .select(select_columns)
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
        except Exception as exc:
            raise RuntimeError(
                f"{table} missing required column(s): {select_columns}; {exc}"
            ) from exc
        page = list(response.data or [])
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def normalize_service_key(raw: str) -> str:
    """Normalize service labels the same way operational seed commands do."""
    text = " ".join(raw.strip().lower().split())
    for suffix in (" services", " service", " contractors", " contractor", " companies", " company"):
        if text.endswith(suffix):
            return text[: -len(suffix)].strip()
    return text


def has_value(value: Any) -> bool:
    return value is not None and value != ""


def numeric_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def truthy_ratio(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if has_value(row.get(field))) / len(rows)


def average_numeric(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(numeric_value(row.get(field)) for row in rows) / len(rows)


def group_rows(
    rows: list[dict[str, Any]],
    key_fields: tuple[str, ...],
) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row.get(field) if row.get(field) is not None else "unknown") for field in key_fields)
        grouped[key].append(row)
    return grouped


def latest_by_pair(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Keep the last row seen for a CBSA/service pair."""
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        cbsa = str(row.get("cbsa_code") or "")
        niche = normalize_service_key(str(row.get("niche_normalized") or ""))
        if cbsa and niche:
            by_pair[(cbsa, niche)] = row
    return by_pair


def rows_by_pair(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cbsa = str(row.get("cbsa_code") or "")
        niche = normalize_service_key(str(row.get("niche_normalized") or ""))
        if cbsa and niche:
            by_pair[(cbsa, niche)].append(row)
    return by_pair


def build_legacy_pairs(
    reports: list[dict[str, Any]],
    metro_scores: list[dict[str, Any]],
) -> set[tuple[str, str]]:
    report_niches = {
        str(row.get("id")): normalize_service_key(str(row.get("niche_keyword") or ""))
        for row in reports
    }
    pairs: set[tuple[str, str]] = set()
    for row in metro_scores:
        cbsa = str(row.get("cbsa_code") or "")
        niche = report_niches.get(str(row.get("report_id") or ""))
        if cbsa and niche:
            pairs.add((cbsa, niche))
    return pairs


def select_metros(
    metros: list[dict[str, Any]],
    population_classes: tuple[str, ...],
) -> list[dict[str, Any]]:
    allowed = set(population_classes)
    selected = [
        row
        for row in metros
        if str(row.get("population_class") or "") in allowed
        and has_value(row.get("cbsa_code"))
    ]
    return sorted(
        selected,
        key=lambda row: (
            str(row.get("population_class") or ""),
            -(numeric_value(row.get("population"))),
            str(row.get("cbsa_code") or ""),
        ),
    )


def build_pairs(
    *,
    metros: list[dict[str, Any]],
    service_names: tuple[str, ...],
    data: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    facts_by_pair = rows_by_pair(data["seo_facts"])
    benchmarks = {
        (
            normalize_service_key(str(row.get("niche_normalized") or "")),
            str(row.get("population_class") or ""),
        ): row
        for row in data["seo_benchmarks"]
    }
    v2_by_pair = latest_by_pair(data["metro_score_v2"])
    explore_by_pair = latest_by_pair(data["explore_market_cells"])
    legacy_pairs = build_legacy_pairs(data["reports"], data["metro_scores"])
    catalog_services = {
        normalize_service_key(str(row.get("niche_normalized") or ""))
        for row in data["niche_naics_mapping"]
    }

    services = tuple(normalize_service_key(service) for service in service_names)
    missing_services = sorted(service for service in services if service not in catalog_services)

    pairs: list[dict[str, Any]] = []
    for metro in metros:
        cbsa = str(metro.get("cbsa_code") or "")
        population_class = str(metro.get("population_class") or "unknown")
        for service in services:
            key = (cbsa, service)
            facts = facts_by_pair.get(key, [])
            benchmark = benchmarks.get((service, population_class))
            v2 = v2_by_pair.get(key)
            explore = explore_by_pair.get(key)
            pairs.append(
                {
                    "cbsa_code": cbsa,
                    "cbsa_name": metro.get("cbsa_name"),
                    "population": metro.get("population"),
                    "population_class": population_class,
                    "niche_normalized": service,
                    "facts": facts,
                    "benchmark": benchmark,
                    "v2": v2,
                    "explore": explore,
                    "legacy_exists": key in legacy_pairs,
                }
            )
    return pairs, missing_services


def fact_has_commercial_volume(facts: list[dict[str, Any]]) -> float:
    for fact in facts:
        if (
            str(fact.get("intent") or "").lower() in COMMERCIAL_INTENTS
            and has_value(fact.get("search_volume_monthly"))
        ):
            return 1.0
    return 0.0


def fact_has_field(facts: list[dict[str, Any]], field: str) -> float:
    return 1.0 if any(has_value(fact.get(field)) for fact in facts) else 0.0


def fact_avg_numeric(facts: list[dict[str, Any]], field: str) -> float:
    return average_numeric(facts, field)


def benchmark_has(pair: dict[str, Any], field: str, *, min_sample_size: int) -> float:
    benchmark = pair.get("benchmark")
    if not isinstance(benchmark, dict):
        return 0.0
    if int(numeric_value(benchmark.get("sample_size_metros"))) < min_sample_size:
        return 0.0
    return 1.0 if has_value(benchmark.get(field)) else 0.0


def v2_has(pair: dict[str, Any], field: str) -> float:
    v2 = pair.get("v2")
    return 1.0 if isinstance(v2, dict) and has_value(v2.get(field)) else 0.0


def explore_has(pair: dict[str, Any], field: str) -> float:
    explore = pair.get("explore")
    return 1.0 if isinstance(explore, dict) and has_value(explore.get(field)) else 0.0


def explore_is_v2(pair: dict[str, Any]) -> float:
    explore = pair.get("explore")
    return 1.0 if isinstance(explore, dict) and explore.get("score_system") == "v2" else 0.0


def known_population(pair: dict[str, Any]) -> float:
    return 1.0 if has_value(pair.get("population")) else 0.0


def local_difficulty_signal(pair: dict[str, Any]) -> float:
    facts = pair["facts"]
    if not facts:
        return 0.0
    known_pack = any(has_value(fact.get("local_pack_present")) for fact in facts)
    if not known_pack:
        return 0.0
    any_pack = any(fact.get("local_pack_present") is True for fact in facts)
    if not any_pack:
        return 1.0
    return min(
        fact_has_field(facts, "top3_review_count_min"),
        fact_has_field(facts, "top3_review_velocity_avg"),
    )


def metric_definitions(min_benchmark_sample_size: int) -> list[dict[str, Any]]:
    return [
        {
            "component": "demand",
            "metric": "commercial_volume",
            "intention": "Commercial or transactional search demand exists for the market.",
            "value": lambda pair: fact_has_commercial_volume(pair["facts"]),
        },
        {
            "component": "demand",
            "metric": "cpc",
            "intention": "CPC evidence exists for monetizable demand.",
            "value": lambda pair: fact_has_field(pair["facts"], "cpc_usd"),
        },
        {
            "component": "demand",
            "metric": "population",
            "intention": "Population denominator exists for per-capita normalization.",
            "value": known_population,
        },
        {
            "component": "demand",
            "metric": "demand_benchmark",
            "intention": "Usable demand benchmark cell exists for this service and city size.",
            "value": lambda pair: benchmark_has(
                pair,
                "median_total_volume_per_capita",
                min_sample_size=min_benchmark_sample_size,
            ),
        },
        {
            "component": "organic",
            "metric": "aggregator_count",
            "intention": "SERP aggregator pressure is observed.",
            "value": lambda pair: fact_has_field(pair["facts"], "aggregator_count_top10"),
        },
        {
            "component": "organic",
            "metric": "local_biz_count",
            "intention": "SERP local-business density is observed.",
            "value": lambda pair: fact_has_field(pair["facts"], "local_biz_count_top10"),
        },
        {
            "component": "organic",
            "metric": "top5_da_value",
            "intention": "Top-5 DA value is available as organic telemetry.",
            "value": lambda pair: fact_has_field(pair["facts"], "avg_top5_da"),
        },
        {
            "component": "organic",
            "metric": "top5_lighthouse_value",
            "intention": "Top-5 Lighthouse value is available as organic telemetry.",
            "value": lambda pair: fact_has_field(pair["facts"], "avg_top5_lighthouse"),
        },
        {
            "component": "organic",
            "metric": "top5_da_measurement",
            "intention": "Top-5 DA measurement coverage is nonzero.",
            "value": lambda pair: fact_avg_numeric(pair["facts"], "top5_da_coverage"),
        },
        {
            "component": "organic",
            "metric": "top5_lighthouse_measurement",
            "intention": "Top-5 Lighthouse measurement coverage is nonzero.",
            "value": lambda pair: fact_avg_numeric(pair["facts"], "top5_lighthouse_coverage"),
        },
        {
            "component": "local",
            "metric": "local_pack_known",
            "intention": "Local-pack presence is known, including valid no-pack cases.",
            "value": lambda pair: fact_has_field(pair["facts"], "local_pack_present"),
        },
        {
            "component": "local",
            "metric": "local_difficulty_inputs",
            "intention": "Top-3 review floor and velocity exist when a local pack exists.",
            "value": local_difficulty_signal,
        },
        {
            "component": "local",
            "metric": "local_benchmark",
            "intention": "Usable local difficulty benchmark exists for this service and city size.",
            "value": lambda pair: benchmark_has(
                pair,
                "median_top3_review_count_min",
                min_sample_size=min_benchmark_sample_size,
            ),
        },
        {
            "component": "monetization",
            "metric": "ads_presence",
            "intention": "Paid search demand is observed.",
            "value": lambda pair: fact_has_field(pair["facts"], "ads_present"),
        },
        {
            "component": "monetization",
            "metric": "lsa_presence",
            "intention": "LSA presence is observed where applicable.",
            "value": lambda pair: fact_has_field(pair["facts"], "lsa_present"),
        },
        {
            "component": "monetization",
            "metric": "business_density",
            "intention": "CBP-backed business density is visible in Explore.",
            "value": lambda pair: explore_has(pair, "business_density_per_1k"),
        },
        {
            "component": "monetization",
            "metric": "monetization_benchmark",
            "intention": "Usable establishment-density benchmark exists.",
            "value": lambda pair: benchmark_has(
                pair,
                "median_establishments_per_100k",
                min_sample_size=min_benchmark_sample_size,
            ),
        },
        {
            "component": "ai_resilience",
            "metric": "aio_presence",
            "intention": "AIO presence is observed.",
            "value": lambda pair: fact_has_field(pair["facts"], "aio_present"),
        },
        {
            "component": "ai_resilience",
            "metric": "paa_density",
            "intention": "PAA density is observed.",
            "value": lambda pair: fact_has_field(pair["facts"], "paa_count"),
        },
        {
            "component": "ai_resilience",
            "metric": "intent_mix",
            "intention": "Keyword intent mix is available to estimate transactional ratio.",
            "value": lambda pair: fact_has_field(pair["facts"], "intent"),
        },
        {
            "component": "ai_resilience",
            "metric": "ai_score",
            "intention": "Persisted V2 AI resilience score exists.",
            "value": lambda pair: v2_has(pair, "ai_resilience"),
        },
        {
            "component": "app_surface",
            "metric": "v2_score_exists",
            "intention": "V2 score row exists for the market pair.",
            "value": lambda pair: 1.0 if isinstance(pair.get("v2"), dict) else 0.0,
        },
        {
            "component": "app_surface",
            "metric": "benchmark_confidence",
            "intention": "V2 score has benchmark confidence metadata.",
            "value": lambda pair: v2_has(pair, "benchmark_confidence"),
        },
        {
            "component": "app_surface",
            "metric": "explore_visible",
            "intention": "Explore read model has a report-backed row.",
            "value": lambda pair: explore_has(pair, "report_id"),
        },
        {
            "component": "app_surface",
            "metric": "explore_v2_preferred",
            "intention": "Explore prefers V2 rather than legacy fallback.",
            "value": explore_is_v2,
        },
    ]


def coverage_average(pairs: list[dict[str, Any]], value_fn: Any) -> float:
    if not pairs:
        return 0.0
    return sum(float(value_fn(pair)) for pair in pairs) / len(pairs)


def classify_metric(
    *,
    component: str,
    metric: str,
    overall: float,
    minimum_required_slice: float,
    reliable_threshold: float,
    slice_floor: float,
) -> tuple[str, str]:
    if "benchmark" in metric and minimum_required_slice < slice_floor:
        return UNDERSAMPLED_STATUS, "requires data acquisition"
    if overall == 0 and metric.startswith("top5_"):
        return MISSING_STATUS, "telemetry-only"
    if overall == 0:
        return MISSING_STATUS, "requires data acquisition"
    if overall >= reliable_threshold and minimum_required_slice >= slice_floor:
        return RELIABLE_STATUS, "keep scored"
    if metric.startswith("top5_"):
        return SPARSE_STATUS, "telemetry-only"
    if component == "app_surface":
        return SPARSE_STATUS, "requires data acquisition"
    return SPARSE_STATUS, "score with warning"


def summarize_metric(
    pairs: list[dict[str, Any]],
    definition: dict[str, Any],
    *,
    reliable_threshold: float,
    slice_floor: float,
) -> dict[str, Any]:
    value_fn = definition["value"]
    overall = round(coverage_average(pairs, value_fn), 4)

    by_population_class = {
        key[0]: round(coverage_average(rows, value_fn), 4)
        for key, rows in sorted(group_rows(pairs, ("population_class",)).items())
    }
    by_service = {
        key[0]: round(coverage_average(rows, value_fn), 4)
        for key, rows in sorted(group_rows(pairs, ("niche_normalized",)).items())
    }
    by_benchmark_cell = {
        "|".join(key): round(coverage_average(rows, value_fn), 4)
        for key, rows in sorted(group_rows(pairs, ("niche_normalized", "population_class")).items())
    }

    required_slice_values = list(by_population_class.values())
    minimum_required_slice = min(required_slice_values) if required_slice_values else 0.0
    status, recommendation = classify_metric(
        component=definition["component"],
        metric=definition["metric"],
        overall=overall,
        minimum_required_slice=minimum_required_slice,
        reliable_threshold=reliable_threshold,
        slice_floor=slice_floor,
    )
    return {
        "component": definition["component"],
        "metric": definition["metric"],
        "intention": definition["intention"],
        "overall_coverage": overall,
        "minimum_required_population_class_coverage": round(minimum_required_slice, 4),
        "status": status,
        "recommendation": recommendation,
        "by_population_class": by_population_class,
        "by_service": by_service,
        "by_benchmark_cell": by_benchmark_cell,
    }


def summarize_components(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for metric in metrics:
        grouped[metric["component"]].append(metric)
    summaries = []
    for component, component_metrics in sorted(grouped.items()):
        overall = sum(m["overall_coverage"] for m in component_metrics) / len(component_metrics)
        statuses = {m["status"] for m in component_metrics}
        if MISSING_STATUS in statuses:
            status = MISSING_STATUS
        elif UNDERSAMPLED_STATUS in statuses:
            status = UNDERSAMPLED_STATUS
        elif SPARSE_STATUS in statuses:
            status = SPARSE_STATUS
        else:
            status = RELIABLE_STATUS
        recommendations = sorted({m["recommendation"] for m in component_metrics})
        summaries.append(
            {
                "component": component,
                "average_coverage": round(overall, 4),
                "status": status,
                "recommendations": recommendations,
                "metrics": [m["metric"] for m in component_metrics],
            }
        )
    return summaries


def summarize_gaps(metrics: list[dict[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
    low_metrics = [
        metric
        for metric in metrics
        if metric["status"] != RELIABLE_STATUS
    ]
    low_metrics.sort(
        key=lambda metric: (
            metric["overall_coverage"],
            metric["minimum_required_population_class_coverage"],
            metric["component"],
            metric["metric"],
        )
    )
    return low_metrics[:limit]


def pair_identity(pair: dict[str, Any]) -> dict[str, Any]:
    return {
        "cbsa_code": pair["cbsa_code"],
        "cbsa_name": pair["cbsa_name"],
        "population_class": pair["population_class"],
        "niche_normalized": pair["niche_normalized"],
    }


def summarize_app_surface_gaps(
    pairs: list[dict[str, Any]],
    *,
    limit: int = 50,
) -> dict[str, Any]:
    missing_v2_pairs = [
        pair_identity(pair)
        for pair in pairs
        if not isinstance(pair.get("v2"), dict)
    ]
    legacy_only_pairs = [
        pair_identity(pair)
        for pair in pairs
        if pair.get("legacy_exists") is True and not isinstance(pair.get("v2"), dict)
    ]
    missing_explore_pairs = [
        pair_identity(pair)
        for pair in pairs
        if not isinstance(pair.get("explore"), dict)
    ]
    legacy_explore_pairs = [
        {
            **pair_identity(pair),
            "score_system": (pair.get("explore") or {}).get("score_system"),
        }
        for pair in pairs
        if isinstance(pair.get("explore"), dict)
        and (pair.get("explore") or {}).get("score_system") != "v2"
    ]
    return {
        "missing_v2_count": len(missing_v2_pairs),
        "legacy_only_count": len(legacy_only_pairs),
        "missing_explore_count": len(missing_explore_pairs),
        "legacy_explore_fallback_count": len(legacy_explore_pairs),
        "missing_v2_pairs": missing_v2_pairs[:limit],
        "legacy_only_pairs": legacy_only_pairs[:limit],
        "missing_explore_pairs": missing_explore_pairs[:limit],
        "legacy_explore_fallback_pairs": legacy_explore_pairs[:limit],
        "example_limit": limit,
    }


def classify_pilot_record(record: dict[str, Any]) -> str:
    """Classify one bulk_score JSONL row for audit reporting."""
    error = str(record.get("error") or "")
    persistence = record.get("persistence") or {}
    status = str(record.get("status") or "")
    if "schema" in error.lower() or "column" in error.lower() or "required but missing" in error.lower():
        return "schema_failure"
    if status == "success" and persistence.get("ok") is True:
        required_counts = (
            numeric_value(persistence.get("metro_scores_count")),
            numeric_value(persistence.get("metro_score_v2_count")),
            numeric_value(persistence.get("seo_facts_count")),
        )
        if persistence.get("report_exists") is True and all(count > 0 for count in required_counts):
            return "success"
        return "persistence_partial_failure"
    if status == "partial_failure" or persistence.get("ok") is False:
        return "persistence_partial_failure"
    return "api_failure"


def pilot_failure_summary(pilot_results: dict[str, Any] | None) -> str | None:
    if not pilot_results:
        return None
    by_status = pilot_results.get("by_status") or {}
    failure_counts = {
        status: count
        for status, count in sorted(by_status.items())
        if status != "success" and int(count) > 0
    }
    if not failure_counts:
        return None
    return "API pilot has non-success rows: " + ", ".join(
        f"{status}={count}" for status, count in failure_counts.items()
    )


def read_pilot_results(paths: list[Path]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(json.loads(line))
    by_status: dict[str, int] = defaultdict(int)
    by_population_class: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_service: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in records:
        classification = classify_pilot_record(record)
        by_status[classification] += 1
        request = record.get("request") or {}
        by_population_class[str(request.get("population_class") or "unknown")][classification] += 1
        by_service[normalize_service_key(str(request.get("service") or "unknown"))][classification] += 1
    return {
        "record_count": len(records),
        "by_status": dict(sorted(by_status.items())),
        "by_population_class": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_population_class.items())
        },
        "by_service": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_service.items())
        },
    }


def build_pilot_command(
    *,
    services: tuple[str, ...],
    expected_project_ref: str | None,
    api_url: str,
    cities: int,
    concurrency: int,
) -> str:
    service_args = " ".join(f"--service-name {json.dumps(service)}" for service in services)
    project_arg = f" --expected-project-ref {expected_project_ref}" if expected_project_ref else ""
    return (
        ".venv/bin/python scripts/explore/bulk_score.py --apply "
        f"--cities {cities} --concurrency {concurrency} --api-url {api_url} "
        "--require-v2-persistence --resume-v2 "
        f"{service_args}{project_arg} "
        "--results-path scripts/explore/scoring_strategy_pilot.jsonl"
    )


def build_report(
    *,
    data: dict[str, list[dict[str, Any]]],
    services: tuple[str, ...],
    population_classes: tuple[str, ...],
    reliable_threshold: float,
    slice_floor: float,
    min_benchmark_sample_size: int,
    expected_project_ref: str | None,
    api_url: str,
    pilot_cities: int,
    pilot_concurrency: int,
    pilot_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_metros = select_metros(data["metros"], population_classes)
    pairs, missing_services = build_pairs(
        metros=selected_metros,
        service_names=services,
        data=data,
    )
    metrics = [
        summarize_metric(
            pairs,
            definition,
            reliable_threshold=reliable_threshold,
            slice_floor=slice_floor,
        )
        for definition in metric_definitions(min_benchmark_sample_size)
    ]
    component_summaries = summarize_components(metrics)
    app_surface_gaps = summarize_app_surface_gaps(pairs)
    critical_failures = [
        f"{metric['component']}.{metric['metric']} is {metric['status']}"
        for metric in metrics
        if metric["status"] in {MISSING_STATUS, UNDERSAMPLED_STATUS}
    ]
    if missing_services:
        critical_failures.append(
            "service catalog missing: " + ", ".join(missing_services)
        )
    pilot_failure = pilot_failure_summary(pilot_results)
    if pilot_failure:
        critical_failures.append(pilot_failure)
    status = "fail" if critical_failures else "pass"
    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": generated_at,
        "status": status,
        "critical_failures": critical_failures,
        "config": {
            "services": list(services),
            "population_classes": list(population_classes),
            "reliable_threshold": reliable_threshold,
            "slice_floor": slice_floor,
            "min_benchmark_sample_size": min_benchmark_sample_size,
            "expected_project_ref": expected_project_ref,
            "api_url": api_url,
        },
        "inventory": {
            "metros_in_scope": len(selected_metros),
            "services_in_scope": len(services),
            "intended_market_pairs": len(pairs),
            "seo_fact_rows": len(data["seo_facts"]),
            "seo_benchmark_cells": len(data["seo_benchmarks"]),
            "metro_score_v2_rows": len(data["metro_score_v2"]),
            "explore_market_cell_rows": len(data["explore_market_cells"]),
            "missing_catalog_services": missing_services,
        },
        "component_summaries": component_summaries,
        "metrics": metrics,
        "top_gaps": summarize_gaps(metrics),
        "app_surface_gaps": app_surface_gaps,
        "pilot": {
            "recommended_command": build_pilot_command(
                services=services,
                expected_project_ref=expected_project_ref,
                api_url=api_url,
                cities=pilot_cities,
                concurrency=pilot_concurrency,
            ),
            "results": pilot_results,
        },
    }


def markdown_table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    if "component_summaries" not in report:
        lines = [
            "# Scoring Strategy Audit",
            "",
            f"- Generated: `{report.get('generated_at', '<unknown>')}`",
            f"- Status: `{report.get('status', 'fail')}`",
            "",
            "## Critical Failures",
            "",
            *[f"- {failure}" for failure in report.get("critical_failures", [])],
        ]
        return "\n".join(lines) + "\n"

    component_rows = [
        (
            item["component"],
            item["average_coverage"],
            item["status"],
            ", ".join(item["recommendations"]),
        )
        for item in report["component_summaries"]
    ]
    gap_rows = [
        (
            gap["component"],
            gap["metric"],
            gap["overall_coverage"],
            gap["minimum_required_population_class_coverage"],
            gap["status"],
            gap["recommendation"],
        )
        for gap in report["top_gaps"]
    ]
    lines = [
        "# Scoring Strategy Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: `{report['status']}`",
        f"- Intended pairs: `{report['inventory']['intended_market_pairs']}`",
        f"- Services: `{', '.join(report['config']['services'])}`",
        f"- Population classes: `{', '.join(report['config']['population_classes'])}`",
        "",
        "## Component Summary",
        "",
        markdown_table(
            ("Component", "Avg coverage", "Status", "Recommendations"),
            component_rows,
        ),
        "",
        "## Top Gaps",
        "",
        markdown_table(
            (
                "Component",
                "Metric",
                "Overall",
                "Min city-size slice",
                "Status",
                "Recommendation",
            ),
            gap_rows,
        ),
        "",
        "## App Surface Gaps",
        "",
        "```json",
        json.dumps(report["app_surface_gaps"], indent=2, sort_keys=True),
        "```",
        "",
        "## API Pilot",
        "",
        "Run after read-only gates are acceptable:",
        "",
        "```bash",
        report["pilot"]["recommended_command"],
        "```",
    ]
    if report["pilot"].get("results"):
        lines.extend(
            [
                "",
                "### Pilot Results",
                "",
                "```json",
                json.dumps(report["pilot"]["results"], indent=2, sort_keys=True),
                "```",
            ]
        )
    if report["critical_failures"]:
        lines.extend(
            [
                "",
                "## Critical Failures",
                "",
                *[f"- {failure}" for failure in report["critical_failures"]],
            ]
        )
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"scoring_audit_{timestamp}.json"
    markdown_path = output_dir / f"scoring_audit_{timestamp}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def fetch_audit_data(supabase: Any) -> dict[str, list[dict[str, Any]]]:
    return {
        table: fetch_pages(supabase, table, columns)
        for table, columns in REQUIRED_COLUMNS.items()
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Run the Supabase inventory audit without API calls. This script is read-only.",
    )
    parser.add_argument(
        "--expected-project-ref",
        default=None,
        help="Optional Supabase project ref guard for NEXT_PUBLIC_SUPABASE_URL.",
    )
    parser.add_argument(
        "--service-name",
        dest="service_names",
        action="append",
        default=None,
        help="Service to include in the intended matrix. Repeat for multiple services.",
    )
    parser.add_argument(
        "--population-class",
        dest="population_classes",
        action="append",
        default=None,
        help="Population class to include. Repeat for multiple classes.",
    )
    parser.add_argument(
        "--reliable-threshold",
        type=float,
        default=0.8,
        help="Overall coverage required for a metric to be reliable (default: 0.8).",
    )
    parser.add_argument(
        "--slice-floor",
        type=float,
        default=0.6,
        help="Minimum city-size slice coverage required for reliability (default: 0.6).",
    )
    parser.add_argument(
        "--min-benchmark-sample-size",
        type=int,
        default=8,
        help="Minimum sample_size_metros for usable benchmark cells (default: 8).",
    )
    parser.add_argument(
        "--api-url",
        default=PRODUCTION_API_URL,
        help=f"API base URL for the recommended pilot command (default: {PRODUCTION_API_URL}).",
    )
    parser.add_argument(
        "--pilot-cities",
        type=int,
        default=12,
        help="City count for the recommended API pilot command (default: 12).",
    )
    parser.add_argument(
        "--pilot-concurrency",
        type=int,
        default=3,
        help="Concurrency for the recommended API pilot command (default: 3).",
    )
    parser.add_argument(
        "--pilot-results",
        action="append",
        type=Path,
        default=None,
        help="Bulk score JSONL result file to include in API pilot analysis. Repeatable.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/scoring_audit"),
        help="Directory for JSON and Markdown audit reports.",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print JSON only and do not write report files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    services = tuple(
        normalize_service_key(service)
        for service in (args.service_names or DEFAULT_SERVICES)
    )
    population_classes = tuple(args.population_classes or DEFAULT_POPULATION_CLASSES)
    try:
        load_env()
        validate_expected_project_ref(args.expected_project_ref)
        pilot_results = read_pilot_results(args.pilot_results or []) if args.pilot_results else None
        report = build_report(
            data=fetch_audit_data(supabase_client()),
            services=services,
            population_classes=population_classes,
            reliable_threshold=args.reliable_threshold,
            slice_floor=args.slice_floor,
            min_benchmark_sample_size=args.min_benchmark_sample_size,
            expected_project_ref=args.expected_project_ref,
            api_url=args.api_url,
            pilot_cities=args.pilot_cities,
            pilot_concurrency=args.pilot_concurrency,
            pilot_results=pilot_results,
        )
    except RuntimeError as exc:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "fail",
            "critical_failures": [str(exc)],
        }

    print(json.dumps(report, indent=2, sort_keys=True))
    if not args.stdout_only:
        json_path, markdown_path = write_reports(report, args.output_dir)
        print(f"wrote_json={json_path}")
        print(f"wrote_markdown={markdown_path}")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
