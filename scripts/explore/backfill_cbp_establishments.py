"""Prepare and optionally upsert CBP establishment rows for Explore."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request


INTEGER_FIELDS = (
    "est",
    "n1_4",
    "n5_9",
    "n10_19",
    "n20_49",
    "n50_99",
    "n100_249",
    "n250_499",
    "n500_999",
    "n1000",
    "emp",
    "ap",
)

ALIASES = {
    "naics_code": ("naics_code", "naics", "NAICS2017", "NAICS2022"),
    "naics_label": ("naics_label", "label", "NAICS2017_LABEL", "NAICS2022_LABEL"),
    "est": ("est", "establishments", "ESTAB"),
    "emp": ("emp", "employees", "EMP"),
    "ap": ("ap", "payroll_thousands", "PAYANN"),
}


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _first_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and value != "":
            return value
    return None


def _require_value(row: dict[str, Any], keys: tuple[str, ...], field: str, row_number: int) -> Any:
    value = _first_value(row, keys)
    if value is None:
        raise ValueError(f"row {row_number} missing required {field}")
    return value


def build_cbp_payload(row: dict[str, Any], *, row_number: int = 1) -> dict[str, Any]:
    """Map an already-fetched CBP row to public.census_cbp_establishments."""
    cbsa_code = _require_value(row, ("cbsa_code",), "cbsa_code", row_number)
    naics_code = _require_value(row, ALIASES["naics_code"], "naics_code", row_number)
    year = _require_value(row, ("year",), "year", row_number)

    payload: dict[str, Any] = {
        "cbsa_code": str(cbsa_code),
        "naics_code": str(naics_code),
        "naics_label": _first_value(row, ALIASES["naics_label"]),
        "year": _int_or_none(year),
        "empflag": row.get("empflag"),
    }
    for field in INTEGER_FIELDS:
        keys = ALIASES.get(field, (field,))
        payload[field] = _int_or_none(_first_value(row, keys))

    payload["suppressed"] = payload["est"] is None and payload["empflag"] is not None
    return payload


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("rows")
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list or an object with a rows list")
        return [dict(row) for row in data]

    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    raise ValueError("Input must be a .json or .csv file")


def postgrest_upsert(url: str, service_key: str, rows: list[dict[str, Any]]) -> None:
    endpoint = (
        f"{url.rstrip('/')}/rest/v1/census_cbp_establishments"
        "?on_conflict=cbsa_code,naics_code,year"
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
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"PostgREST upsert failed with HTTP {response.status}")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(
            f"PostgREST upsert failed with HTTP {exc.code}: {body}",
        ) from exc


def _build_rows(path: Path) -> list[dict[str, Any]]:
    return [
        build_cbp_payload(row, row_number=index)
        for index, row in enumerate(load_rows(path), start=1)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to already-fetched CBP rows as JSON or CSV.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.input is None:
        print("No input file or verified CBP fetch source provided. No live mutation ran.")
        return 1

    try:
        rows = _build_rows(args.input)
    except Exception as exc:  # noqa: BLE001 - CLI should fail without tracebacks.
        print(f"CBP input import failed: {type(exc).__name__}: {exc}")
        print("No live mutation ran.")
        return 1

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
    raise SystemExit(main())
