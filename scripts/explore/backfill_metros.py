"""Backfill public.metros from the CBSA seed plus ACS demographic data."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "src/data/seed/cbsa_seed.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def derive_population_class(population: int | None) -> str | None:
    if population is None:
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


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return round(float(value), 1)


def _rate(owner: Any, total: Any) -> float | None:
    owner_int = _int_or_none(owner)
    total_int = _int_or_none(total)
    if owner_int is None or total_int is None or total_int == 0:
        return None
    return round(owner_int / total_int, 4)


def build_metro_payload(
    seed: dict[str, Any],
    acs: dict[str, Any] | None,
    *,
    acs_loaded_at: str | None = None,
) -> dict[str, Any]:
    acs = acs or {}
    population = _int_or_none(acs.get("total_population")) or _int_or_none(
        seed.get("population"),
    )
    households = _int_or_none(acs.get("total_housing_units"))
    owner_units = _int_or_none(acs.get("owner_occupied_units"))
    renter_units = _int_or_none(acs.get("renter_occupied_units"))
    if renter_units is None and households is not None and owner_units is not None:
        renter_units = households - owner_units

    return {
        "cbsa_code": str(seed["cbsa_code"]),
        "cbsa_name": seed["cbsa_name"],
        "state": seed["state"],
        "cbsa_type": seed.get("cbsa_type"),
        "population": population,
        "principal_cities": seed.get("principal_cities", []),
        "dataforseo_location_codes": seed.get("dataforseo_location_codes", []),
        "households": households,
        "owner_occupied_housing_units": owner_units,
        "renter_occupied_housing_units": renter_units,
        "owner_occupancy_rate": _rate(owner_units, households),
        "median_household_income_usd": _int_or_none(
            acs.get("median_household_income"),
        ),
        "median_year_structure_built": _int_or_none(acs.get("median_year_built")),
        "median_age_years": _float_or_none(acs.get("median_age_years")),
        "acs_vintage": _int_or_none(acs.get("acs_vintage")),
        "acs_loaded_at": acs_loaded_at if acs else None,
        "population_class": derive_population_class(population),
    }


def load_seed(path: Path = SEED_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


async def load_acs_by_cbsa(year: int) -> dict[str, dict[str, Any]]:
    from src.clients.census.client import CensusClient

    client = CensusClient(api_key=os.environ.get("CENSUS_API_KEY"), year=year)
    rows = await client.fetch_msa_demographics()
    by_cbsa: dict[str, dict[str, Any]] = {}
    for row in rows:
        cbsa_code = row.get("cbsa_code")
        if cbsa_code:
            enriched = dict(row)
            enriched["acs_vintage"] = year
            by_cbsa[str(cbsa_code)] = enriched
    return by_cbsa


def postgrest_upsert(url: str, service_key: str, rows: list[dict[str, Any]]) -> None:
    endpoint = (
        f"{url.rstrip('/')}/rest/v1/metros?"
        f"{parse.urlencode({'on_conflict': 'cbsa_code'})}"
    )
    payload = json.dumps(rows).encode("utf-8")
    req = request.Request(
        endpoint,
        data=payload,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            response.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(
            f"PostgREST upsert failed with HTTP {exc.code}: {body}",
        ) from exc


def _build_rows(
    seed_rows: list[dict[str, Any]],
    acs_by_cbsa: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    acs_loaded_at = datetime.now(timezone.utc).isoformat()
    return [
        build_metro_payload(
            seed,
            acs_by_cbsa.get(str(seed["cbsa_code"])),
            acs_loaded_at=acs_loaded_at,
        )
        for seed in seed_rows
    ]


def _sanitize_exception(exc: Exception) -> str:
    return f"{type(exc).__name__}: ACS demographic request failed"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2022)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    seed_rows = load_seed()
    try:
        acs_by_cbsa = await load_acs_by_cbsa(args.year)
    except Exception as exc:  # noqa: BLE001 - CLI must fail without tracebacks.
        print(f"ACS fetch failed: {_sanitize_exception(exc)}")
        return 1
    rows = _build_rows(seed_rows, acs_by_cbsa)

    if not args.apply:
        print(json.dumps(rows[:5], indent=2, sort_keys=True))
        print("dry_run=true")
        print(f"prepared_rows={len(rows)}")
        return 0

    supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    missing = [
        name
        for name, value in (
            ("NEXT_PUBLIC_SUPABASE_URL", supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", service_key),
        )
        if not value
    ]
    if missing:
        print(f"Missing Supabase environment variable(s): {', '.join(missing)}")
        print("No live mutation ran.")
        return 2

    postgrest_upsert(supabase_url, service_key, rows)
    print(f"upserted_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
