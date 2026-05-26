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
    METRIC_UNDERSAMPLED_STATUS,
    build_canary_guidance,
    summarize_metric_sufficiency,
    summarize_strategy_readiness,
)

PAGE_SIZE = 1000

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
    "explore_market_cells": ("cbsa_code", "niche_normalized", "report_id"),
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
    metric_sufficiency_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    metro_by_cbsa = {str(row.get("cbsa_code")): row for row in metros}
    benchmark_sample_sizes: dict[tuple[str, str], int] = {}
    for row in benchmarks:
        if not row.get("niche_normalized") or not row.get("population_class"):
            continue
        key = (str(row.get("niche_normalized")), str(row.get("population_class")))
        sample_size = int(numeric_value(row.get("sample_size_metros")))
        benchmark_sample_sizes[key] = max(benchmark_sample_sizes.get(key, 0), sample_size)
    benchmark_keys = set(benchmark_sample_sizes)
    usable_benchmark_keys = {
        key
        for key, sample_size in benchmark_sample_sizes.items()
        if sample_size >= min_benchmark_sample_size
    }
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
            benchmark_key = (niche, population_class)
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
    if len(usable_benchmark_keys) < min_benchmark_cells:
        failures.append(
            f"usable benchmark cell count {len(usable_benchmark_keys)} below minimum "
            f"{min_benchmark_cells}"
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

    report = {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "threshold": threshold,
        "min_benchmark_cells": min_benchmark_cells,
        "overall": overall,
        "benchmark_cells": {
            "count": len(benchmark_keys),
            "usable_count": len(usable_benchmark_keys),
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
        report["strategy_readiness"] = strategy_readiness
        report["canary_guidance"] = canary_guidance
    return report


def audit_signal_coverage(
    supabase: Any,
    *,
    threshold: float,
    min_benchmark_cells: int,
    min_benchmark_sample_size: int,
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
        )
    except RuntimeError as exc:
        report = {"status": "fail", "failures": [str(exc)]}

    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
