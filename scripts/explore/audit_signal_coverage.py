"""Read-only DA/Lighthouse and benchmark coverage audit for Explore seeding."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.supabase_guard import (  # noqa: E402
    POSTGREST_API_ERROR_TYPES,
    is_postgrest_missing_column_error,
    supabase_project_ref,
)
from scripts.explore.audit_scoring_strategy import (  # noqa: E402
    METRIC_MISSING_STATUS,
    METRIC_READY_STATUS,
    METRIC_UNDERSAMPLED_STATUS,
    build_canary_guidance,
    normalize_service_key,
    summarize_metric_sufficiency,
    summarize_strategy_readiness,
)

PAGE_SIZE = 1000
DEFAULT_REQUIRED_SERVICES = (
    "roofing",
    "plumbing",
    "hvac",
    "tree service",
    "auto repair",
    "water damage restoration",
    "electrician",
    "locksmith",
)
DEFAULT_REQUIRED_POPULATION_CLASSES = (
    "micro_under_50k",
    "small_50_100k",
    "medium_100_300k",
    "large_300k_1m",
    "metro_1m_5m",
    "mega_5m_plus",
)

REQUIRED_COLUMNS = {
    "seo_facts": (
        "cbsa_code",
        "niche_normalized",
        "avg_top5_da",
        "avg_top5_lighthouse",
        "top5_da_coverage",
        "top5_lighthouse_coverage",
    ),
    "metros": ("cbsa_code", "cbsa_name", "population_class"),
    "seo_benchmarks": (
        "benchmark_run_id",
        "niche_normalized",
        "population_class",
        "last_recomputed_at",
        "fact_window_end",
        "sample_size_metros",
    ),
    "seo_benchmark_metric_sufficiency": (
        "benchmark_run_id",
        "niche_normalized",
        "population_class",
        "metric_family",
        "attempted_metros",
        "non_null_metros",
        "attempted_observations",
        "non_null_observations",
        "confidence_label",
        "source_endpoint",
        "source_window_start",
        "source_window_end",
        "created_at",
    ),
    "explore_market_cells": ("cbsa_code", "niche_normalized", "report_id", "score_system"),
}

ACCEPTANCE_GATE_LABELS = {
    "usable_benchmark_cells": "usable benchmark cell count",
    "metric_ready_cells": "metric-ready benchmark cell count",
    "explore_v2_rows": "Explore V2 row count",
}
METRIC_FAMILY_COLLECTION_FLAGS = {
    "organic_authority": ("--collect-organic-telemetry",),
    "lighthouse_site_quality": ("--collect-organic-telemetry",),
    "review_velocity": ("--collect-review-velocity", "--review-depth"),
    "gbp_profile": ("--collect-gbp-profile",),
}


def load_env(env_path: Path | None = None) -> None:
    path = env_path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def validate_expected_project_ref(expected_project_ref: str | None) -> None:
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
        except POSTGREST_API_ERROR_TYPES as exc:
            if not is_postgrest_missing_column_error(exc):
                raise
            raise RuntimeError(f"{table} missing required column(s): {select_columns}") from exc
        page = list(response.data or [])
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def coverage_ratio(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get(field) is not None) / len(rows)


def average_coverage(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    values = []
    for row in rows:
        value = row.get(field)
        if isinstance(value, int | float):
            values.append(float(value))
        else:
            values.append(0.0)
    return sum(values) / len(rows)


def numeric_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "fact_count": len(rows),
        "da_value_coverage": round(coverage_ratio(rows, "avg_top5_da"), 4),
        "lighthouse_value_coverage": round(
            coverage_ratio(rows, "avg_top5_lighthouse"),
            4,
        ),
        "avg_top5_da_coverage": round(average_coverage(rows, "top5_da_coverage"), 4),
        "avg_top5_lighthouse_coverage": round(
            average_coverage(rows, "top5_lighthouse_coverage"),
            4,
        ),
    }


def group_value(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if value is None or value == "":
        return "unknown"
    return str(value)


def group_summary(
    facts: list[dict[str, Any]],
    key_fields: tuple[str, ...],
    *,
    label: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        key = tuple(group_value(fact, field) for field in key_fields)
        grouped[key].append(fact)
    summaries = []
    for key, rows in sorted(grouped.items()):
        record = {field: value for field, value in zip(key_fields, key, strict=True)}
        record.update(summarize_group(rows))
        summaries.append(record)
    return [{"group": label, "rows": summaries}]


def count_explore_v2_rows(
    explore_cells: list[dict[str, Any]],
    *,
    metro_by_cbsa: Mapping[str, Mapping[str, Any]],
    required_benchmark_keys: set[tuple[str, str]],
) -> int:
    return sum(
        1
        for row in explore_cells
        if row.get("report_id")
        and str(row.get("score_system") or "").strip().lower() == "v2"
        and (
            normalize_service_key(str(row.get("niche_normalized") or "")),
            str(metro_by_cbsa.get(str(row.get("cbsa_code") or ""), {}).get("population_class") or ""),
        )
        in required_benchmark_keys
    )


def count_metric_ready_cells(
    metric_sufficiency: dict[str, Any] | None,
    *,
    required_benchmark_keys: set[tuple[str, str]],
) -> int:
    if metric_sufficiency is None:
        return 0
    metric_families = metric_sufficiency.get("metric_families") or ()
    return sum(
        1
        for cell in metric_sufficiency.get("cells", [])
        if (
            str(cell.get("niche_normalized") or ""),
            str(cell.get("population_class") or ""),
        )
        in required_benchmark_keys
        if len(cell.get("ready_metric_families") or []) == len(metric_families)
        and all(
            family.get("status") == METRIC_READY_STATUS
            for family in (cell.get("families") or {}).values()
        )
    )


def build_readiness_gates(
    *,
    usable_benchmark_cells: int,
    min_benchmark_cells: int,
    metric_ready_cells: int,
    min_metric_ready_cells: int,
    explore_v2_rows: int,
    min_explore_v2_rows: int,
) -> dict[str, Any]:
    counts = {
        "usable_benchmark_cells": usable_benchmark_cells,
        "metric_ready_cells": metric_ready_cells,
        "explore_v2_rows": explore_v2_rows,
    }
    minimums = {
        "usable_benchmark_cells": min_benchmark_cells,
        "metric_ready_cells": min_metric_ready_cells,
        "explore_v2_rows": min_explore_v2_rows,
    }
    blocking_checks = [
        name for name, minimum in minimums.items() if minimum > 0 and counts[name] < minimum
    ]
    return {
        "ready": not blocking_checks,
        "blocking_checks": blocking_checks,
        "counts": counts,
        "minimums": minimums,
    }


def build_required_benchmark_keys(
    *,
    services: tuple[str, ...] = DEFAULT_REQUIRED_SERVICES,
    population_classes: tuple[str, ...] = DEFAULT_REQUIRED_POPULATION_CLASSES,
) -> set[tuple[str, str]]:
    return {
        (normalize_service_key(service), population_class)
        for service in services
        for population_class in population_classes
    }


def collection_flags_for_metric_families(metric_families: list[str]) -> list[str]:
    flags: list[str] = []
    for family in metric_families:
        for flag in METRIC_FAMILY_COLLECTION_FLAGS.get(family, ()):
            if flag not in flags:
                flags.append(flag)
    return flags


def metric_gap_details_by_required_key(
    metric_sufficiency: dict[str, Any] | None,
    *,
    required_benchmark_keys: set[tuple[str, str]],
    min_benchmark_sample_size: int,
) -> dict[tuple[str, str], dict[str, int]]:
    if metric_sufficiency is None:
        return {}
    gaps: dict[tuple[str, str], dict[str, int]] = {}
    for cell in metric_sufficiency.get("cells", []):
        key = (
            str(cell.get("niche_normalized") or ""),
            str(cell.get("population_class") or ""),
        )
        if key not in required_benchmark_keys:
            continue
        gap_families = (
            set(cell.get("blocked_metric_families") or [])
            | set(cell.get("undersampled_metric_families") or [])
        )
        if gap_families:
            families = cell.get("families") or {}
            gaps[key] = {
                family: max(
                    0,
                    min_benchmark_sample_size
                    - int(numeric_value((families.get(family) or {}).get("non_null_metros"))),
                )
                for family in sorted(gap_families)
            }
    return gaps


def build_required_acquisition_plan(
    *,
    required_benchmark_keys: set[tuple[str, str]],
    benchmark_sample_sizes: dict[tuple[str, str], int],
    metric_sufficiency: dict[str, Any] | None,
    min_benchmark_sample_size: int,
) -> dict[str, Any]:
    metric_gaps = metric_gap_details_by_required_key(
        metric_sufficiency,
        required_benchmark_keys=required_benchmark_keys,
        min_benchmark_sample_size=min_benchmark_sample_size,
    )
    cells = []
    ready_cell_count = 0
    for niche, population_class in sorted(required_benchmark_keys):
        sample_size = benchmark_sample_sizes.get((niche, population_class), 0)
        needed_sample_metros = max(0, min_benchmark_sample_size - sample_size)
        metric_family_shortfalls = metric_gaps.get((niche, population_class), {})
        needs_metric_families = list(metric_family_shortfalls)
        if needed_sample_metros == 0 and not needs_metric_families:
            ready_cell_count += 1
            continue
        collection_flags = collection_flags_for_metric_families(needs_metric_families)
        acquisition_target_pairs = max(
            [needed_sample_metros, *metric_family_shortfalls.values(), 1]
            if needs_metric_families
            else [needed_sample_metros]
        )
        suggested_options: dict[str, Any] = {
            "niche": niche,
            "population_class": population_class,
            "sample_mode": "pilot",
            "limit_pairs": acquisition_target_pairs,
            "required_flags": ["--require-dfs", "--require-v2-persistence"],
            "paid_budget_required": True,
        }
        if "--collect-review-velocity" in collection_flags:
            suggested_options["review_depth"] = 10
        if "--collect-organic-telemetry" in collection_flags:
            suggested_options["organic_telemetry_limit"] = 5
        cells.append(
            {
                "niche_normalized": niche,
                "population_class": population_class,
                "current_sample_size": sample_size,
                "needed_sample_metros": needed_sample_metros,
                "needs_metric_families": needs_metric_families,
                "metric_family_shortfalls": metric_family_shortfalls,
                "collection_flags": collection_flags,
                "suggested_options": suggested_options,
            }
        )
    cells.sort(
        key=lambda cell: (
            -int(cell["needed_sample_metros"]),
            -len(cell["needs_metric_families"]),
            str(cell["niche_normalized"]),
            str(cell["population_class"]),
        )
    )
    return {
        "required_cells_total": len(required_benchmark_keys),
        "ready_cell_count": ready_cell_count,
        "blocking_cell_count": len(cells),
        "min_benchmark_sample_size": min_benchmark_sample_size,
        "cells": cells,
    }


def low_coverage_failures(
    rows: list[dict[str, Any]],
    key_fields: tuple[str, ...],
    *,
    label: str,
    threshold: float,
) -> list[str]:
    failures: list[str] = []
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(group_value(row, field) for field in key_fields)
        grouped[key].append(row)

    metrics = (
        ("DA value coverage", "da_value_coverage"),
        ("Lighthouse value coverage", "lighthouse_value_coverage"),
        ("DA measurement coverage", "avg_top5_da_coverage"),
        ("Lighthouse measurement coverage", "avg_top5_lighthouse_coverage"),
    )
    for key, group_rows in sorted(grouped.items()):
        summary = summarize_group(group_rows)
        key_label = ", ".join(
            f"{field}={value}" for field, value in zip(key_fields, key, strict=True)
        )
        for metric_label, metric_key in metrics:
            value = float(summary[metric_key])
            if value < threshold:
                failures.append(
                    f"{label} {key_label} {metric_label} "
                    f"{value:.4f} below threshold {threshold:.4f}"
                )
    return failures


def build_report(
    *,
    facts: list[dict[str, Any]],
    metros: list[dict[str, Any]],
    benchmarks: list[dict[str, Any]],
    explore_cells: list[dict[str, Any]],
    threshold: float,
    min_benchmark_cells: int,
    min_benchmark_sample_size: int,
    min_metric_ready_cells: int = 0,
    min_explore_v2_rows: int = 0,
    required_services: tuple[str, ...] = DEFAULT_REQUIRED_SERVICES,
    required_population_classes: tuple[str, ...] = DEFAULT_REQUIRED_POPULATION_CLASSES,
    metric_sufficiency_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    metro_by_cbsa = {str(row.get("cbsa_code")): row for row in metros}
    benchmark_sample_sizes: dict[tuple[str, str], int] = {}
    for row in benchmarks:
        if not row.get("niche_normalized") or not row.get("population_class"):
            continue
        key = (
            normalize_service_key(str(row.get("niche_normalized") or "")),
            str(row.get("population_class")),
        )
        sample_size = int(numeric_value(row.get("sample_size_metros")))
        benchmark_sample_sizes[key] = max(benchmark_sample_sizes.get(key, 0), sample_size)
    benchmark_keys = set(benchmark_sample_sizes)
    usable_benchmark_keys = {
        key
        for key, sample_size in benchmark_sample_sizes.items()
        if sample_size >= min_benchmark_sample_size
    }
    required_benchmark_keys = build_required_benchmark_keys(
        services=required_services,
        population_classes=required_population_classes,
    )
    missing_required_benchmark_keys = required_benchmark_keys - benchmark_keys
    undersampled_required_benchmark_keys = {
        key
        for key in required_benchmark_keys & benchmark_keys
        if benchmark_sample_sizes.get(key, 0) < min_benchmark_sample_size
    }
    usable_required_benchmark_keys = usable_benchmark_keys & required_benchmark_keys
    out_of_scope_usable_benchmark_keys = usable_benchmark_keys - required_benchmark_keys
    explore_keys = {
        (str(row.get("cbsa_code")), str(row.get("niche_normalized")))
        for row in explore_cells
        if row.get("cbsa_code") and row.get("niche_normalized") and row.get("report_id")
    }

    enriched_facts = []
    fact_benchmark_keys: set[tuple[str, str]] = set()
    missing_benchmark_keys: set[tuple[str, str]] = set()
    undersampled_benchmark_keys: set[tuple[str, str]] = set()
    missing_explore_keys: set[tuple[str, str]] = set()
    for fact in facts:
        cbsa_code = str(fact.get("cbsa_code") or "")
        niche = str(fact.get("niche_normalized") or "")
        population_class = str(
            metro_by_cbsa.get(cbsa_code, {}).get("population_class") or "unknown"
        )
        enriched = dict(fact)
        enriched["population_class"] = population_class
        enriched["metro"] = metro_by_cbsa.get(cbsa_code, {}).get("cbsa_name") or cbsa_code
        enriched["explore_visible"] = (cbsa_code, niche) in explore_keys
        enriched_facts.append(enriched)

        if niche and population_class != "unknown":
            benchmark_key = (normalize_service_key(niche), population_class)
            fact_benchmark_keys.add(benchmark_key)
            if benchmark_key not in benchmark_keys:
                missing_benchmark_keys.add(benchmark_key)
            elif benchmark_sample_sizes.get(benchmark_key, 0) < min_benchmark_sample_size:
                undersampled_benchmark_keys.add(benchmark_key)
        if niche and cbsa_code and (cbsa_code, niche) not in explore_keys:
            missing_explore_keys.add((cbsa_code, niche))

    overall = summarize_group(enriched_facts)
    failures: list[str] = []
    if overall["da_value_coverage"] < threshold:
        failures.append(
            f"DA value coverage {overall['da_value_coverage']:.4f} below threshold {threshold:.4f}"
        )
    if overall["lighthouse_value_coverage"] < threshold:
        failures.append(
            "Lighthouse value coverage "
            f"{overall['lighthouse_value_coverage']:.4f} below threshold {threshold:.4f}"
        )
    if overall["avg_top5_da_coverage"] < threshold:
        failures.append(
            "DA measurement coverage "
            f"{overall['avg_top5_da_coverage']:.4f} below threshold {threshold:.4f}"
        )
    if overall["avg_top5_lighthouse_coverage"] < threshold:
        failures.append(
            "Lighthouse measurement coverage "
            f"{overall['avg_top5_lighthouse_coverage']:.4f} below threshold {threshold:.4f}"
        )
    if len(usable_required_benchmark_keys) < min_benchmark_cells:
        failures.append(
            "usable benchmark cell count within required scope "
            f"{len(usable_required_benchmark_keys)} below minimum {min_benchmark_cells}"
        )
    if missing_benchmark_keys:
        failures.append(
            f"{len(missing_benchmark_keys)} fact niche/population_class pair(s) lack benchmark cells"
        )
    if undersampled_benchmark_keys:
        failures.append(
            f"{len(undersampled_benchmark_keys)} benchmark cell(s) below sample size "
            f"{min_benchmark_sample_size}"
        )
    if missing_explore_keys:
        failures.append(f"{len(missing_explore_keys)} fact pair(s) are missing Explore cache rows")

    for key_fields, label in (
        (("niche_normalized",), "service"),
        (("population_class",), "population_class"),
        (("cbsa_code", "metro"), "metro"),
        (("niche_normalized", "population_class"), "benchmark_cell"),
        (("explore_visible",), "explore_visibility"),
    ):
        failures.extend(
            low_coverage_failures(
                enriched_facts,
                key_fields,
                label=label,
                threshold=threshold,
            )
        )

    by_explore_visibility: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in enriched_facts:
        by_explore_visibility[str(bool(fact["explore_visible"])).lower()].append(fact)

    metric_sufficiency = None
    required_metric_sufficiency = None
    strategy_readiness = None
    canary_guidance = None
    if metric_sufficiency_rows is not None:
        metric_sufficiency = summarize_metric_sufficiency(
            benchmark_cells=fact_benchmark_keys,
            benchmarks=benchmarks,
            metric_sufficiency_rows=metric_sufficiency_rows,
            min_benchmark_sample_size=min_benchmark_sample_size,
        )
        strategy_readiness = summarize_strategy_readiness(metric_sufficiency)
        canary_guidance = build_canary_guidance(metric_sufficiency, strategy_readiness)
        metric_gap_count = sum(
            1
            for cell in metric_sufficiency["cells"]
            for detail in cell["families"].values()
            if detail["status"] in {METRIC_MISSING_STATUS, METRIC_UNDERSAMPLED_STATUS}
        )
        if metric_gap_count:
            failures.append(
                f"{metric_gap_count} benchmark metric family sufficiency gap(s) need collection"
            )
        required_metric_sufficiency = summarize_metric_sufficiency(
            benchmark_cells=required_benchmark_keys,
            benchmarks=benchmarks,
            metric_sufficiency_rows=metric_sufficiency_rows,
            min_benchmark_sample_size=min_benchmark_sample_size,
        )

    required_acquisition_plan = build_required_acquisition_plan(
        required_benchmark_keys=required_benchmark_keys,
        benchmark_sample_sizes=benchmark_sample_sizes,
        metric_sufficiency=required_metric_sufficiency,
        min_benchmark_sample_size=min_benchmark_sample_size,
    )

    readiness_gates = build_readiness_gates(
        usable_benchmark_cells=len(usable_required_benchmark_keys),
        min_benchmark_cells=min_benchmark_cells,
        metric_ready_cells=count_metric_ready_cells(
            required_metric_sufficiency,
            required_benchmark_keys=required_benchmark_keys,
        ),
        min_metric_ready_cells=min_metric_ready_cells,
        explore_v2_rows=count_explore_v2_rows(
            explore_cells,
            metro_by_cbsa=metro_by_cbsa,
            required_benchmark_keys=required_benchmark_keys,
        ),
        min_explore_v2_rows=min_explore_v2_rows,
    )
    for check in readiness_gates["blocking_checks"]:
        failures.append(
            f"{ACCEPTANCE_GATE_LABELS[check]} {readiness_gates['counts'][check]} "
            f"below minimum {readiness_gates['minimums'][check]}"
        )

    report = {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "threshold": threshold,
        "min_benchmark_cells": min_benchmark_cells,
        "overall": overall,
        "benchmark_cells": {
            "count": len(benchmark_keys),
            "usable_count": len(usable_benchmark_keys),
            "required_cells_total": len(required_benchmark_keys),
            "usable_required_count": len(usable_required_benchmark_keys),
            "out_of_scope_usable_count": len(out_of_scope_usable_benchmark_keys),
            "missing_required_cells": [
                {"niche_normalized": niche, "population_class": population_class}
                for niche, population_class in sorted(missing_required_benchmark_keys)
            ],
            "undersampled_required_cells": [
                {
                    "niche_normalized": niche,
                    "population_class": population_class,
                    "sample_size_metros": benchmark_sample_sizes.get(
                        (niche, population_class),
                        0,
                    ),
                }
                for niche, population_class in sorted(undersampled_required_benchmark_keys)
            ],
            "missing_fact_cells": [
                {"niche_normalized": niche, "population_class": population_class}
                for niche, population_class in sorted(missing_benchmark_keys)
            ],
            "undersampled_fact_cells": [
                {
                    "niche_normalized": niche,
                    "population_class": population_class,
                    "sample_size_metros": benchmark_sample_sizes.get(
                        (niche, population_class),
                        0,
                    ),
                }
                for niche, population_class in sorted(undersampled_benchmark_keys)
            ],
        },
        "explore_visibility": {
            "visible_pairs": len(explore_keys),
            "missing_fact_pairs": [
                {"cbsa_code": cbsa_code, "niche_normalized": niche}
                for cbsa_code, niche in sorted(missing_explore_keys)
            ],
            "groups": [
                {
                    "explore_visible": visible,
                    **summarize_group(rows),
                }
                for visible, rows in sorted(by_explore_visibility.items())
            ],
        },
        "readiness_gates": readiness_gates,
        "required_acquisition_plan": required_acquisition_plan,
        "groups": (
            group_summary(enriched_facts, ("niche_normalized",), label="service")
            + group_summary(enriched_facts, ("population_class",), label="population_class")
            + group_summary(enriched_facts, ("cbsa_code", "metro"), label="metro")
            + group_summary(
                enriched_facts,
                ("niche_normalized", "population_class"),
                label="benchmark_cell",
            )
        ),
    }
    if metric_sufficiency is not None:
        report["metric_sufficiency"] = metric_sufficiency
        report["required_metric_sufficiency"] = required_metric_sufficiency
        report["strategy_readiness"] = strategy_readiness
        report["canary_guidance"] = canary_guidance
    return report


def audit_signal_coverage(
    supabase: Any,
    *,
    threshold: float,
    min_benchmark_cells: int,
    min_benchmark_sample_size: int,
    min_metric_ready_cells: int = 0,
    min_explore_v2_rows: int = 0,
) -> dict[str, Any]:
    facts = fetch_pages(supabase, "seo_facts", REQUIRED_COLUMNS["seo_facts"])
    metros = fetch_pages(supabase, "metros", REQUIRED_COLUMNS["metros"])
    benchmarks = fetch_pages(
        supabase,
        "seo_benchmarks",
        REQUIRED_COLUMNS["seo_benchmarks"],
    )
    metric_sufficiency_rows = fetch_pages(
        supabase,
        "seo_benchmark_metric_sufficiency",
        REQUIRED_COLUMNS["seo_benchmark_metric_sufficiency"],
    )
    explore_cells = fetch_pages(
        supabase,
        "explore_market_cells",
        REQUIRED_COLUMNS["explore_market_cells"],
    )
    return build_report(
        facts=facts,
        metros=metros,
        benchmarks=benchmarks,
        explore_cells=explore_cells,
        metric_sufficiency_rows=metric_sufficiency_rows,
        threshold=threshold,
        min_benchmark_cells=min_benchmark_cells,
        min_benchmark_sample_size=min_benchmark_sample_size,
        min_metric_ready_cells=min_metric_ready_cells,
        min_explore_v2_rows=min_explore_v2_rows,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=0.8,
        help="Minimum overall DA and Lighthouse value coverage ratio (default: 0.8).",
    )
    parser.add_argument(
        "--min-benchmark-cells",
        type=int,
        default=1,
        help="Minimum benchmark cells required before passing (default: 1).",
    )
    parser.add_argument(
        "--min-benchmark-sample-size",
        type=int,
        default=8,
        help="Minimum sample_size_metros for fact-backed benchmark cells (default: 8).",
    )
    parser.add_argument(
        "--min-metric-ready-cells",
        type=int,
        default=0,
        help=(
            "Minimum benchmark cells whose full metric-family sufficiency is ready "
            "(default: 0, disabled)."
        ),
    )
    parser.add_argument(
        "--min-explore-v2-rows",
        type=int,
        default=0,
        help="Minimum report-backed Explore rows with score_system=v2 (default: 0, disabled).",
    )
    parser.add_argument(
        "--expected-project-ref",
        default=None,
        help="Optional Supabase project ref guard for NEXT_PUBLIC_SUPABASE_URL.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        load_env()
        validate_expected_project_ref(args.expected_project_ref)
        report = audit_signal_coverage(
            supabase_client(),
            threshold=args.coverage_threshold,
            min_benchmark_cells=args.min_benchmark_cells,
            min_benchmark_sample_size=args.min_benchmark_sample_size,
            min_metric_ready_cells=args.min_metric_ready_cells,
            min_explore_v2_rows=args.min_explore_v2_rows,
        )
    except RuntimeError as exc:
        report = {"status": "fail", "failures": [str(exc)]}

    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
