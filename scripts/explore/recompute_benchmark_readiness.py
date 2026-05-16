"""Read-only readiness checks before running benchmark recompute."""

from __future__ import annotations

import argparse


def readiness_status(
    metros_with_population: int,
    seo_fact_count: int,
    cbp_count: int,
) -> dict[str, object]:
    """Return whether Explore benchmark source counts are ready."""
    counts = {
        "metros_with_population": metros_with_population,
        "seo_fact_count": seo_fact_count,
        "cbp_count": cbp_count,
    }
    blocking_checks = [name for name, count in counts.items() if count <= 0]

    return {
        "ready": not blocking_checks,
        "blocking_checks": blocking_checks,
        "counts": counts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check source counts before running benchmark recompute.",
    )
    parser.add_argument("--metros-with-population", type=int, required=True)
    parser.add_argument("--seo-fact-count", type=int, required=True)
    parser.add_argument("--cbp-count", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = readiness_status(
        metros_with_population=args.metros_with_population,
        seo_fact_count=args.seo_fact_count,
        cbp_count=args.cbp_count,
    )

    print(f"ready={str(result['ready']).lower()}")
    print(f"blocking_checks={','.join(result['blocking_checks'])}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
