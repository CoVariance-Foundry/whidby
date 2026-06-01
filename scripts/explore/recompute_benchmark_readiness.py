"""Read-only readiness checks before running benchmark recompute."""

from __future__ import annotations

import argparse


def readiness_status(
    metros_with_population: int,
    seo_fact_count: int,
    cbp_count: int,
    usable_benchmark_cells: int = 0,
    min_benchmark_cells: int = 0,
    metric_ready_cells: int = 0,
    min_metric_ready_cells: int = 0,
    explore_v2_rows: int = 0,
    min_explore_v2_rows: int = 0,
) -> dict[str, object]:
    """Return whether benchmark recompute and Explore acceptance gates are ready."""
    counts = {
        "metros_with_population": metros_with_population,
        "seo_fact_count": seo_fact_count,
        "cbp_count": cbp_count,
        "usable_benchmark_cells": usable_benchmark_cells,
        "metric_ready_cells": metric_ready_cells,
        "explore_v2_rows": explore_v2_rows,
    }
    minimums = {
        "metros_with_population": 1,
        "seo_fact_count": 1,
        "cbp_count": 1,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check source counts before running benchmark recompute.",
    )
    parser.add_argument("--metros-with-population", type=int, required=True)
    parser.add_argument("--seo-fact-count", type=int, required=True)
    parser.add_argument("--cbp-count", type=int, required=True)
    parser.add_argument("--usable-benchmark-cells", type=int, default=0)
    parser.add_argument("--min-benchmark-cells", type=int, default=0)
    parser.add_argument("--metric-ready-cells", type=int, default=0)
    parser.add_argument("--min-metric-ready-cells", type=int, default=0)
    parser.add_argument("--explore-v2-rows", type=int, default=0)
    parser.add_argument("--min-explore-v2-rows", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = readiness_status(
        metros_with_population=args.metros_with_population,
        seo_fact_count=args.seo_fact_count,
        cbp_count=args.cbp_count,
        usable_benchmark_cells=args.usable_benchmark_cells,
        min_benchmark_cells=args.min_benchmark_cells,
        metric_ready_cells=args.metric_ready_cells,
        min_metric_ready_cells=args.min_metric_ready_cells,
        explore_v2_rows=args.explore_v2_rows,
        min_explore_v2_rows=args.min_explore_v2_rows,
    )

    print(f"ready={str(result['ready']).lower()}")
    print(f"blocking_checks={','.join(result['blocking_checks'])}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
