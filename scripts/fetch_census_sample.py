"""Fetch a 100-row sample from the Census ACS API via CensusClient.

Usage:
    python3.11 -m scripts.fetch_census_sample
    python3.11 -m scripts.fetch_census_sample --year 2021 --limit 50
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from src.clients.census.client import CensusClient


async def main(year: int, limit: int) -> None:
    client = CensusClient(year=year)
    all_rows = await client.fetch_msa_demographics()

    # Sort by population descending so the sample shows the largest MSAs
    all_rows.sort(
        key=lambda r: r.get("total_population") or 0,
        reverse=True,
    )
    sample = all_rows[:limit]

    print(f"Fetched {len(all_rows)} MSAs from ACS {year}, showing top {len(sample)}:\n")
    print(f"{'CBSA':<8} {'Population':>12} {'Med Income':>12} {'Owner%':>8} {'Broadband%':>10}  Name")
    print("-" * 90)

    for row in sample:
        pop = row.get("total_population")
        income = row.get("median_household_income")
        owner = row.get("owner_occupied_units")
        total_h = row.get("total_housing_units")
        bb = row.get("broadband_subscriptions")
        bb_total = row.get("total_internet_universe")

        owner_pct = f"{owner / total_h:.0%}" if owner and total_h else "—"
        bb_pct = f"{bb / bb_total:.0%}" if bb and bb_total else "—"

        print(
            f"{row['cbsa_code']:<8} "
            f"{pop or 0:>12,} "
            f"{income or 0:>12,} "
            f"{owner_pct:>8} "
            f"{bb_pct:>10}  "
            f"{row['name']}"
        )

    # Also dump raw JSON for the first 5 rows
    print(f"\n--- Raw JSON (first 5 of {len(sample)}) ---")
    print(json.dumps(sample[:5], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Census ACS sample data")
    parser.add_argument("--year", type=int, default=2022, help="ACS year (default: 2022)")
    parser.add_argument("--limit", type=int, default=100, help="Number of rows (default: 100)")
    args = parser.parse_args()
    asyncio.run(main(args.year, args.limit))
