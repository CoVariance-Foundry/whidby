"""Enrich sampled benchmark metros with DataForSEO location codes.

Usage:
  .venv/bin/python -m scripts.benchmarks.enrich_dfs_codes --dry-run
  .venv/bin/python -m scripts.benchmarks.enrich_dfs_codes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.clients.dataforseo import DataForSEOClient  # noqa: E402

METROS_PATH = Path(__file__).parent / "metros_sampled.json"
CITY_TYPES = frozenset({"city", "city council", "municipality", "town"})
US_STATE_NAMES = {
    "AL": "alabama",
    "AK": "alaska",
    "AZ": "arizona",
    "AR": "arkansas",
    "CA": "california",
    "CO": "colorado",
    "CT": "connecticut",
    "DE": "delaware",
    "DC": "district of columbia",
    "FL": "florida",
    "GA": "georgia",
    "HI": "hawaii",
    "ID": "idaho",
    "IL": "illinois",
    "IN": "indiana",
    "IA": "iowa",
    "KS": "kansas",
    "KY": "kentucky",
    "LA": "louisiana",
    "ME": "maine",
    "MD": "maryland",
    "MA": "massachusetts",
    "MI": "michigan",
    "MN": "minnesota",
    "MS": "mississippi",
    "MO": "missouri",
    "MT": "montana",
    "NE": "nebraska",
    "NV": "nevada",
    "NH": "new hampshire",
    "NJ": "new jersey",
    "NM": "new mexico",
    "NY": "new york",
    "NC": "north carolina",
    "ND": "north dakota",
    "OH": "ohio",
    "OK": "oklahoma",
    "OR": "oregon",
    "PA": "pennsylvania",
    "RI": "rhode island",
    "SC": "south carolina",
    "SD": "south dakota",
    "TN": "tennessee",
    "TX": "texas",
    "UT": "utah",
    "VT": "vermont",
    "VA": "virginia",
    "WA": "washington",
    "WV": "west virginia",
    "WI": "wisconsin",
    "WY": "wyoming",
}


def normalize(text: str) -> str:
    """Normalize human place names for matching."""
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


def candidate_cities(cbsa_name: str) -> list[str]:
    """Return city candidates from the city-side of a CBSA display name."""
    prefix = cbsa_name.split(",", 1)[0]
    return [part.strip() for part in re.split(r"[-–]+", prefix) if part.strip()]


def extract_location_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, list):
            return [row for row in result if isinstance(row, dict)]
    return []


def build_index(locations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for loc in locations:
        if str(loc.get("location_type", "")).lower() not in CITY_TYPES:
            continue
        name = str(loc.get("location_name", "")).split(",", 1)[0]
        key = normalize(name)
        if key:
            index.setdefault(key, []).append(loc)
    return index


def state_tokens(state: str) -> set[str]:
    state_code = state.strip().upper()
    tokens = {normalize(state_code)} if state_code else set()
    state_name = US_STATE_NAMES.get(state_code)
    if state_name:
        tokens.add(state_name)
    return tokens


def location_matches_state(loc: dict[str, Any], state: str) -> bool:
    tokens = state_tokens(state)
    if not tokens:
        return True

    location_name = normalize(str(loc.get("location_name", "")))
    return any(token and re.search(rf"\b{re.escape(token)}\b", location_name) for token in tokens)


def resolve_codes(metro: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> list[int]:
    codes: list[int] = []
    for city in candidate_cities(str(metro["cbsa_name"])):
        for loc in index.get(normalize(city), []):
            if str(loc.get("country_iso_code", "")).upper() != "US":
                continue
            if not location_matches_state(loc, str(metro.get("state", ""))):
                continue
            code = loc.get("location_code")
            if isinstance(code, int) and code not in codes:
                codes.append(code)
    return codes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrich sampled benchmark metros with DataForSEO location codes."
    )
    parser.add_argument("--dry-run", action="store_true", help="Print enrichment count only.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise SystemExit("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are required")

    metros = json.loads(METROS_PATH.read_text())
    client = DataForSEOClient(login=login, password=password, persistent_cache=False)
    response = await client.locations()
    if response.status != "ok":
        raise SystemExit(f"DataForSEO locations() failed: {response.error}")

    index = build_index(extract_location_rows(response.data))

    enriched = 0
    for metro in metros:
        if metro.get("dataforseo_location_codes"):
            continue
        codes = resolve_codes(metro, index)
        if codes:
            metro["dataforseo_location_codes"] = codes
            metro["_dfs_source"] = "enriched"
            enriched += 1

    print(f"enriched={enriched}")
    if not args.dry_run:
        METROS_PATH.write_text(json.dumps(metros, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
