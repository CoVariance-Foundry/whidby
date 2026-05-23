"""Guarded apply path for enriching metros with DataForSEO location codes."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.explore.audit_metro_dfs_readiness import (
    fetch_dfs_locations,
    fetch_metros,
    load_env,
    supabase_client,
    validate_expected_project_ref,
)
from scripts.explore.metro_dfs_readiness import (
    MetroDfsReadinessMatch,
    match_metros,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROVENANCE_COLUMNS = (
    "dataforseo_location_match_name",
    "dataforseo_location_match_confidence",
    "dataforseo_location_match_source",
    "dataforseo_location_verified_at",
    "dataforseo_location_review_reason",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report candidate updates only. This is the default behavior.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply selected updates to public.metros.",
    )
    parser.add_argument(
        "--expected-project-ref",
        default=None,
        help="Required with --apply; must match NEXT_PUBLIC_SUPABASE_URL.",
    )
    parser.add_argument(
        "--confidence",
        choices=("exact", "strong"),
        default="exact",
        help="exact applies exact matches only; strong also applies approved strong rows.",
    )
    parser.add_argument(
        "--approved-csv",
        type=Path,
        default=None,
        help="CSV of approved strong matches. Required with --confidence strong.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of selected candidate rows to process.",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print JSON only and do not write timestamped report files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/metro_readiness"),
        help="Directory for timestamped JSON and CSV outputs.",
    )
    args = parser.parse_args(argv)
    args.dry_run = not args.apply
    return args


def validate_args(args: argparse.Namespace) -> None:
    if args.apply and not args.expected_project_ref:
        raise RuntimeError("--expected-project-ref is required with --apply")
    if args.limit is not None and args.limit < 1:
        raise RuntimeError("--limit must be a positive integer")
    if args.confidence == "strong" and args.approved_csv is None:
        raise RuntimeError("--approved-csv is required with --confidence strong")
    if args.apply:
        validate_expected_project_ref(args.expected_project_ref)


def load_approved_strong_rows(path: Path | None) -> set[tuple[str, int]]:
    if path is None:
        return set()
    approved: set[tuple[str, int]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            approved_value = row.get("approved")
            if approved_value is not None and not _truthy(approved_value):
                continue
            cbsa_code = str(row.get("cbsa_code") or "").strip()
            location_code = _int_or_none(
                row.get("selected_location_code")
                or row.get("location_code")
                or row.get("dataforseo_location_code")
            )
            if cbsa_code and location_code is not None:
                approved.add((cbsa_code, location_code))
    return approved


def select_candidates(
    matches: list[MetroDfsReadinessMatch],
    *,
    confidence: str,
    approved_strong_rows: set[tuple[str, int]],
    limit: int | None,
) -> list[MetroDfsReadinessMatch]:
    candidates: list[MetroDfsReadinessMatch] = []
    for match in matches:
        if match.status == "exact":
            candidates.append(match)
        elif (
            confidence == "strong"
            and match.status == "strong"
            and match.selected_location_code is not None
            and (match.cbsa_code, match.selected_location_code) in approved_strong_rows
        ):
            candidates.append(match)
    return candidates[:limit] if limit is not None else candidates


def build_summary(
    *,
    matches: list[MetroDfsReadinessMatch],
    candidates: list[MetroDfsReadinessMatch],
    dry_run: bool,
    applied_rows: list[dict[str, Any]],
    provenance_columns_missing: bool,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "dry_run": dry_run,
        "matched_count": len(matches),
        "candidate_count": len(candidates),
        "applied_count": 0 if dry_run else len(applied_rows),
        "skipped_count": len(matches) - len(candidates),
        "provenance_columns_missing": provenance_columns_missing,
        "applied_rows": applied_rows,
        "candidate_rows": [
            _candidate_detail(candidate, provenance_columns_missing=False)
            for candidate in candidates
        ],
    }


def apply_candidates(
    supabase: Any,
    candidates: list[MetroDfsReadinessMatch],
) -> tuple[list[dict[str, Any]], bool]:
    applied_rows: list[dict[str, Any]] = []
    provenance_columns_missing = False
    verified_at = datetime.now(timezone.utc).isoformat()
    for match in candidates:
        payload = _update_payload(match, verified_at=verified_at, include_provenance=True)
        try:
            _update_metro(supabase, match.cbsa_code, payload)
        except Exception as exc:
            if _is_missing_provenance_column_error(exc):
                provenance_columns_missing = True
                raise RuntimeError(
                    "Provenance columns are missing or schema cache is stale; "
                    "aborting apply without codes-only fallback."
                ) from exc
            raise
        applied_rows.append(
            _candidate_detail(
                match,
                provenance_columns_missing=False,
            )
        )
    return applied_rows, provenance_columns_missing


def build_report(
    *,
    supabase: Any,
    dfs_locations: list[dict[str, Any]],
    dry_run: bool,
    confidence: str,
    approved_strong_rows: set[tuple[str, int]],
    limit: int | None,
) -> dict[str, Any]:
    metros = fetch_metros(supabase)
    matches = match_metros(metros, dfs_locations)
    candidates = select_candidates(
        matches,
        confidence=confidence,
        approved_strong_rows=approved_strong_rows,
        limit=limit,
    )
    applied_rows: list[dict[str, Any]] = []
    provenance_columns_missing = False
    if not dry_run:
        applied_rows, provenance_columns_missing = apply_candidates(supabase, candidates)
    return build_summary(
        matches=matches,
        candidates=candidates,
        dry_run=dry_run,
        applied_rows=applied_rows,
        provenance_columns_missing=provenance_columns_missing,
    )


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"metro_dfs_enrichment_{timestamp}.json"
    csv_path = output_dir / f"metro_dfs_enrichment_candidates_{timestamp}.csv"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "cbsa_code",
            "cbsa_name",
            "status",
            "selected_location_code",
            "selected_location_name",
            "existing_codes",
            "dataforseo_location_codes",
            "provenance_columns_missing",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["candidate_rows"]:
            writer.writerow(row)
    return json_path, csv_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        load_env()
        validate_args(args)
        report = build_report(
            supabase=supabase_client(),
            dfs_locations=asyncio.run(fetch_dfs_locations()),
            dry_run=args.dry_run,
            confidence=args.confidence,
            approved_strong_rows=load_approved_strong_rows(args.approved_csv),
            limit=args.limit,
        )
    except RuntimeError as exc:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "fail",
            "dry_run": not args.apply,
            "failures": [str(exc)],
        }

    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "ok" and not args.stdout_only:
        json_path, csv_path = write_reports(report, args.output_dir)
        print(f"wrote_json={json_path}")
        print(f"wrote_candidates_csv={csv_path}")
    return 1 if report["status"] == "fail" else 0


def _update_payload(
    match: MetroDfsReadinessMatch,
    *,
    verified_at: str,
    include_provenance: bool,
) -> dict[str, Any]:
    selected_location_code = match.selected_location_code
    if selected_location_code is None:
        raise RuntimeError(f"Cannot update {match.cbsa_code}: missing selected code")
    payload: dict[str, Any] = {
        "dataforseo_location_codes": _dedupe_codes(
            [selected_location_code, *match.existing_codes]
        )
    }
    if include_provenance:
        payload.update(
            {
                "dataforseo_location_match_name": match.selected_location_name,
                "dataforseo_location_match_confidence": match.status,
                "dataforseo_location_match_source": "metro_dfs_readiness",
                "dataforseo_location_verified_at": verified_at,
                "dataforseo_location_review_reason": match.reason,
            }
        )
    return payload


def _update_metro(supabase: Any, cbsa_code: str, payload: dict[str, Any]) -> None:
    response = (
        supabase.table("metros")
        .update(payload)
        .eq("cbsa_code", cbsa_code)
        .execute()
    )
    data = getattr(response, "data", None)
    if data is not None and len(data) != 1:
        raise RuntimeError(
            "Supabase update failed closed: expected exactly one metros row "
            f"for cbsa_code={cbsa_code}, got {len(data)}"
        )


def _candidate_detail(
    match: MetroDfsReadinessMatch,
    *,
    provenance_columns_missing: bool,
) -> dict[str, Any]:
    codes = _dedupe_codes([match.selected_location_code, *match.existing_codes])
    return {
        "cbsa_code": match.cbsa_code,
        "cbsa_name": match.cbsa_name,
        "status": match.status,
        "selected_location_code": match.selected_location_code,
        "selected_location_name": match.selected_location_name,
        "existing_codes": list(match.existing_codes),
        "dataforseo_location_codes": codes,
        "provenance_columns_missing": provenance_columns_missing,
    }


def _dedupe_codes(values: list[int | None]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        if value is None:
            continue
        code = int(value)
        if code in seen:
            continue
        seen.add(code)
        result.append(code)
    return result


def _truthy(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "t", "yes", "y"}


def _is_missing_provenance_column_error(exc: Exception) -> bool:
    message = str(exc).casefold()
    missing_column_patterns = (
        "column {column} does not exist",
        "column \"{column}\" does not exist",
        "could not find the '{column}' column",
        "could not find the \"{column}\" column",
        "column '{column}' does not exist",
    )
    provenance_column_missing = any(
        pattern.format(column=column) in message
        for column in PROVENANCE_COLUMNS
        for pattern in missing_column_patterns
    )
    schema_cache_missing = (
        "schema cache" in message
        and any(token in message for token in ("could not find", "not found", "missing"))
        and any(column in message for column in PROVENANCE_COLUMNS)
    )
    return provenance_column_missing or schema_cache_missing


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
