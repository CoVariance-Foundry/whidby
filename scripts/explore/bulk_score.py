"""Bulk-score city×service pairs to populate the explore_market_cells materialized view.

Usage:
    # Preview what will be scored (no API calls):
    python -m scripts.explore.bulk_score --preview

    # Score 50 rank-and-rent metros × 12 services via local FastAPI:
    python -m scripts.explore.bulk_score --apply

    # Custom city/service counts:
    python -m scripts.explore.bulk_score --apply --cities 20 --services 6

    # Explicit service list:
    python -m scripts.explore.bulk_score --apply --service-name roofing --service-name plumbing

    # Resume after interruption (skips already-scored pairs):
    python -m scripts.explore.bulk_score --apply --resume

    # V2-aware resume (skips only pairs with metro_score_v2 + seo_facts):
    python -m scripts.explore.bulk_score --apply --resume-v2

    # Retry failed/partial pairs from an audit file:
    python -m scripts.explore.bulk_score --apply --retry-failed-from scripts/explore/bulk_score_results.jsonl

    # Refresh the materialized view only (no scoring):
    python -m scripts.explore.bulk_score --refresh-only

    # Use a remote API URL:
    python -m scripts.explore.bulk_score --apply --api-url https://whidby-1.onrender.com

Env vars:
    NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY — for matview refresh
    NEXT_PUBLIC_API_URL — FastAPI base (default: http://localhost:8000)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
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
    "auto repair",
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
PAGE_SIZE = 1000
MAX_METRO_FETCH = 1000
RETRYABLE_STATUSES = {"failed", "partial_failure"}
RANK_AND_RENT_CLASS_ORDER = (
    "large_300k_1m",
    "medium_100_300k",
    "metro_1m_5m",
    "small_50_100k",
    "mega_5m_plus",
)
STRIP_TRAILING_SERVICE_SUFFIXES = re.compile(
    r"\s+\b(near me|services?|company|companies|contractors?|pros?|experts?)\b$",
    re.IGNORECASE,
)
MULTI_SPACE = re.compile(r"\s+")
CATALOG_SERVICE_KEYS = {MULTI_SPACE.sub(" ", service.strip().lower()) for service in SERVICES}


def default_results_path() -> Path:
    return PROJECT_ROOT / "scripts" / "explore" / "bulk_score_results.jsonl"


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
    return os.environ.get("NEXT_PUBLIC_API_URL", "http://localhost:8000").rstrip("/")


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
    """Compatibility wrapper for the old top-population selection."""
    return fetch_metros(
        supabase,
        limit=limit,
        strategy="top-population",
        population_classes=None,
        min_population=None,
        max_population=None,
        require_dfs=False,
        mega_cap=None,
    )


def fetch_metros(
    supabase: Any,
    *,
    limit: int,
    strategy: str,
    population_classes: list[str] | None,
    min_population: int | None,
    max_population: int | None,
    require_dfs: bool,
    mega_cap: int | None,
) -> list[dict[str, Any]]:
    response = (
        supabase.table("metros")
        .select(
            "cbsa_code, cbsa_name, state, population, population_class, "
            "dataforseo_location_codes"
        )
        .not_.is_("population", "null")
        .order("population", desc=True)
        .limit(MAX_METRO_FETCH)
        .execute()
    )
    candidates = list(response.data or [])
    filtered = [
        metro
        for metro in candidates
        if _metro_matches_filters(
            metro,
            population_classes=population_classes,
            min_population=min_population,
            max_population=max_population,
            require_dfs=require_dfs,
        )
    ]
    if strategy == "top-population":
        ordered = sorted(
            filtered,
            key=lambda metro: (
                -(int(metro.get("population") or 0)),
                str(metro.get("cbsa_code") or ""),
            ),
        )
        return ordered[:limit]

    ordered = _rank_and_rent_order(filtered)
    return _apply_mega_cap(ordered, limit=limit, mega_cap=mega_cap)


def _metro_matches_filters(
    metro: dict[str, Any],
    *,
    population_classes: list[str] | None,
    min_population: int | None,
    max_population: int | None,
    require_dfs: bool,
) -> bool:
    population = metro.get("population")
    if population is None:
        return False
    population_int = int(population)
    if min_population is not None and population_int < min_population:
        return False
    if max_population is not None and population_int > max_population:
        return False
    if population_classes and metro.get("population_class") not in population_classes:
        return False
    if require_dfs and not _has_dfs_location(metro):
        return False
    return True


def _has_dfs_location(metro: dict[str, Any]) -> bool:
    codes = metro.get("dataforseo_location_codes")
    return isinstance(codes, list) and any(code is not None for code in codes)


def _rank_and_rent_order(metros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {name: index for index, name in enumerate(RANK_AND_RENT_CLASS_ORDER)}
    fallback_priority = len(priority)
    return sorted(
        metros,
        key=lambda metro: (
            priority.get(str(metro.get("population_class") or ""), fallback_priority),
            -(int(metro.get("population") or 0)),
            str(metro.get("state") or ""),
            str(metro.get("cbsa_code") or ""),
        ),
    )


def _apply_mega_cap(
    metros: list[dict[str, Any]], *, limit: int, mega_cap: int | None
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    mega_count = 0
    for metro in metros:
        if metro.get("population_class") == "mega_5m_plus" and mega_cap is not None:
            if mega_count >= mega_cap:
                continue
            mega_count += 1
        selected.append(metro)
        if len(selected) >= limit:
            return selected
    return selected


def summarize_metro_selection(metros: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for metro in metros:
        population_class = str(metro.get("population_class") or "unknown")
        summary[population_class] = summary.get(population_class, 0) + 1
    return summary


def normalize_service_key(raw: str, catalog_keys: set[str] | None = None) -> str:
    text = MULTI_SPACE.sub(" ", raw.strip().lower()).strip()
    known_keys = catalog_keys or CATALOG_SERVICE_KEYS
    if text in known_keys:
        return text
    return STRIP_TRAILING_SERVICE_SUFFIXES.sub("", text).strip()


def select_services(args: argparse.Namespace) -> list[str]:
    """Resolve requested service labels into unique normalized scoring labels."""
    service_names = getattr(args, "service_names", None)
    raw_services = service_names if service_names else SERVICES[: args.services]
    services: list[str] = []
    seen: set[str] = set()
    for raw in raw_services:
        service = normalize_service_key(raw)
        if not service:
            raise ValueError("Service names must be non-empty")
        if service in seen:
            continue
        services.append(service)
        seen.add(service)
    return services


def fetch_service_catalog_keys(supabase: Any) -> set[str]:
    rows = _fetch_pages(supabase, "niche_naics_mapping", "niche_normalized")
    return {
        MULTI_SPACE.sub(" ", str(row.get("niche_normalized") or "").strip().lower())
        for row in rows
        if row.get("niche_normalized")
    }


def validate_services_for_catalog(supabase: Any, services: list[str]) -> list[str]:
    """Validate services against the Explore catalog and return catalog-normalized keys."""
    catalog_keys = fetch_service_catalog_keys(supabase)
    normalized_services = [normalize_service_key(service, catalog_keys) for service in services]
    missing = [
        service
        for service, normalized in zip(services, normalized_services, strict=True)
        if normalized not in catalog_keys
    ]
    if missing:
        raise RuntimeError(
            "Requested service(s) are missing from niche_naics_mapping: "
            + ", ".join(missing)
        )
    return list(dict.fromkeys(normalized_services))


def fetch_scored_pairs(supabase: Any) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    try:
        market_cells = _fetch_pages(
            supabase,
            "explore_market_cells",
            "cbsa_code,niche_normalized,report_id",
        )
        pairs.update(
            (str(row["cbsa_code"]), normalize_service_key(str(row["niche_normalized"])))
            for row in market_cells
            if row.get("cbsa_code") and row.get("niche_normalized") and row.get("report_id")
        )
    except Exception as exc:
        logger.info(
            "Could not read explore_market_cells for resume state; falling back to reports + metro_scores: %s",
            exc,
        )

    all_rows = _fetch_pages(supabase, "metro_scores", "cbsa_code, report_id")
    scored_cbsa = {row["cbsa_code"] for row in all_rows}

    if not scored_cbsa:
        return pairs

    all_reports = _fetch_pages(supabase, "reports", "id, niche_keyword")
    report_niche = {row["id"]: row["niche_keyword"] for row in all_reports}

    for row in all_rows:
        niche = report_niche.get(row["report_id"])
        if niche:
            pairs.add((row["cbsa_code"], normalize_service_key(niche)))
    return pairs


def fetch_v2_persisted_pairs(supabase: Any) -> set[tuple[str, str]]:
    """Return pairs that have both normalized V2 scores and benchmark fact rows."""
    v2_rows = _fetch_pages(
        supabase,
        "metro_score_v2",
        "cbsa_code,niche_normalized,report_id",
    )
    fact_rows = _fetch_pages(
        supabase,
        "seo_facts",
        "cbsa_code,niche_normalized,report_id",
    )
    v2_pairs = {
        (str(row["cbsa_code"]), normalize_service_key(str(row["niche_normalized"])))
        for row in v2_rows
        if row.get("cbsa_code") and row.get("niche_normalized") and row.get("report_id")
    }
    fact_pairs = {
        (str(row["cbsa_code"]), normalize_service_key(str(row["niche_normalized"])))
        for row in fact_rows
        if row.get("cbsa_code") and row.get("niche_normalized") and row.get("report_id")
    }
    return v2_pairs.intersection(fact_pairs)


def load_retry_pairs(path: Path) -> set[tuple[str, str]]:
    """Load failed or partial city-service pairs from a bulk-score JSONL audit."""
    pairs: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Could not parse retry audit row {line_number} in {path}"
                ) from exc
            if record.get("status") not in RETRYABLE_STATUSES:
                continue
            request = record.get("request")
            if not isinstance(request, dict):
                continue
            cbsa_code = str(request.get("cbsa_code") or "").strip()
            service = str(
                request.get("niche_normalized") or request.get("service") or ""
            ).strip()
            if cbsa_code and service:
                pairs.add((cbsa_code, normalize_service_key(service)))
    return pairs


def _fetch_pages(supabase: Any, table: str, columns: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        response = (
            supabase.table(table)
            .select(columns)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        page = list(response.data or [])
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


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


def verify_persistence(
    supabase: Any,
    *,
    report_id: str | None,
    cbsa_code: str,
    require_v2: bool,
) -> dict[str, Any]:
    if not report_id:
        return {
            "ok": False,
            "report_exists": False,
            "metro_scores_count": 0,
            "metro_score_v2_count": 0,
            "seo_facts_count": 0,
            "missing": ["report_id"],
        }

    report_rows = _select_rows(
        supabase,
        "reports",
        "id",
        filters={"id": report_id},
        limit=1,
    )
    score_rows = _select_rows(
        supabase,
        "metro_scores",
        "report_id, cbsa_code",
        filters={"report_id": report_id, "cbsa_code": cbsa_code},
    )
    score_v2_rows: list[dict[str, Any]] = []
    seo_fact_rows: list[dict[str, Any]] = []
    if require_v2:
        score_v2_rows = _select_rows(
            supabase,
            "metro_score_v2",
            "report_id, cbsa_code",
            filters={"report_id": report_id, "cbsa_code": cbsa_code},
        )
        seo_fact_rows = _select_rows(
            supabase,
            "seo_facts",
            "report_id, cbsa_code",
            filters={"report_id": report_id, "cbsa_code": cbsa_code},
        )

    missing = []
    if not report_rows:
        missing.append("reports")
    if not score_rows:
        missing.append("metro_scores")
    if require_v2 and not score_v2_rows:
        missing.append("metro_score_v2")
    if require_v2 and not seo_fact_rows:
        missing.append("seo_facts")

    return {
        "ok": not missing,
        "report_exists": bool(report_rows),
        "metro_scores_count": len(score_rows),
        "metro_score_v2_count": len(score_v2_rows),
        "seo_facts_count": len(seo_fact_rows),
        "missing": missing,
    }


def persistence_verification_error(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "report_exists": False,
        "metro_scores_count": 0,
        "metro_score_v2_count": 0,
        "seo_facts_count": 0,
        "missing": ["persistence_verification"],
        "error": str(exc),
    }


def _select_rows(
    supabase: Any,
    table: str,
    columns: str,
    *,
    filters: dict[str, Any],
    limit: int | None = None,
) -> list[dict[str, Any]]:
    query = supabase.table(table).select(columns)
    for column, value in filters.items():
        query = query.eq(column, value)
    if limit is not None:
        query = query.limit(limit)
    response = query.execute()
    return list(response.data or [])


def build_audit_record(
    *,
    status: str,
    metro: dict[str, Any],
    city_name: str,
    service: str,
    api_url: str,
    started_at: datetime,
    elapsed_ms: int,
    result: dict[str, Any] | None,
    persistence: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:
    report_id = result.get("report_id") if result else None
    persist_warning = result.get("persist_warning") if result else None
    return {
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": elapsed_ms,
        "api_url": api_url,
        "request": {
            "cbsa_code": metro.get("cbsa_code"),
            "cbsa_name": metro.get("cbsa_name"),
            "city": city_name,
            "state": metro.get("state"),
            "service": service,
            "niche_normalized": normalize_service_key(service),
            "population": metro.get("population"),
            "population_class": metro.get("population_class"),
        },
        "report_id": report_id,
        "score": {
            "opportunity_score": result.get("opportunity_score") if result else None,
            "classification_label": result.get("classification_label") if result else None,
            "score_system": _score_system(result),
            "v2_score_count": _v2_score_count(result),
        },
        "persist_warning": persist_warning,
        "persistence": persistence,
        "error": error,
    }


def _score_system(result: dict[str, Any] | None) -> str | None:
    if result is None:
        return None
    return "v2" if _v2_score_count(result) > 0 else "legacy"


def _v2_score_count(result: dict[str, Any] | None) -> int:
    if result is None:
        return 0
    report = result.get("report")
    if not isinstance(report, dict):
        return 0
    return sum(
        1
        for metro in report.get("metros", [])
        if isinstance(metro, dict) and isinstance(metro.get("v2_scores"), dict)
    )


def _status_for_result(
    result: dict[str, Any] | None,
    persistence: dict[str, Any],
) -> str:
    if not result or not result.get("report_id"):
        return "failed"
    if result.get("persist_warning") or not persistence.get("ok"):
        return "partial_failure"
    return "success"


def _error_for_status(
    status: str,
    result: dict[str, Any] | None,
    persistence: dict[str, Any],
) -> str | None:
    if status == "failed":
        if result is None:
            return "Scoring API request failed before returning a response."
        return "Scoring API returned a response without report_id."
    if status != "partial_failure":
        return None

    errors = []
    if result and result.get("persist_warning"):
        errors.append(str(result["persist_warning"]))
    if persistence.get("error"):
        errors.append(f"persistence verification failed: {persistence['error']}")
    missing = ", ".join(persistence.get("missing") or [])
    if missing:
        errors.append(f"missing {missing}")
    return "; ".join(errors) if errors else None


def refresh_matview(supabase: Any) -> None:
    logger.info("Refreshing explore_market_cells materialized view...")
    supabase.rpc("_refresh_explore_market_cells", {}).execute()


def _is_missing_refresh_rpc(exc: Exception) -> bool:
    message = str(exc).lower()
    return "_refresh_explore_market_cells" in message and any(
        marker in message
        for marker in (
            "not found",
            "does not exist",
            "could not find",
            "schema cache",
            "pgrst202",
        )
    )


def refresh_matview_sql() -> None:
    """Refresh via direct SQL if the RPC doesn't exist."""
    _load_env()
    sb = _supabase_client()
    try:
        refresh_matview(sb)
        logger.info("Materialized view refreshed via RPC.")
        return
    except Exception as exc:
        if not _is_missing_refresh_rpc(exc):
            raise
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
            except Exception as fallback_exc:
                raise RuntimeError(
                    "Could not refresh explore_market_cells via fallback exec_sql RPC."
                ) from fallback_exc
        raise RuntimeError(
            "Could not refresh explore_market_cells programmatically. "
            "Run this SQL manually in Supabase: "
            "REFRESH MATERIALIZED VIEW public.explore_market_cells;"
        )


def city_short_name(cbsa_name: str) -> str:
    return cbsa_name.split(",")[0].split("-")[0].strip()


async def run_bulk_score(args: argparse.Namespace) -> None:
    _load_env()
    sb = _supabase_client()
    api_url = _api_url(args)
    retry_pairs: set[tuple[str, str]] | None = None
    retry_failed_from = getattr(args, "retry_failed_from", None)
    if retry_failed_from:
        retry_pairs = load_retry_pairs(retry_failed_from)
        logger.info(
            "Loaded %d retryable pair(s) from %s",
            len(retry_pairs),
            retry_failed_from,
        )
        if not retry_pairs:
            logger.info("No failed or partial pairs found in retry audit; nothing to do.")
            return

    logger.info(
        "Fetching up to %d metros with %s strategy...",
        args.cities,
        args.strategy,
    )
    metros = fetch_metros(
        sb,
        limit=args.cities,
        strategy=args.strategy,
        population_classes=args.population_classes,
        min_population=args.min_population,
        max_population=args.max_population,
        require_dfs=args.require_dfs,
        mega_cap=args.mega_cap,
    )
    logger.info(
        "Found %d metros by class: %s",
        len(metros),
        summarize_metro_selection(metros),
    )

    services = validate_services_for_catalog(sb, select_services(args))
    logger.info("Services to score (%d): %s", len(services), ", ".join(services))

    total_pairs = len(metros) * len(services)

    scored_pairs: set[tuple[str, str]] = set()
    resume_v2 = getattr(args, "resume_v2", False)
    if args.resume or resume_v2:
        logger.info("Checking for already-scored pairs...")
        scored_pairs = fetch_v2_persisted_pairs(sb) if resume_v2 else fetch_scored_pairs(sb)
        logger.info("Found %d already-scored pairs", len(scored_pairs))

    pairs = []
    selected_pair_keys: set[tuple[str, str]] = set()
    for metro in metros:
        for service in services:
            cbsa = metro["cbsa_code"]
            pair_key = (cbsa, normalize_service_key(service))
            selected_pair_keys.add(pair_key)
            if retry_pairs is not None and pair_key not in retry_pairs:
                continue
            if (args.resume or resume_v2) and pair_key in scored_pairs:
                continue
            pairs.append((metro, service))

    if retry_pairs is not None:
        unmatched_retry_pairs = retry_pairs - selected_pair_keys
        if unmatched_retry_pairs:
            logger.warning(
                "Retry audit contained %d pair(s) outside the current city/service selection.",
                len(unmatched_retry_pairs),
            )

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
        logger.info("Population class mix: %s", summarize_metro_selection(metros))
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
    partial_failed = 0
    completed = 0
    results_path = getattr(args, "results_path", None) or default_results_path()
    if not results_path.is_absolute():
        results_path = PROJECT_ROOT / results_path
    results_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    write_lock = asyncio.Lock()
    sem = asyncio.Semaphore(args.concurrency)

    async def _worker(
        idx: int, metro: dict[str, Any], service: str, client: httpx.AsyncClient
    ) -> bool:
        nonlocal succeeded, failed, partial_failed, completed
        city_name = city_short_name(metro["cbsa_name"])
        state = metro["state"]

        async with sem:
            elapsed = time.monotonic() - started
            rate = succeeded / (elapsed / 60) if elapsed > 60 else 0
            logger.info(
                "[%d/%d] Scoring %s, %s × %s  (ok=%d fail=%d rate=%.1f/min)",
                idx, len(pairs), city_name, state, service, succeeded, failed, rate,
            )

            attempt_started_at = datetime.now(timezone.utc)
            attempt_start = time.monotonic()
            result = await score_one(client, api_url, city_name, state, service)

        completed += 1
        elapsed_ms = int((time.monotonic() - attempt_start) * 1000)
        try:
            persistence = await asyncio.to_thread(
                verify_persistence,
                sb,
                report_id=result.get("report_id") if result else None,
                cbsa_code=metro["cbsa_code"],
                require_v2=args.require_v2_persistence,
            )
        except Exception as exc:
            persistence = persistence_verification_error(exc)
        status = _status_for_result(result, persistence)
        if status == "success":
            succeeded += 1
        elif status == "partial_failure":
            partial_failed += 1
        else:
            failed += 1

        audit_record = build_audit_record(
            status=status,
            metro=metro,
            city_name=city_name,
            service=service,
            api_url=api_url,
            started_at=attempt_started_at,
            elapsed_ms=elapsed_ms,
            result=result,
            persistence=persistence,
            error=_error_for_status(status, result, persistence),
        )
        async with write_lock:
            with open(results_path, "a") as f:
                f.write(json.dumps(audit_record, sort_keys=True) + "\n")

        return status == "success"

    async with httpx.AsyncClient() as client:
        tasks = [
            _worker(i, metro, service, client)
            for i, (metro, service) in enumerate(pairs, 1)
        ]
        await asyncio.gather(*tasks)

    total_time = time.monotonic() - started
    logger.info(
        "\n=== BULK SCORE COMPLETE ===\n"
        "  Succeeded: %d\n"
        "  Partial:   %d\n"
        "  Failed:    %d\n"
        "  Total:     %d\n"
        "  Time:      %.1f minutes\n"
        "  Results:   %s",
        succeeded,
        partial_failed,
        failed,
        succeeded + partial_failed + failed,
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
        help="Skip pairs already visible in explore_market_cells or legacy score tables.",
    )
    parser.add_argument(
        "--resume-v2",
        action="store_true",
        help=(
            "Skip only pairs that already have both metro_score_v2 and seo_facts rows. "
            "Use this for V2-aware recovery without skipping legacy-only pairs."
        ),
    )
    parser.add_argument(
        "--retry-failed-from",
        type=Path,
        default=None,
        help="Retry only failed or partial_failure pairs from a bulk-score JSONL audit.",
    )
    parser.add_argument(
        "--cities",
        type=int,
        default=50,
        help="Number of metros to select (default: 50).",
    )
    parser.add_argument(
        "--strategy",
        choices=("rank-and-rent", "top-population"),
        default="rank-and-rent",
        help="Metro selection strategy (default: rank-and-rent).",
    )
    parser.add_argument(
        "--population-class",
        dest="population_classes",
        action="append",
        default=None,
        help="Restrict to a population_class; repeat for multiple classes.",
    )
    parser.add_argument(
        "--min-population",
        type=int,
        default=None,
        help="Minimum metro population to include.",
    )
    parser.add_argument(
        "--max-population",
        type=int,
        default=None,
        help="Maximum metro population to include.",
    )
    parser.add_argument(
        "--require-dfs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require at least one DataForSEO location code (default: true).",
    )
    parser.add_argument(
        "--mega-cap",
        type=int,
        default=5,
        help="Maximum mega_5m_plus metros to include (default: 5).",
    )
    parser.add_argument(
        "--services",
        type=int,
        default=12,
        help="Number of services from the catalog (default: 12).",
    )
    parser.add_argument(
        "--service-name",
        dest="service_names",
        action="append",
        default=None,
        help="Explicit service to score. Repeat to build a custom service list.",
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
        help="FastAPI base URL (default: NEXT_PUBLIC_API_URL or http://localhost:8000).",
    )
    parser.add_argument(
        "--results-path",
        type=Path,
        default=None,
        help=(
            "JSONL audit output path. Defaults to scripts/explore/bulk_score_results.jsonl."
        ),
    )
    parser.add_argument(
        "--require-v2-persistence",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require metro_score_v2 and seo_facts rows before counting success (default: true).",
    )
    args = parser.parse_args()

    if args.resume and args.resume_v2:
        parser.error("Use either --resume or --resume-v2, not both")
    if args.retry_failed_from and (args.resume or args.resume_v2):
        parser.error("--retry-failed-from cannot be combined with --resume or --resume-v2")

    if args.refresh_only:
        refresh_matview_sql()
        return

    if not args.preview and not args.apply:
        parser.error("Specify --preview or --apply")

    args.concurrency = max(1, min(20, args.concurrency))
    if args.mega_cap is not None:
        args.mega_cap = max(0, args.mega_cap)
    if args.population_classes:
        args.population_classes = list(dict.fromkeys(args.population_classes))

    asyncio.run(run_bulk_score(args))


if __name__ == "__main__":
    main()
