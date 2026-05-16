# Explore Data Model Population Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate the canonical Explore source tables and wire `/explore` to a complete read model so population, income, density, growth, cached scores, and benchmark confidence are available from the correct tables.

**Architecture:** `public.metros` owns CBSA identity, population, income, ACS demographic fields, and `population_class`. `public.census_cbp_establishments` plus `public.niche_naics_mapping` owns service-aware density and establishment growth. `public.seo_benchmarks` is recomputed from `seo_facts`, `metros`, and CBP as scoring baseline data; it is not the source for per-city population or income. The consumer app should read a complete Explore repository/service output instead of a partial client-side loader that hardcodes density and growth to null.

**Tech Stack:** Python 3.11, Supabase/PostgREST, Postgres SQL migrations/RPCs, Next.js app, Vitest, Pytest, DocGuard.

---

## Current Findings To Preserve

- Live app-facing `public.metros` returned 11 visible rows and sampled rows had `population`, `median_household_income_usd`, and `population_class` as `null`.
- The app publishable key could read `public.metros`, but `public.census_cbp_establishments` and `public.seo_benchmarks` were not visible through PostgREST.
- The local `SUPABASE_SERVICE_ROLE_KEY` in `apps/app/.env.local` was rejected as invalid for the configured project.
- Current `apps/app/src/lib/explore/load-explore-data.ts` reads `metros`, `reports`, and `metro_scores`, limits metros to 100, and explicitly sets `business_density_per_1k` and `establishment_growth_yoy` to `null`.
- There is no `.Codex/databricks-context/` directory in this checkout. Use Supabase migrations and canonical docs as the local schema source of truth unless a schema crawler or remote schema check proves otherwise.

## File Structure

- `scripts/explore/audit_explore_sources.py`: read-only Supabase/PostgREST audit for required tables, columns, row counts, non-null coverage, and app-key visibility.
- `scripts/explore/backfill_metros.py`: service-role backfill/upsert for `public.metros` from `src/data/seed/cbsa_seed.json` plus optional ACS rows.
- `scripts/explore/backfill_cbp_establishments.py`: service-role backfill/upsert for latest and prior CBP establishment rows for mapped target NAICS codes.
- `src/domain/explore/metrics.py`: pure metric formulas for weighted establishments, density per 1k, annualized growth, and population class.
- `src/domain/explore/entities.py`: DTO/dataclass definitions for Explore source rows and summaries.
- `src/clients/explore_repository.py`: Supabase/PostgREST repository that reads the canonical tables and returns normalized row dictionaries.
- `src/domain/services/explore_city_service.py`: orchestration layer that combines repository reads into Explore summaries.
- `apps/app/src/lib/explore/load-explore-data.ts`: temporary consumer loader hardening or API-client wiring to consume complete Explore summaries.
- `.Codex/ACTIVE_WORK.md`: current workstream status and next commands.
- `.Codex/project_context.md`: concise completion context after verified implementation.
- `docs-canonical/ARCHITECTURE.md`, `docs-canonical/DATA-MODEL.md`, `docs-canonical/TEST-SPEC.md`: update only when the implementation changes the canonical architecture/schema/test obligations.

---

### Task 1: Add Read-Only Explore Source Audit

**Files:**
- Create: `scripts/explore/audit_explore_sources.py`
- Create: `tests/scripts/test_audit_explore_sources.py`
- Modify: `.Codex/ACTIVE_WORK.md`

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_audit_explore_sources.py`:

```python
from scripts.explore.audit_explore_sources import (
    REQUIRED_TABLES,
    summarize_table_health,
)


def test_required_tables_include_explore_sources() -> None:
    assert REQUIRED_TABLES == (
        "metros",
        "census_cbp_establishments",
        "niche_naics_mapping",
        "reports",
        "metro_scores",
        "metro_score_v2",
        "seo_facts",
        "seo_benchmarks",
    )


def test_summarize_table_health_flags_sparse_metros() -> None:
    summary = summarize_table_health(
        table="metros",
        row_count=11,
        non_null_counts={
            "population": 0,
            "median_household_income_usd": 0,
            "population_class": 0,
        },
    )

    assert summary["table"] == "metros"
    assert summary["row_count"] == 11
    assert summary["status"] == "fail"
    assert "population" in summary["missing_required_fields"]
    assert "median_household_income_usd" in summary["missing_required_fields"]
    assert "population_class" in summary["missing_required_fields"]


def test_summarize_table_health_allows_optional_fields() -> None:
    summary = summarize_table_health(
        table="metros",
        row_count=120,
        non_null_counts={
            "population": 120,
            "median_household_income_usd": 118,
            "population_class": 120,
            "median_age_years": 0,
        },
    )

    assert summary["status"] == "warn"
    assert summary["missing_required_fields"] == []
    assert summary["missing_optional_fields"] == ["median_age_years"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/scripts/test_audit_explore_sources.py -v
```

Expected: FAIL because `scripts.explore.audit_explore_sources` does not exist.

- [ ] **Step 3: Create the audit module**

Create `scripts/explore/audit_explore_sources.py`:

```python
"""Read-only audit for Explore source table readiness.

This script intentionally does not write data. It checks whether the app-facing
Supabase project has the canonical source tables and enough populated fields for
Explore Cities to render complete rows.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib import parse, request


REQUIRED_TABLES = (
    "metros",
    "census_cbp_establishments",
    "niche_naics_mapping",
    "reports",
    "metro_scores",
    "metro_score_v2",
    "seo_facts",
    "seo_benchmarks",
)

REQUIRED_NON_NULL_FIELDS: dict[str, tuple[str, ...]] = {
    "metros": (
        "population",
        "median_household_income_usd",
        "population_class",
    ),
}

OPTIONAL_NON_NULL_FIELDS: dict[str, tuple[str, ...]] = {
    "metros": (
        "owner_occupancy_rate",
        "median_age_years",
    ),
}


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    key: str


def summarize_table_health(
    *,
    table: str,
    row_count: int,
    non_null_counts: dict[str, int],
) -> dict[str, Any]:
    required = REQUIRED_NON_NULL_FIELDS.get(table, ())
    optional = OPTIONAL_NON_NULL_FIELDS.get(table, ())
    missing_required = [
        field for field in required if non_null_counts.get(field, 0) == 0
    ]
    missing_optional = [
        field for field in optional if non_null_counts.get(field, 0) == 0
    ]

    if row_count == 0 or missing_required:
        status = "fail"
    elif missing_optional:
        status = "warn"
    else:
        status = "pass"

    return {
        "table": table,
        "row_count": row_count,
        "status": status,
        "missing_required_fields": missing_required,
        "missing_optional_fields": missing_optional,
        "non_null_counts": non_null_counts,
    }


def load_env(path: str = "apps/app/.env.local") -> dict[str, str]:
    env: dict[str, str] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key] = value
    return {**env, **os.environ}


def config_from_env(env: dict[str, str], *, service_role: bool) -> SupabaseConfig:
    url = env.get("NEXT_PUBLIC_SUPABASE_URL")
    key_name = (
        "SUPABASE_SERVICE_ROLE_KEY"
        if service_role
        else "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY"
    )
    key = env.get(key_name)
    if not url or not key:
        raise RuntimeError(f"Missing NEXT_PUBLIC_SUPABASE_URL or {key_name}")
    return SupabaseConfig(url=url.rstrip("/"), key=key)


def postgrest_get(config: SupabaseConfig, path: str, *, prefer: str | None = None) -> tuple[int, dict[str, str], str]:
    headers = {
        "apikey": config.key,
        "authorization": f"Bearer {config.key}",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = request.Request(f"{config.url}/rest/v1/{path}", headers=headers)
    try:
        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers), body
    except Exception as exc:
        return 0, {}, json.dumps({"error": str(exc)})


def get_count(config: SupabaseConfig, table: str) -> tuple[int, str | None]:
    status, headers, body = postgrest_get(
        config,
        f"{table}?select=*&limit=1",
        prefer="count=exact",
    )
    content_range = headers.get("Content-Range") or headers.get("content-range")
    if status != 200 or not content_range:
        return 0, body
    try:
        return int(content_range.rsplit("/", 1)[1]), None
    except ValueError:
        return 0, body


def get_non_null_count(config: SupabaseConfig, table: str, field: str) -> int:
    path = (
        f"{table}?select={parse.quote(field)}"
        f"&{parse.quote(field)}=not.is.null&limit=1"
    )
    status, headers, _body = postgrest_get(config, path, prefer="count=exact")
    content_range = headers.get("Content-Range") or headers.get("content-range")
    if status != 200 or not content_range:
        return 0
    try:
        return int(content_range.rsplit("/", 1)[1])
    except ValueError:
        return 0


def audit(config: SupabaseConfig) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for table in REQUIRED_TABLES:
        row_count, error = get_count(config, table)
        fields = REQUIRED_NON_NULL_FIELDS.get(table, ()) + OPTIONAL_NON_NULL_FIELDS.get(table, ())
        non_null_counts = {
            field: get_non_null_count(config, table, field)
            for field in fields
        }
        summary = summarize_table_health(
            table=table,
            row_count=row_count,
            non_null_counts=non_null_counts,
        )
        if error:
            summary["error"] = error
        summaries.append(summary)
    return summaries


def main() -> int:
    env = load_env()
    service_role = "--service-role" in sys.argv
    config = config_from_env(env, service_role=service_role)
    summaries = audit(config)
    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 1 if any(item["status"] == "fail" for item in summaries) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run focused test**

Run:

```bash
pytest tests/scripts/test_audit_explore_sources.py -v
```

Expected: PASS.

- [ ] **Step 5: Run read-only live audit**

Run:

```bash
python scripts/explore/audit_explore_sources.py
python scripts/explore/audit_explore_sources.py --service-role
```

Expected: publishable-key audit reports the same visible app state; service-role audit either succeeds or clearly reports invalid/missing service-role credentials.

- [ ] **Step 6: Update active work**

Add a concise note to `.Codex/ACTIVE_WORK.md` with the command results and current blocker if service role remains invalid.

- [ ] **Step 7: Commit**

Run:

```bash
git add scripts/explore/audit_explore_sources.py tests/scripts/test_audit_explore_sources.py .Codex/ACTIVE_WORK.md
git commit -m "chore: add explore source audit"
```

---

### Task 2: Backfill `public.metros` From Seed Plus ACS Data

**Files:**
- Create: `scripts/explore/backfill_metros.py`
- Create: `tests/scripts/test_backfill_metros.py`
- Modify: `.Codex/ACTIVE_WORK.md`

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_backfill_metros.py`:

```python
from scripts.explore.backfill_metros import (
    build_metro_payload,
    derive_population_class,
)


def test_derive_population_class_boundaries() -> None:
    assert derive_population_class(None) is None
    assert derive_population_class(49_999) == "micro_under_50k"
    assert derive_population_class(50_000) == "small_50_100k"
    assert derive_population_class(100_000) == "medium_100_300k"
    assert derive_population_class(300_000) == "large_300k_1m"
    assert derive_population_class(1_000_000) == "metro_1m_5m"
    assert derive_population_class(5_000_000) == "mega_5m_plus"


def test_build_metro_payload_prefers_acs_values() -> None:
    seed = {
        "cbsa_code": "38060",
        "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
        "state": "AZ",
        "population": 4_946_145,
        "principal_cities": ["Phoenix", "Mesa"],
        "dataforseo_location_codes": [1012873],
    }
    acs = {
        "total_population": 5_015_678,
        "median_household_income": 82_000,
        "total_housing_units": 1_900_000,
        "owner_occupied_units": 1_150_000,
        "median_year_built": 1994,
        "median_age_years": 37,
        "acs_vintage": 2022,
    }

    payload = build_metro_payload(seed, acs)

    assert payload["cbsa_code"] == "38060"
    assert payload["population"] == 5_015_678
    assert payload["median_household_income_usd"] == 82_000
    assert payload["population_class"] == "mega_5m_plus"
    assert payload["owner_occupancy_rate"] == 0.6053
    assert payload["principal_cities"] == ["Phoenix", "Mesa"]
    assert payload["dataforseo_location_codes"] == [1012873]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/scripts/test_backfill_metros.py -v
```

Expected: FAIL because `scripts.explore.backfill_metros` does not exist.

- [ ] **Step 3: Implement payload builder and dry-run CLI**

Create `scripts/explore/backfill_metros.py`:

```python
"""Backfill canonical public.metros rows for Explore Cities."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any
from urllib import request

from src.clients.census.client import CensusClient


SEED_PATH = Path("src/data/seed/cbsa_seed.json")


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


def _rate(owner: Any, total: Any) -> float | None:
    owner_int = _int_or_none(owner)
    total_int = _int_or_none(total)
    if not owner_int or not total_int:
        return None
    return round(owner_int / total_int, 4)


def build_metro_payload(seed: dict[str, Any], acs: dict[str, Any] | None) -> dict[str, Any]:
    acs = acs or {}
    population = _int_or_none(acs.get("total_population")) or _int_or_none(seed.get("population"))
    return {
        "cbsa_code": str(seed["cbsa_code"]),
        "cbsa_name": seed["cbsa_name"],
        "state": seed["state"],
        "cbsa_type": seed.get("cbsa_type"),
        "population": population,
        "principal_cities": seed.get("principal_cities", []),
        "dataforseo_location_codes": seed.get("dataforseo_location_codes", []),
        "households": _int_or_none(acs.get("total_housing_units")),
        "owner_occupied_housing_units": _int_or_none(acs.get("owner_occupied_units")),
        "renter_occupied_housing_units": None,
        "owner_occupancy_rate": _rate(
            acs.get("owner_occupied_units"),
            acs.get("total_housing_units"),
        ),
        "median_household_income_usd": _int_or_none(
            acs.get("median_household_income")
        ),
        "median_year_structure_built": _int_or_none(acs.get("median_year_built")),
        "median_age_years": _int_or_none(acs.get("median_age_years")),
        "acs_vintage": _int_or_none(acs.get("acs_vintage")),
        "population_class": derive_population_class(population),
    }


def load_seed(path: Path = SEED_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


async def load_acs_by_cbsa(year: int) -> dict[str, dict[str, Any]]:
    rows = await CensusClient(year=year).fetch_msa_demographics()
    for row in rows:
        row["acs_vintage"] = year
    return {str(row["cbsa_code"]): row for row in rows}


def postgrest_upsert(url: str, service_key: str, rows: list[dict[str, Any]]) -> None:
    body = json.dumps(rows).encode("utf-8")
    req = request.Request(
        f"{url.rstrip('/')}/rest/v1/metros?on_conflict=cbsa_code",
        data=body,
        method="POST",
        headers={
            "apikey": service_key,
            "authorization": f"Bearer {service_key}",
            "content-type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    with request.urlopen(req, timeout=60) as response:
        if response.status not in (200, 201, 204):
            raise RuntimeError(f"metros upsert failed: HTTP {response.status}")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    seed_rows = load_seed()
    acs_by_cbsa = await load_acs_by_cbsa(args.year)
    payloads = [
        build_metro_payload(row, acs_by_cbsa.get(str(row["cbsa_code"])))
        for row in seed_rows
    ]

    if args.dry_run:
        print(json.dumps(payloads[:5], indent=2))
        print(f"prepared_rows={len(payloads)}")
        return 0

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    postgrest_upsert(url, service_key, payloads)
    print(f"upserted_metros={len(payloads)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/scripts/test_backfill_metros.py -v
```

Expected: PASS.

- [ ] **Step 5: Run dry-run without DB writes**

Run:

```bash
python scripts/explore/backfill_metros.py --dry-run
```

Expected: prints five prepared rows and `prepared_rows=<seed count>`.

- [ ] **Step 6: Apply backfill only after service-role env is valid**

Run:

```bash
set -a
. ./.env
set +a
python scripts/explore/backfill_metros.py
python scripts/explore/audit_explore_sources.py --service-role
```

Expected: `metros` row count is greater than the current 11-row partial state, and non-null `population`, `median_household_income_usd`, and `population_class` counts are greater than zero.

- [ ] **Step 7: Update active work**

Record exact row counts and whether live backfill ran in `.Codex/ACTIVE_WORK.md`. If credentials are invalid, state that no live mutation ran.

- [ ] **Step 8: Commit**

Run:

```bash
git add scripts/explore/backfill_metros.py tests/scripts/test_backfill_metros.py .Codex/ACTIVE_WORK.md
git commit -m "feat: backfill explore metros"
```

---

### Task 3: Add Pure Explore Metric Formulas

**Files:**
- Create: `src/domain/explore/__init__.py`
- Create: `src/domain/explore/metrics.py`
- Create: `tests/unit/test_explore_metrics.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_explore_metrics.py`:

```python
from src.domain.explore.metrics import (
    annualized_growth,
    business_density_per_1k,
    weighted_establishments,
)


def test_weighted_establishments_uses_mapping_weights() -> None:
    cbp_rows = [
        {"naics_code": "238160", "est": 100},
        {"naics_code": "238220", "est": 40},
        {"naics_code": "999999", "est": 999},
    ]
    weights = {"238160": 1.0, "238220": 0.5}

    assert weighted_establishments(cbp_rows, weights) == 120.0


def test_business_density_per_1k_returns_null_without_population() -> None:
    assert business_density_per_1k(100, None) is None
    assert business_density_per_1k(100, 0) is None


def test_business_density_per_1k_scales_for_table_readability() -> None:
    assert business_density_per_1k(250, 100_000) == 2.5


def test_annualized_growth_returns_null_without_prior() -> None:
    assert annualized_growth(latest=120, prior=0, year_span=5) is None
    assert annualized_growth(latest=120, prior=None, year_span=5) is None


def test_annualized_growth_uses_year_span() -> None:
    assert annualized_growth(latest=121, prior=100, year_span=2) == 0.1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/test_explore_metrics.py -v
```

Expected: FAIL because `src.domain.explore.metrics` does not exist.

- [ ] **Step 3: Implement formulas**

Create `src/domain/explore/__init__.py`:

```python
"""Explore Cities domain model and pure metric formulas."""
```

Create `src/domain/explore/metrics.py`:

```python
"""Pure Explore Cities metric formulas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def weighted_establishments(
    cbp_rows: Sequence[Mapping[str, Any]],
    weights_by_naics: Mapping[str, float],
) -> float:
    total = 0.0
    for row in cbp_rows:
        naics_code = str(row.get("naics_code", ""))
        weight = weights_by_naics.get(naics_code)
        if weight is None:
            continue
        est = row.get("est")
        if est is None:
            continue
        total += float(est) * weight
    return round(total, 4)


def business_density_per_1k(
    weighted_establishment_count: float | int | None,
    population: int | None,
) -> float | None:
    if weighted_establishment_count is None or not population:
        return None
    return round(float(weighted_establishment_count) / population * 1_000, 4)


def annualized_growth(
    *,
    latest: float | int | None,
    prior: float | int | None,
    year_span: int,
) -> float | None:
    if latest is None or prior is None or prior <= 0 or year_span <= 0:
        return None
    return round((float(latest) / float(prior)) ** (1 / year_span) - 1, 4)
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/unit/test_explore_metrics.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/domain/explore/__init__.py src/domain/explore/metrics.py tests/unit/test_explore_metrics.py
git commit -m "feat: add explore metric formulas"
```

---

### Task 4: Backfill CBP Establishments For Mapped Services

**Files:**
- Create: `scripts/explore/backfill_cbp_establishments.py`
- Create: `tests/scripts/test_backfill_cbp_establishments.py`
- Modify: `.Codex/ACTIVE_WORK.md`

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_backfill_cbp_establishments.py`:

```python
from scripts.explore.backfill_cbp_establishments import build_cbp_payload


def test_build_cbp_payload_maps_census_fields() -> None:
    row = {
        "cbsa_code": "38060",
        "naics_code": "238160",
        "naics_label": "Roofing contractors",
        "year": 2022,
        "est": "123",
        "n1_4": "80",
        "emp": "900",
        "ap": "12345",
        "empflag": None,
    }

    payload = build_cbp_payload(row)

    assert payload["cbsa_code"] == "38060"
    assert payload["naics_code"] == "238160"
    assert payload["year"] == 2022
    assert payload["est"] == 123
    assert payload["n1_4"] == 80
    assert payload["emp"] == 900
    assert payload["ap"] == 12345
    assert payload["suppressed"] is False


def test_build_cbp_payload_marks_suppressed_establishments() -> None:
    payload = build_cbp_payload(
        {
            "cbsa_code": "38060",
            "naics_code": "238160",
            "year": 2022,
            "est": None,
            "empflag": "D",
        }
    )

    assert payload["est"] is None
    assert payload["suppressed"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/scripts/test_backfill_cbp_establishments.py -v
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement payload builder and safe CLI**

Create `scripts/explore/backfill_cbp_establishments.py` with `build_cbp_payload(row)` and a CLI that:

```python
def build_cbp_payload(row: dict[str, object]) -> dict[str, object]:
    def int_or_none(value: object) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    est = int_or_none(row.get("est"))
    return {
        "cbsa_code": str(row["cbsa_code"]),
        "naics_code": str(row["naics_code"]),
        "naics_label": row.get("naics_label"),
        "year": int(row["year"]),
        "est": est,
        "n1_4": int_or_none(row.get("n1_4")),
        "n5_9": int_or_none(row.get("n5_9")),
        "n10_19": int_or_none(row.get("n10_19")),
        "n20_49": int_or_none(row.get("n20_49")),
        "n50_99": int_or_none(row.get("n50_99")),
        "n100_249": int_or_none(row.get("n100_249")),
        "n250_499": int_or_none(row.get("n250_499")),
        "n500_999": int_or_none(row.get("n500_999")),
        "n1000": int_or_none(row.get("n1000")),
        "emp": int_or_none(row.get("emp")),
        "ap": int_or_none(row.get("ap")),
        "empflag": row.get("empflag"),
        "suppressed": est is None and row.get("empflag") is not None,
    }
```

The CLI may use existing Census CBP client/helpers if available. If no complete CBP fetch client exists, keep the script in dry-run/import-file mode and document the missing fetch integration in `.Codex/ACTIVE_WORK.md` rather than inventing an unverified API contract.

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/scripts/test_backfill_cbp_establishments.py -v
```

Expected: PASS.

- [ ] **Step 5: Run or defer live CBP backfill**

If a verified CBP fetch path exists, run latest and prior year backfills. If not, stop at tested payload/import support and record the exact blocker.

Validation SQL after any live write:

```sql
select year, count(*)
from public.census_cbp_establishments
group by year
order by year desc;

select count(*)
from public.census_cbp_establishments
where est is not null;
```

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/explore/backfill_cbp_establishments.py tests/scripts/test_backfill_cbp_establishments.py .Codex/ACTIVE_WORK.md
git commit -m "feat: prepare explore cbp backfill"
```

---

### Task 5: Recompute Benchmark Readiness

**Files:**
- Create: `scripts/explore/recompute_benchmark_readiness.py`
- Create: `tests/scripts/test_recompute_benchmark_readiness.py`
- Modify: `.Codex/ACTIVE_WORK.md`

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_recompute_benchmark_readiness.py`:

```python
from scripts.explore.recompute_benchmark_readiness import readiness_status


def test_readiness_status_requires_metros_and_facts() -> None:
    result = readiness_status(
        metros_with_population=0,
        seo_fact_count=10,
        cbp_count=10,
    )

    assert result["ready"] is False
    assert "metros_with_population" in result["blocking_checks"]


def test_readiness_status_passes_when_sources_exist() -> None:
    result = readiness_status(
        metros_with_population=60,
        seo_fact_count=500,
        cbp_count=1000,
    )

    assert result["ready"] is True
    assert result["blocking_checks"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/scripts/test_recompute_benchmark_readiness.py -v
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement readiness helper**

Create `scripts/explore/recompute_benchmark_readiness.py`:

```python
"""Preflight checks before recomputing public.seo_benchmarks."""

from __future__ import annotations

from typing import Any


def readiness_status(
    *,
    metros_with_population: int,
    seo_fact_count: int,
    cbp_count: int,
) -> dict[str, Any]:
    blocking: list[str] = []
    if metros_with_population <= 0:
        blocking.append("metros_with_population")
    if seo_fact_count <= 0:
        blocking.append("seo_fact_count")
    if cbp_count <= 0:
        blocking.append("cbp_count")
    return {
        "ready": not blocking,
        "blocking_checks": blocking,
        "metros_with_population": metros_with_population,
        "seo_fact_count": seo_fact_count,
        "cbp_count": cbp_count,
    }
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/scripts/test_recompute_benchmark_readiness.py -v
```

Expected: PASS.

- [ ] **Step 5: Run recompute only when ready**

Run source checks with the audit from Task 1. If ready, run:

```bash
.venv/bin/python -m scripts.benchmarks.recompute_benchmarks 120
```

Expected: `public.seo_benchmarks` has rows by `niche_normalized` and `population_class`.

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/explore/recompute_benchmark_readiness.py tests/scripts/test_recompute_benchmark_readiness.py .Codex/ACTIVE_WORK.md
git commit -m "chore: add benchmark recompute readiness check"
```

---

### Task 6: Add Explore City Service Read Model

**Files:**
- Create: `src/domain/explore/entities.py`
- Create: `src/domain/services/explore_city_service.py`
- Create: `tests/unit/test_explore_city_service.py`

- [ ] **Step 1: Write the failing service test**

Create `tests/unit/test_explore_city_service.py`:

```python
from src.domain.services.explore_city_service import ExploreCityService


class FakeExploreRepository:
    def load_metros(self) -> list[dict]:
        return [
            {
                "cbsa_code": "38060",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "state": "AZ",
                "population": 100_000,
                "population_class": "medium_100_300k",
                "median_household_income_usd": 82_000,
            }
        ]

    def load_scores(self, cbsa_codes: list[str]) -> list[dict]:
        return [
            {
                "cbsa_code": "38060",
                "niche_normalized": "roofing",
                "niche_keyword": "roofing",
                "presentation_score": 81,
                "score_system": "legacy",
            }
        ]

    def load_metric_inputs(self, cbsa_codes: list[str], niche_normalized: str) -> dict:
        return {
            "weights_by_naics": {"238160": 1.0},
            "latest_year": 2022,
            "prior_year": 2021,
            "cbp_rows": {
                ("38060", 2022): [{"naics_code": "238160", "est": 250}],
                ("38060", 2021): [{"naics_code": "238160", "est": 200}],
            },
        }


def test_city_service_combines_demographics_scores_and_metrics() -> None:
    service = ExploreCityService(FakeExploreRepository())

    summaries = service.list_cities(service_filter="roofing")

    assert len(summaries) == 1
    city = summaries[0]
    assert city["cbsa_code"] == "38060"
    assert city["population"] == 100_000
    assert city["median_household_income_usd"] == 82_000
    assert city["business_density_per_1k"] == 2.5
    assert city["establishment_growth_yoy"] == 0.25
    assert city["growth_available"] is True
    assert city["cached_services_count"] == 1
    assert city["best_score"] == 81
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/unit/test_explore_city_service.py -v
```

Expected: FAIL because `ExploreCityService` does not exist.

- [ ] **Step 3: Implement service**

Create `src/domain/explore/entities.py`:

```python
"""Typed dictionaries for Explore Cities read model."""

from __future__ import annotations

from typing import Any, TypedDict


class ExploreCitySummary(TypedDict, total=False):
    cbsa_code: str
    cbsa_name: str
    state: str
    population: int | None
    population_class: str | None
    median_household_income_usd: int | None
    business_density_per_1k: float | None
    establishment_growth_yoy: float | None
    growth_available: bool
    cached_services_count: int
    best_score: int | None
    score_system: str
    cached_scores: list[dict[str, Any]]
```

Create `src/domain/services/explore_city_service.py` using `weighted_establishments`, `business_density_per_1k`, and `annualized_growth` from Task 3.

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/unit/test_explore_metrics.py tests/unit/test_explore_city_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/domain/explore/entities.py src/domain/services/explore_city_service.py tests/unit/test_explore_city_service.py
git commit -m "feat: add explore city read service"
```

---

### Task 7: Wire Consumer Loader To Complete Explore Rows

**Files:**
- Modify: `apps/app/src/lib/explore/types.ts`
- Modify: `apps/app/src/lib/explore/load-explore-data.ts`
- Modify: `apps/app/src/lib/explore/load-explore-data.test.ts`
- Modify: `.Codex/ACTIVE_WORK.md`

- [ ] **Step 1: Add failing Vitest assertion**

Update `apps/app/src/lib/explore/load-explore-data.test.ts` so the primary mapping test expects non-null density and growth when returned by the backend/read model fixture:

```ts
expect(data.cities[0]).toMatchObject({
  cbsa_code: "38060",
  population: 4_900_000,
  median_household_income_usd: 82000,
  business_density_per_1k: 2.5,
  establishment_growth_yoy: 0.1,
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
npm --workspace apps/app test -- load-explore-data
```

Expected: FAIL because the current loader hardcodes density and growth to `null`.

- [ ] **Step 3: Implement minimal loader hardening**

Until a public API route is added, update the loader so it reads complete metric fields if available from the selected source. Remove the hardcoded nulls from `summarizeMetro` and source them from the metro/read-model row:

```ts
business_density_per_1k: asNumber(metro.business_density_per_1k),
establishment_growth_yoy: asNumber(metro.establishment_growth_yoy),
```

If `public.metros` does not have those computed fields, add a separate repository/API task before merging rather than adding duplicate persistent columns to `metros`.

- [ ] **Step 4: Remove client-side universe truncation from the final path**

Do not rely on `METRO_LIMIT = 100` as the final Explore universe. Either remove the limit when backend pagination exists or document in `.Codex/ACTIVE_WORK.md` that the remaining task is to add `GET /api/explore/cities` pagination.

- [ ] **Step 5: Run focused tests**

Run:

```bash
npm --workspace apps/app test -- load-explore-data
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add apps/app/src/lib/explore/types.ts apps/app/src/lib/explore/load-explore-data.ts apps/app/src/lib/explore/load-explore-data.test.ts .Codex/ACTIVE_WORK.md
git commit -m "fix: surface explore demographic metrics"
```

---

### Task 8: Canonical Docs And Final Verification

**Files:**
- Modify: `.Codex/ACTIVE_WORK.md`
- Modify: `.Codex/project_context.md`
- Modify if implementation changed architecture: `docs-canonical/ARCHITECTURE.md`
- Modify if implementation changed schema/DTOs: `docs-canonical/DATA-MODEL.md`
- Modify if tests changed obligations: `docs-canonical/TEST-SPEC.md`

- [ ] **Step 1: Update active work**

Record:

```markdown
## Explore Data Model Population

Status: implemented locally / live backfill blocked / live backfill completed
Verified:
- `pytest ...`
- `npm --workspace apps/app test -- load-explore-data`
- `python scripts/explore/audit_explore_sources.py`
Next:
- exact remaining remote-data or API-route action
```

- [ ] **Step 2: Update project context**

Add a short completed-work note to `.Codex/project_context.md` explaining what was built and whether live Supabase data was populated.

- [ ] **Step 3: Run verification**

Run:

```bash
pytest tests/scripts/test_audit_explore_sources.py tests/scripts/test_backfill_metros.py tests/scripts/test_backfill_cbp_establishments.py tests/scripts/test_recompute_benchmark_readiness.py tests/unit/test_explore_metrics.py tests/unit/test_explore_city_service.py -v
npm --workspace apps/app test -- load-explore-data
git diff --check
npx docguard-cli guard
```

Expected:
- Focused Python tests pass.
- Focused app Vitest passes.
- `git diff --check` passes.
- DocGuard either passes or reports only pre-existing warnings; record exact result.

- [ ] **Step 4: Commit**

Run:

```bash
git add .Codex/ACTIVE_WORK.md .Codex/project_context.md docs-canonical/ARCHITECTURE.md docs-canonical/DATA-MODEL.md docs-canonical/TEST-SPEC.md
git commit -m "docs: record explore data model population"
```

---

## Self-Review Notes

- The plan separates per-city demographics (`metros`) from population-class benchmark baselines (`seo_benchmarks`).
- The plan does not create duplicate `_v2`, `_simplified`, or replacement source tables.
- Live writes are gated behind valid service-role env and explicit command execution.
- If CBP API integration is not already present, Task 4 stops at tested import/payload support and records the missing fetch path instead of inventing unverified Census behavior.
- The final app path must not leave density and growth hardcoded to null.
