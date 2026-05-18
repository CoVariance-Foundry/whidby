"""Read-only audit for Explore source table visibility and sparse fields."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse, request


REQUIRED_TABLES = (
    "metros",
    "census_cbp_establishments",
    "niche_naics_mapping",
    "reports",
    "metro_scores",
    "metro_score_v2",
    "explore_market_cells",
    "seo_facts",
    "seo_benchmarks",
)

REQUIRED_NON_NULL_FIELDS = {
    "metros": (
        "population",
        "median_household_income_usd",
        "population_class",
    ),
}

OPTIONAL_NON_NULL_FIELDS = {
    "metros": (
        "owner_occupancy_rate",
        "median_age_years",
    ),
}

CBP_YEAR_CANDIDATES = tuple(range(2010, 2031))


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    key: str

    @property
    def rest_url(self) -> str:
        return f"{self.url.rstrip('/')}/rest/v1"


def summarize_table_health(
    *,
    table: str,
    row_count: int,
    non_null_counts: dict[str, int],
    error: str | None = None,
) -> dict[str, Any]:
    required_fields = REQUIRED_NON_NULL_FIELDS.get(table, ())
    optional_fields = OPTIONAL_NON_NULL_FIELDS.get(table, ())
    missing_required = [
        field for field in required_fields if non_null_counts.get(field, 0) == 0
    ]
    missing_optional = [
        field
        for field in optional_fields
        if field in non_null_counts and non_null_counts[field] == 0
    ]

    if error or row_count == 0 or missing_required:
        status = "fail"
    elif missing_optional:
        status = "warn"
    else:
        status = "pass"

    summary: dict[str, Any] = {
        "table": table,
        "row_count": row_count,
        "status": status,
        "missing_required_fields": missing_required,
        "missing_optional_fields": missing_optional,
        "non_null_counts": non_null_counts,
    }
    if error:
        summary["error"] = error
    return summary


def summarize_explore_readiness(
    *,
    explore_market_cells_count: int,
    market_cells_with_density: int,
    cbp_years: list[int],
    errors: list[str] | None = None,
) -> dict[str, Any]:
    growth_available = len(cbp_years) >= 2
    status = "pass"
    messages: list[str] = []

    if explore_market_cells_count == 0:
        status = "fail"
        messages.append("explore_market_cells has no rows")
    if market_cells_with_density == 0:
        status = "warn" if status == "pass" else status
        messages.append("explore_market_cells has no density metrics")
    if not growth_available:
        status = "warn" if status == "pass" else status
        messages.append(
            f"growth unavailable: census_cbp_establishments has {len(cbp_years)} year loaded",
        )
    if errors:
        status = "fail"
        messages.extend(errors)

    return {
        "table": "explore_readiness",
        "status": status,
        "explore_market_cells_count": explore_market_cells_count,
        "market_cells_with_density": market_cells_with_density,
        "cbp_years": cbp_years,
        "growth_available": growth_available,
        "message": "; ".join(messages) if messages else "explore data ready",
    }


def load_env(env_path: Path | None = None) -> dict[str, str]:
    path = env_path or Path("apps/app/.env.local")
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            env[key.strip()] = value.strip().strip("'\"")

    env.update(os.environ)
    return env


def config_from_env(
    env: dict[str, str],
    *,
    service_role: bool = False,
) -> SupabaseConfig:
    url = env.get("NEXT_PUBLIC_SUPABASE_URL", "")
    key_name = (
        "SUPABASE_SERVICE_ROLE_KEY"
        if service_role
        else "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY"
    )
    key = env.get(key_name, "")

    missing = [
        name
        for name, value in (
            ("NEXT_PUBLIC_SUPABASE_URL", url),
            (key_name, key),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Missing Supabase environment variable(s): {', '.join(missing)}")

    return SupabaseConfig(url=url, key=key)


def postgrest_get(
    config: SupabaseConfig,
    table: str,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], str]:
    query = parse.urlencode(params or {})
    url = f"{config.rest_url}/{parse.quote(table)}"
    if query:
        url = f"{url}?{query}"

    request_headers = {
        "apikey": config.key,
        "Authorization": f"Bearer {config.key}",
        "Accept": "application/json",
    }
    request_headers.update(headers or {})
    req = request.Request(url, headers=request_headers, method="GET")

    try:
        with request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers.items()), body
    except Exception as exc:  # noqa: BLE001 - audit output should capture all failures.
        status = getattr(exc, "code", 0)
        error_body = getattr(exc, "read", lambda: b"")()
        body = error_body.decode("utf-8") if error_body else json.dumps({"error": str(exc)})
        return int(status or 0), {}, body


def _parse_count(headers: dict[str, str]) -> int:
    content_range = headers.get("Content-Range") or headers.get("content-range", "")
    if "/" not in content_range:
        return 0
    total = content_range.rsplit("/", 1)[1]
    if total == "*":
        return 0
    try:
        return int(total)
    except ValueError:
        return 0


def _count_error(table: str, status: int, body: str) -> str:
    return f"{table} count request failed with HTTP {status}: {body}"


def get_count(
    config: SupabaseConfig,
    table: str,
    params: dict[str, str] | None = None,
) -> tuple[int, str | None]:
    query_params = {
        "select": "*",
        "limit": "1",
    }
    query_params.update(params or {})
    status, headers, body = postgrest_get(
        config,
        table,
        params=query_params,
        headers={"Prefer": "count=exact", "Range": "0-0"},
    )
    if status < 200 or status >= 300:
        return 0, _count_error(table, status, body)
    return _parse_count(headers), None


def get_non_null_count(
    config: SupabaseConfig,
    table: str,
    field: str,
) -> tuple[int, str | None]:
    status, headers, body = postgrest_get(
        config,
        table,
        params={
            "select": field,
            field: "not.is.null",
            "limit": "1",
        },
        headers={"Prefer": "count=exact", "Range": "0-0"},
    )
    if status < 200 or status >= 300:
        return 0, _count_error(f"{table}.{field}", status, body)
    return _parse_count(headers), None


def get_cbp_years(config: SupabaseConfig) -> tuple[list[int], str | None]:
    years: list[int] = []
    errors: list[str] = []
    for year in CBP_YEAR_CANDIDATES:
        count, error = get_count(
            config,
            "census_cbp_establishments",
            params={"year": f"eq.{year}"},
        )
        if error:
            errors.append(error)
        elif count > 0:
            years.append(year)
    return years, "; ".join(errors) if errors else None


def audit(config: SupabaseConfig) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for table in REQUIRED_TABLES:
        row_count, error = get_count(config, table)
        non_null_counts: dict[str, int] = {}
        field_errors: list[str] = []

        fields = REQUIRED_NON_NULL_FIELDS.get(table, ()) + OPTIONAL_NON_NULL_FIELDS.get(
            table,
            (),
        )
        for field in fields:
            count, field_error = get_non_null_count(config, table, field)
            non_null_counts[field] = count
            if field_error:
                field_errors.append(field_error)

        errors = [item for item in (error, *field_errors) if item]
        summaries.append(
            summarize_table_health(
                table=table,
                row_count=row_count,
                non_null_counts=non_null_counts,
                error="; ".join(errors) if errors else None,
            ),
        )
    market_cells_count, market_cells_error = get_count(config, "explore_market_cells")
    market_cells_with_density, density_error = get_non_null_count(
        config,
        "explore_market_cells",
        "business_density_per_1k",
    )
    cbp_years, years_error = get_cbp_years(config)
    readiness_errors = [
        item for item in (market_cells_error, density_error, years_error) if item
    ]
    summaries.append(
        summarize_explore_readiness(
            explore_market_cells_count=market_cells_count,
            market_cells_with_density=market_cells_with_density,
            cbp_years=cbp_years,
            errors=readiness_errors,
        ),
    )
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--service-role",
        action="store_true",
        help="Use SUPABASE_SERVICE_ROLE_KEY instead of the publishable app key.",
    )
    args = parser.parse_args()

    try:
        config = config_from_env(load_env(), service_role=args.service_role)
        summaries = audit(config)
    except ValueError as exc:
        summaries = [
            {
                "table": "environment",
                "row_count": 0,
                "status": "fail",
                "missing_required_fields": [],
                "missing_optional_fields": [],
                "non_null_counts": {},
                "error": str(exc),
            },
        ]

    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 1 if any(summary["status"] == "fail" for summary in summaries) else 0


if __name__ == "__main__":
    raise SystemExit(main())
