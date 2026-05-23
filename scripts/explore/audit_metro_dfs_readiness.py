"""Read-only audit for maximizing DFS-ready metros."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.explore.metro_dfs_readiness import (
    MetroDfsReadinessMatch,
    match_metros,
    residual_review_classification,
    residual_seed_policy,
    summarize_matches,
)
from src.clients.dataforseo.client import DataForSEOClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAGE_SIZE = 1000
METRO_COLUMNS = (
    "cbsa_code",
    "cbsa_name",
    "state",
    "population",
    "population_class",
    "principal_cities",
    "dataforseo_location_codes",
)


def load_env(env_path: Path | None = None) -> None:
    """Load root .env values without overwriting already-exported values."""
    path = env_path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def supabase_project_ref(supabase_url: str) -> str | None:
    """Extract a project ref only from exact https://<ref>.supabase.co hosts."""
    parsed = urlparse(supabase_url.strip())
    if parsed.scheme != "https" or parsed.hostname is None:
        return None
    suffix = ".supabase.co"
    if not parsed.hostname.endswith(suffix):
        return None
    project_ref = parsed.hostname[: -len(suffix)]
    if not project_ref or "." in project_ref:
        return None
    return project_ref


def validate_expected_project_ref(expected_project_ref: str | None) -> None:
    """Fail closed before reading production data if the project ref is wrong."""
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


def fetch_metros(supabase: Any) -> list[dict[str, Any]]:
    """Fetch all metros using paginated read-only selects."""
    rows: list[dict[str, Any]] = []
    offset = 0
    select_columns = ",".join(METRO_COLUMNS)
    while True:
        try:
            response = (
                supabase.table("metros")
                .select(select_columns)
                .order("population", desc=True)
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
        except Exception as exc:
            raise RuntimeError(
                f"metros missing required column(s): {select_columns}; {exc}"
            ) from exc
        page = list(response.data or [])
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


async def fetch_dfs_locations() -> list[dict[str, Any]]:
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    missing = [
        name
        for name, value in (
            ("DATAFORSEO_LOGIN", login),
            ("DATAFORSEO_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing DataForSEO environment variable(s): " + ", ".join(missing)
        )
    response = await DataForSEOClient(
        login,
        password,
        persistent_cache=False,
    ).locations()
    if response.status != "ok":
        raise RuntimeError(f"DataForSEO locations API failed: {response.error}")
    rows = _extract_location_rows(response.data)
    if not rows:
        raise RuntimeError("DataForSEO locations API returned no location rows")
    return rows


def build_report(
    metros: list[dict[str, Any]],
    dfs_locations: list[dict[str, Any]],
) -> dict[str, Any]:
    matches = match_metros(metros, dfs_locations)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "metro_count": len(metros),
        "dfs_location_count": len(dfs_locations),
        "summary": summarize_matches(matches),
        "matches": [match.asdict() for match in matches],
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"metro_dfs_readiness_{timestamp}.json"
    candidates_path = output_dir / f"metro_dfs_readiness_candidates_{timestamp}.csv"
    review_path = output_dir / f"metro_dfs_readiness_review_{timestamp}.csv"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    matches = [MetroDfsReadinessMatch(**row) for row in report["matches"]]
    _write_match_csv(candidates_path, matches)
    _write_match_csv(
        review_path,
        [
            match
            for match in matches
            if match.status in {"ambiguous", "invalid_existing_code", "no_match"}
        ],
    )
    return json_path, candidates_path, review_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-project-ref",
        default=None,
        help="Optional Supabase project ref guard for NEXT_PUBLIC_SUPABASE_URL.",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print JSON only and do not write report files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/metro_readiness"),
        help="Directory for timestamped JSON and CSV audit outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        load_env()
        validate_expected_project_ref(args.expected_project_ref)
        report = build_report(
            fetch_metros(supabase_client()),
            asyncio.run(fetch_dfs_locations()),
        )
    except RuntimeError as exc:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "fail",
            "failures": [str(exc)],
        }

    print(json.dumps(_stdout_report(report), indent=2, sort_keys=True))
    if report["status"] == "ok" and not args.stdout_only:
        json_path, candidates_path, review_path = write_reports(report, args.output_dir)
        print(f"wrote_json={json_path}")
        print(f"wrote_candidates_csv={candidates_path}")
        print(f"wrote_review_csv={review_path}")
    return 1 if report["status"] == "fail" else 0


def _extract_location_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for key in ("result", "locations", "data"):
            rows = _extract_location_rows(data.get(key))
            if rows:
                return rows
        tasks = data.get("tasks")
        if isinstance(tasks, list):
            for task in tasks:
                rows = _extract_location_rows(task)
                if rows:
                    return rows
    return []


def _write_match_csv(path: Path, matches: list[MetroDfsReadinessMatch]) -> None:
    fieldnames = [
        *list(MetroDfsReadinessMatch.__dataclass_fields__.keys()),
        "residual_review_classification",
        "production_seed_policy",
        "approval_artifact_required",
        "review_notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for match in matches:
            row = match.asdict()
            row["existing_codes"] = ",".join(str(code) for code in match.existing_codes)
            row["residual_review_classification"] = residual_review_classification(
                match.status
            )
            row["production_seed_policy"] = residual_seed_policy(match.status)
            row["approval_artifact_required"] = (
                "yes" if row["production_seed_policy"] == "excluded_until_reviewed" else "no"
            )
            row["review_notes"] = ""
            writer.writerow(row)


def _stdout_report(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("status") != "ok":
        return report
    return {key: value for key, value in report.items() if key != "matches"}


if __name__ == "__main__":
    raise SystemExit(main())
