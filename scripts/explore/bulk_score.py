"""Bulk-score city×service pairs to populate the explore_market_cells materialized view.

Usage:
    # Preview what will be scored (no API calls):
    python -m scripts.explore.bulk_score --preview

    # Score top 50 metros × 12 services via local FastAPI:
    python -m scripts.explore.bulk_score --apply

    # Custom city/service counts:
    python -m scripts.explore.bulk_score --apply --cities 20 --services 6

    # Resume after interruption (skips already-scored pairs):
    python -m scripts.explore.bulk_score --apply --resume

    # Refresh the materialized view only (no scoring):
    python -m scripts.explore.bulk_score --refresh-only

    # Use a remote API URL:
    python -m scripts.explore.bulk_score --apply --api-url https://whidby-1.onrender.com

Env vars:
    NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY — for matview refresh
    NEXT_PUBLIC_API_URL — FastAPI base (default: http://localhost:8001)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SERVICES = [
    "roofing",
    "plumbing",
    "hvac",
    "tree service",
    "pest control",
    "water damage restoration",
    "landscaping",
    "electrician",
    "concrete",
    "fence installation",
    "pressure washing",
    "garage door repair",
    "painting",
    "carpet cleaning",
    "junk removal",
    "locksmith",
]

DEFAULT_CONCURRENCY = 10


def _load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def _api_url(args: argparse.Namespace) -> str:
    if args.api_url:
        return args.api_url.rstrip("/")
    return os.environ.get("NEXT_PUBLIC_API_URL", "http://localhost:8001").rstrip("/")


def _supabase_client() -> Any:
    from supabase import create_client

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required for matview refresh"
        )
    return create_client(url, key)


def fetch_top_metros(supabase: Any, limit: int) -> list[dict[str, Any]]:
    response = (
        supabase.table("metros")
        .select("cbsa_code, cbsa_name, state, population")
        .not_.is_("population", "null")
        .order("population", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def fetch_scored_pairs(supabase: Any) -> set[tuple[str, str]]:
    response = (
        supabase.table("metro_scores")
        .select("cbsa_code, report_id")
        .execute()
    )
    scored_cbsa = {row["cbsa_code"] for row in response.data}

    if not scored_cbsa:
        return set()

    reports_response = (
        supabase.table("reports")
        .select("id, niche_keyword")
        .execute()
    )
    report_niche = {row["id"]: row["niche_keyword"] for row in reports_response.data}

    pairs = set()
    for row in response.data:
        niche = report_niche.get(row["report_id"])
        if niche:
            pairs.add((row["cbsa_code"], niche.strip().lower()))
    return pairs


async def score_one(
    client: httpx.AsyncClient,
    api_url: str,
    city_name: str,
    state: str,
    service: str,
) -> dict[str, Any] | None:
    payload = {
        "niche": service,
        "city": city_name,
        "state": state,
    }
    try:
        resp = await client.post(
            f"{api_url}/api/niches/score",
            json=payload,
            timeout=180.0,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "HTTP %d for %s × %s: %s",
            resp.status_code,
            city_name,
            service,
            resp.text[:200],
        )
        return None
    except httpx.TimeoutException:
        logger.error("Timeout scoring %s × %s", city_name, service)
        return None
    except Exception as exc:
        logger.error("Error scoring %s × %s: %s", city_name, service, exc)
        return None


def refresh_matview(supabase: Any) -> None:
    logger.info("Refreshing explore_market_cells materialized view...")
    supabase.rpc("_refresh_explore_market_cells", {}).execute()


def refresh_matview_sql() -> None:
    """Refresh via direct SQL if the RPC doesn't exist."""
    _load_env()
    sb = _supabase_client()
    try:
        refresh_matview(sb)
        logger.info("Materialized view refreshed via RPC.")
    except Exception:
        logger.info("RPC not found, refreshing via raw SQL...")
        sb.postgrest.auth(os.environ["SUPABASE_SERVICE_ROLE_KEY"])
        if hasattr(sb, "rpc"):
            try:
                sb.rpc(
                    "exec_sql",
                    {"query": "REFRESH MATERIALIZED VIEW public.explore_market_cells"},
                ).execute()
                logger.info("Materialized view refreshed via exec_sql RPC.")
                return
            except Exception:
                pass
        logger.warning(
            "Could not refresh matview programmatically. "
            "Run this SQL manually in Supabase:\n"
            "  REFRESH MATERIALIZED VIEW public.explore_market_cells;"
        )


def city_short_name(cbsa_name: str) -> str:
    return cbsa_name.split(",")[0].split("-")[0].strip()


async def run_bulk_score(args: argparse.Namespace) -> None:
    _load_env()
    sb = _supabase_client()
    api_url = _api_url(args)

    logger.info("Fetching top %d metros by population...", args.cities)
    metros = fetch_top_metros(sb, args.cities)
    logger.info("Found %d metros", len(metros))

    services = SERVICES[: args.services]
    logger.info("Services to score (%d): %s", len(services), ", ".join(services))

    total_pairs = len(metros) * len(services)

    scored_pairs: set[tuple[str, str]] = set()
    if args.resume:
        logger.info("Checking for already-scored pairs...")
        scored_pairs = fetch_scored_pairs(sb)
        logger.info("Found %d already-scored pairs", len(scored_pairs))

    pairs = []
    for metro in metros:
        for service in services:
            cbsa = metro["cbsa_code"]
            if args.resume and (cbsa, service.strip().lower()) in scored_pairs:
                continue
            pairs.append((metro, service))

    if args.preview:
        logger.info("\n=== PREVIEW: %d pairs to score ===", len(pairs))
        logger.info("Cities (%d):", len(metros))
        for m in metros:
            logger.info(
                "  %s  %s (%s)  pop=%s",
                m["cbsa_code"],
                m["cbsa_name"],
                m["state"],
                f"{m['population']:,}",
            )
        logger.info("\nServices (%d): %s", len(services), ", ".join(services))
        logger.info("\nTotal pairs: %d", len(pairs))
        if scored_pairs:
            logger.info("Already scored (will skip): %d", total_pairs - len(pairs))
        logger.info(
            "\nEstimated DataForSEO cost: ~$%.2f (at ~$0.01/pair)",
            len(pairs) * 0.01,
        )
        avg_time_per_pair = 15.0
        parallel_time = len(pairs) * avg_time_per_pair / args.concurrency
        logger.info(
            "Estimated time: ~%d minutes (at ~%.0fs/pair, concurrency=%d)",
            int(parallel_time / 60),
            avg_time_per_pair,
            args.concurrency,
        )
        return

    logger.info(
        "Scoring %d pairs (%d skipped as already scored), concurrency=%d...",
        len(pairs),
        total_pairs - len(pairs),
        args.concurrency,
    )

    # Verify API is reachable
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{api_url}/health", timeout=10.0)
            if health.status_code != 200:
                logger.error("API health check failed: %d", health.status_code)
                sys.exit(1)
        except Exception as exc:
            logger.error("Cannot reach API at %s: %s", api_url, exc)
            sys.exit(1)

    succeeded = 0
    failed = 0
    completed = 0
    results_path = PROJECT_ROOT / "scripts" / "explore" / "bulk_score_results.jsonl"
    started = time.monotonic()
    write_lock = asyncio.Lock()
    sem = asyncio.Semaphore(args.concurrency)

    async def _worker(
        idx: int, metro: dict[str, Any], service: str, client: httpx.AsyncClient
    ) -> bool:
        nonlocal succeeded, failed, completed
        city_name = city_short_name(metro["cbsa_name"])
        state = metro["state"]

        async with sem:
            elapsed = time.monotonic() - started
            rate = succeeded / (elapsed / 60) if elapsed > 60 else 0
            logger.info(
                "[%d/%d] Scoring %s, %s × %s  (ok=%d fail=%d rate=%.1f/min)",
                idx, len(pairs), city_name, state, service, succeeded, failed, rate,
            )

            result = await score_one(client, api_url, city_name, state, service)

        completed += 1
        if result and result.get("report_id"):
            succeeded += 1
            async with write_lock:
                with open(results_path, "a") as f:
                    f.write(
                        json.dumps(
                            {
                                "cbsa_code": metro["cbsa_code"],
                                "city": city_name,
                                "state": state,
                                "service": service,
                                "report_id": result["report_id"],
                                "opportunity_score": result.get("opportunity_score"),
                                "classification_label": result.get("classification_label"),
                            }
                        )
                        + "\n"
                    )
            return True
        else:
            failed += 1
            return False

    async with httpx.AsyncClient() as client:
        tasks = [
            _worker(i, metro, service, client)
            for i, (metro, service) in enumerate(pairs, 1)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    total_time = time.monotonic() - started
    logger.info(
        "\n=== BULK SCORE COMPLETE ===\n"
        "  Succeeded: %d\n"
        "  Failed:    %d\n"
        "  Total:     %d\n"
        "  Time:      %.1f minutes\n"
        "  Results:   %s",
        succeeded,
        failed,
        succeeded + failed,
        total_time / 60,
        results_path,
    )

    if succeeded > 0:
        logger.info("Refreshing materialized view...")
        refresh_matview_sql()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-score city×service pairs for the explore page."
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show what would be scored without making API calls.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually run scoring (costs DataForSEO + Anthropic credits).",
    )
    parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="Only refresh the materialized view, no scoring.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip pairs that already have scores in metro_scores.",
    )
    parser.add_argument(
        "--cities",
        type=int,
        default=50,
        help="Number of top metros by population (default: 50).",
    )
    parser.add_argument(
        "--services",
        type=int,
        default=12,
        help="Number of services from the catalog (default: 12).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max parallel scoring requests (default: {DEFAULT_CONCURRENCY}, range 1-20).",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="FastAPI base URL (default: NEXT_PUBLIC_API_URL or http://localhost:8001).",
    )
    args = parser.parse_args()

    if args.refresh_only:
        refresh_matview_sql()
        return

    if not args.preview and not args.apply:
        parser.error("Specify --preview or --apply")

    args.concurrency = max(1, min(20, args.concurrency))

    asyncio.run(run_bulk_score(args))


if __name__ == "__main__":
    main()
