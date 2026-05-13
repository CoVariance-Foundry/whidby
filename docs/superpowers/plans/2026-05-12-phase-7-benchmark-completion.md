# Phase 7 Benchmark Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish Phase 7 data-provider readiness, generate the census-grounded benchmark database that V2 scoring reads from, and add a Sonar-compatible slice path for LA plumbing without overstating unsupported residuals.

**Architecture:** Treat migrations `009_metros_and_census.sql` and `010_v2_benchmarks.sql` as the canonical benchmark schema. Keep Phase 7 provider adapters as infrastructure inputs, but do not apply duplicate provider-reference tables until they are reconciled with the canonical `metros`, `census_cbp_establishments`, `seo_facts`, and `seo_benchmarks` path. Add a repeatable benchmark recompute function plus a small runner/audit script so staging can be validated before production. Sonar is layered on top as a separate `sonar` schema that can consume existing ACS, CBP, NAICS, and DFS facts for a slice-lite run, then expand to the full residual spec only after geo crosswalk, NES, BDS, and trends inputs exist.

**Tech Stack:** Python 3.11+, pytest, ruff, Supabase Postgres, Supabase MCP/SQL, DataForSEO, Anthropic, Census ACS/CBP, BLS, Google Trends/DataForSEO Trends, scikit-learn or NumPy-based ridge regression for Sonar residuals once the full peer matrix is loaded.

---

## Execution Status - 2026-05-12

Completed in this implementation pass:

- Tasks 1-7: local provider environment repaired, benchmark Supabase env separation added, provider migration 011 reconciled/applied to staging, local-pack review fields added, DFS enrichment helper added, benchmark recompute RPC added/applied, and recompute runner verified against staging.
- Tasks 9-10: `run_pilot.py` now supports `--sample-mode {pilot,full}`, `--full-sample`, `--limit-pairs`, repeatable `--niche`, and repeatable `--population-class`; invalid filters fail before credential checks; V2 scoring boundary is documented.
- Task 11: Sonar slice-lite schema, service-role RPC, builder, and tests are implemented. Staging contains `238220__msa__31080__2023` with status `partial_sources`, latest score `0.8193`, one run, peer count `289`, and score version `sonar-lite-0.1`.
- Task 12: full Sonar residual closure gates are documented; no full-residual code was added because required source layers are not loaded.

Deferred or blocked:

- Task 8 paid DataForSEO rerun was not executed in this pass. Existing `seo_facts.top3_review_count_min` values remain mostly/null for current facts until a paid collection rerun is approved.
- Task 9 production-grade coverage remains below target after recompute: 43 insufficient cells, 12 low cells, 0 medium/high cells. Full-sample paid collection is required to reach `sample_size_metros >= 8`.
- Task 13 production promotion was not executed. Production must wait for explicit approval plus a staging health review.
- Task 14 final validation is the current closeout step.

Sampling prune update:

- Paid benchmark collection now distinguishes census-available metros from SEO-benchmark-eligible metros. Default paid runs include only metros with native DataForSEO codes in `mega_5m_plus`, `metro_1m_5m`, `large_300k_1m`, or validated `medium_100_300k` classes.
- Default paid runs exclude `small_50_100k`, `micro_under_50k`, empty-code metros, and state-borrowed DFS codes. Use `--include-low-signal` only for explicit diagnostics.
- `--preflight-only` validates keyword-volume coverage without SERP pulls or Supabase writes. The current full filtered launch sample is 60 metros: 9 mega, 37 metro, 12 large, and 2 medium.
- Live filtered preflight on 2026-05-12 covered 10 pilot pairs across plumber and concrete contractor with 10/10 success, zero writes, and one repeated invalid New York keyword-volume code. `metros_sampled.json` now keeps New York SERP codes intact while using `keyword_volume_location_codes=[1023191, 1022703]` for volume.
- Concurrent same-niche pilot pairs now share one in-flight keyword expansion to avoid repeated paid Anthropic and DFS suggestion calls.
- Small and micro metros remain census-only until a cheaper or better local keyword-volume source exists; they should not block Phase 7 benchmark completion.

---

## Verified Current State

As of 2026-05-12:

- Supabase `whidby-staging` has migrations `metros_and_census` and `v2_benchmarks` applied.
- Supabase `whidby` production does not yet have the census/benchmark tables.
- Staging row counts:
  - `metros`: 935
  - `census_cbp_establishments`: 23,558
  - `census_target_naics`: 45
  - `niche_naics_mapping`: 144
  - `seo_facts`: 2,694
  - `seo_benchmarks`: 0
  - `metro_score_v2`: 0
- Staging `seo_facts` covers 10 niches, 19 metros, snapshots from 2026-04-26 to 2026-04-27.
- `seo_facts.top3_review_count_min` is empty for all facts, so local difficulty benchmarks are not complete.
- Sonar spec review found that LA MSA plumbing has enough data for a slice-lite record:
  - `metros` has CBSA `31080` with population `13,012,469`, households `4,464,908`, median household income `$93,525`, owner occupancy `0.4857`, ACS vintage `2023`, and DataForSEO location codes.
  - `census_cbp_establishments` has unsuppressed `31080 × 238220 × 2023` with `3,793` establishments, `39,381` employees, payroll, and establishment size buckets.
  - The CBP peer set for `238220` has `289` MSAs with population over `100,000`, `ESTAB > 50`, and no suppression, enough for the spec's residual peer-size gate.
  - `seo_facts` has `38` LA plumber keyword rows with volume and CPC, total monthly volume `114,820`, weighted CPC about `$35.27`, and local pack present on all rows.
- Sonar full spec is not implementable from current loaded data alone because staging does not have `geo.canonical_geo`, `geo.crosswalk`, `sonar.cells`, `sonar.cell_runs`, `sonar.scoring_weights`, NES, BDS, HUD FMR, NAICS concordance, CBP 2018-2022 history, or stored trends slope/seasonality.
- Local provider tests fail because `.venv` has no `numpy`, while `src/clients/census/adapter.py` imports it.
- `supabase/migrations/011_data_provider_tables.sql` is present locally but is not applied in staging. It creates `cities` and `business_patterns`, which duplicate the already-applied benchmark path. Do not apply it as-is.

## File Map

| Action | File | Responsibility |
|---|---|---|
| Verify/possibly modify | `pyproject.toml` | Ensure `numpy` is declared and installable in the repo venv |
| Modify | `scripts/benchmarks/run_pilot.py` | Use benchmark-specific Supabase env vars, capture local-pack review floors, support staged collection runs |
| Modify | `scripts/benchmarks/smoke_test.py` | Use the same benchmark env vars and disable mismatched persistent cache behavior |
| Create | `scripts/benchmarks/enrich_dfs_codes.py` | Enrich sampled metros with DFS location codes or explicit fallback metadata |
| Create | `scripts/benchmarks/recompute_benchmarks.py` | Invoke/audit benchmark recompute from the command line |
| Create | `supabase/migrations/012_recompute_seo_benchmarks.sql` | Add repeatable SQL function for rebuilding `seo_benchmarks` from `seo_facts` |
| Create | `supabase/migrations/013_sonar_slice_lite.sql` | Add `sonar.cells`, `sonar.cell_runs`, and `sonar.scoring_weights` for Sonar slice persistence |
| Create | `scripts/sonar/build_slice_lite.py` | Build the LA plumbing `CellRecord` from existing ACS, CBP, NAICS, and DFS benchmark tables |
| Create | `tests/scripts/test_sonar_slice_metrics.py` | Verify metric-block construction and missing-source quality flags without network |
| Future create | `src/sonar/residuals.py` | Fit ridge residual models after the complete Sonar peer matrix exists |
| Modify | `supabase/migrations/011_data_provider_tables.sql` | Reconcile or neutralize duplicate provider-reference tables before any apply |
| Modify | `docs/algo_spec_v2.md` | Replace pseudo-SQL with the actual recompute contract and known limitations |
| Modify | `docs-canonical/DATA-MODEL.md` | Document benchmark entities and source-of-truth table names |
| Modify | `docs-canonical/ENVIRONMENT.md` | Document benchmark env vars and staging-first workflow |

---

## Task 1: Repair Local Phase 7 Test Environment

**Files:**
- Verify: `pyproject.toml`
- Test: `tests/clients/census/test_census_adapter.py`
- Test: `tests/clients/bls/test_bls_adapter.py`
- Test: `tests/clients/trends/test_trends_adapter.py`
- Test: `tests/clients/test_composite_providers.py`

- [ ] **Step 1: Verify `numpy` is declared**

Run:

```bash
rg -n '"numpy"' pyproject.toml
```

Expected: one dependency entry for `numpy`.

- [ ] **Step 2: Install repo dependencies into `.venv`**

Run:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

Expected: install completes, including `numpy`.

- [ ] **Step 3: Verify Python and numpy inside `.venv`**

Run:

```bash
.venv/bin/python -c "import sys, numpy; print(sys.version.split()[0]); print(numpy.__version__)"
```

Expected: Python 3.11+ and a printed numpy version.

- [ ] **Step 4: Run provider tests**

Run:

```bash
.venv/bin/python -m pytest tests/clients/census/ tests/clients/bls/ tests/clients/trends/ tests/clients/test_composite_providers.py -v
```

Expected: all provider tests pass. If they fail after dependency install, fix only the provider code under `src/clients/{census,bls,trends}/` and rerun this command.

- [ ] **Step 5: Run architecture import check**

Run:

```bash
.venv/bin/python scripts/check_domain_imports.py
```

Expected: `Domain layer is clean`.

- [ ] **Step 6: Commit**

If dependency files changed:

```bash
git add pyproject.toml package-lock.json
git commit -m "chore: restore phase 7 provider test environment"
```

If no files changed, do not commit.

---

## Task 2: Fix Benchmark Supabase Environment Separation

**Files:**
- Modify: `scripts/benchmarks/run_pilot.py`
- Modify: `scripts/benchmarks/smoke_test.py`
- Modify: `docs-canonical/ENVIRONMENT.md`

- [ ] **Step 1: Update `run_pilot.py` credential loading**

Change the Supabase key loading near the top of `scripts/benchmarks/run_pilot.py` to:

```python
SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",  # whidby-staging
)
SUPABASE_KEY = (
    os.environ.get("BENCHMARK_SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)
```

- [ ] **Step 2: Keep DataForSEO persistent cache disabled for benchmark runs**

Keep this exact client construction in `main()`:

```python
dfs = DataForSEOClient(login=DFS_LOGIN, password=DFS_PASS, persistent_cache=False)
```

Expected: no benchmark run uses the app's `NEXT_PUBLIC_SUPABASE_URL` accidentally.

- [ ] **Step 3: Update `smoke_test.py` to use benchmark key**

Change the smoke-test key loading to:

```python
SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",
)
SUPABASE_KEY = (
    os.environ.get("BENCHMARK_SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)
```

Also construct the DFS client as:

```python
dfs = DataForSEOClient(
    login=os.environ["DATAFORSEO_LOGIN"],
    password=os.environ["DATAFORSEO_PASSWORD"],
    persistent_cache=False,
)
```

- [ ] **Step 4: Document benchmark env vars**

Add this table to `docs-canonical/ENVIRONMENT.md` under the Supabase/staging section:

```markdown
### Benchmark Runner Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `BENCHMARK_SUPABASE_URL` | Recommended | Supabase project URL for benchmark writes. Defaults to `whidby-staging`. |
| `BENCHMARK_SUPABASE_KEY` | Recommended | Service-role key for the benchmark Supabase project. Falls back to `SUPABASE_SERVICE_ROLE_KEY`. |
```

- [ ] **Step 5: Run smoke import check**

Run:

```bash
.venv/bin/python -c "from scripts.benchmarks.run_pilot import SUPABASE_URL, SUPABASE_KEY; print(SUPABASE_URL); print(bool(SUPABASE_KEY))"
```

Expected: staging URL and `True`. Do not print the key.

- [ ] **Step 6: Commit**

```bash
git add scripts/benchmarks/run_pilot.py scripts/benchmarks/smoke_test.py docs-canonical/ENVIRONMENT.md
git commit -m "fix: isolate benchmark Supabase configuration"
```

---

## Task 3: Reconcile the Unapplied Phase 7 Provider Migration

**Files:**
- Modify: `supabase/migrations/011_data_provider_tables.sql`
- Modify: `docs-canonical/DATA-MODEL.md`

- [ ] **Step 1: Confirm staging does not have 011 tables**

Run via Supabase SQL against `whidby-staging`:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('cities', 'business_patterns', 'service_acv_estimates')
order by table_name;
```

Expected: no rows before this task starts.

- [ ] **Step 2: Replace duplicate table definitions**

Rewrite `supabase/migrations/011_data_provider_tables.sql` so it does not create duplicate `cities` or `business_patterns` tables. The canonical equivalents are:

- `public.metros` for city/metro demographics
- `public.census_cbp_establishments` for business patterns

Use this migration body:

```sql
-- 011_data_provider_tables.sql
--
-- Phase 7 provider persistence that does not duplicate the benchmark schema.
-- Canonical demographics live in public.metros.
-- Canonical CBP business density lives in public.census_cbp_establishments.

CREATE TABLE IF NOT EXISTS public.service_acv_estimates (
    naics_code TEXT NOT NULL REFERENCES public.census_target_naics(naics_code),
    cbsa_code TEXT NOT NULL DEFAULT 'national',
    mean_hourly_wage NUMERIC,
    avg_job_hours NUMERIC,
    overhead_multiplier NUMERIC NOT NULL DEFAULT 2.0,
    acv_estimate NUMERIC,
    year INTEGER,
    source TEXT NOT NULL DEFAULT 'bls'
        CHECK (source IN ('bls', 'manual', 'derived')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (naics_code, cbsa_code)
);

CREATE INDEX IF NOT EXISTS idx_service_acv_cbsa
    ON public.service_acv_estimates(cbsa_code);

ALTER TABLE public.service_acv_estimates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_acv_read_all ON public.service_acv_estimates;
CREATE POLICY service_acv_read_all
    ON public.service_acv_estimates
    FOR SELECT
    USING (true);

COMMENT ON TABLE public.service_acv_estimates IS
    'Phase 7 BLS-derived service annual contract value estimates keyed by NAICS and CBSA. Demographics and CBP density remain in metros/census_cbp_establishments.';
```

- [ ] **Step 3: Update data model docs**

In `docs-canonical/DATA-MODEL.md`, add concise rows for:

```markdown
| MetroBenchmarkSource | Supabase `metros` table | cbsa_code | ACS-backed metro demographics and population class |
| CBPEstablishment | Supabase `census_cbp_establishments` table | cbsa_code + naics_code + year | Census CBP establishment density for monetization benchmarks |
| SeoFact | Supabase `seo_facts` table | niche + cbsa + keyword + date | Keyword-grain observations used to build benchmarks |
| SeoBenchmark | Supabase `seo_benchmarks` table | niche + population_class | V2 benchmark cell used by scoring |
| ServiceACVEstimate | Supabase `service_acv_estimates` table | naics_code + cbsa_code | BLS-derived ACV estimates |
```

- [ ] **Step 4: Apply only after review**

Do not apply `011_data_provider_tables.sql` until Task 1 and Task 2 are green. When applying, use Supabase migration tooling against staging first.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/011_data_provider_tables.sql docs-canonical/DATA-MODEL.md
git commit -m "fix: align phase 7 provider tables with benchmark schema"
```

---

## Task 4: Capture Local-Pack Review Floors in `seo_facts`

**Files:**
- Modify: `scripts/benchmarks/run_pilot.py`
- Test: create `tests/scripts/test_benchmark_serp_parsing.py`

- [ ] **Step 1: Add parser tests for review floor fields**

Create `tests/scripts/test_benchmark_serp_parsing.py`:

```python
from scripts.benchmarks.run_pilot import parse_serp_items


def test_parse_serp_items_extracts_top3_review_floor_and_rating():
    serp = [{
        "items": [{
            "type": "local_pack",
            "rank_absolute": 1,
            "items": [
                {"title": "A", "rating": {"value": 4.8, "votes_count": 120}},
                {"title": "B", "rating": {"value": 4.5, "votes_count": 80}},
                {"title": "C", "rating": {"value": 4.1, "votes_count": 40}},
            ],
        }]
    }]

    parsed = parse_serp_items(serp)

    assert parsed["local_pack_present"] is True
    assert parsed["top3_review_count_min"] == 40
    assert parsed["top3_review_count_avg"] == 80
    assert parsed["top3_rating_avg"] == 4.47
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/scripts/test_benchmark_serp_parsing.py -v
```

Expected: fail because the new keys are absent.

- [ ] **Step 3: Update `parse_serp_items` defaults**

Add these defaults to `flags` in `scripts/benchmarks/run_pilot.py`:

```python
"top3_review_count_min": None,
"top3_review_count_avg": None,
"top3_rating_avg": None,
```

- [ ] **Step 4: Compute top-3 local-pack metrics**

After collecting `top_local_pack_items`, add:

```python
    review_counts = [
        item["rating_count"]
        for item in flags["top_local_pack_items"][:3]
        if isinstance(item.get("rating_count"), (int, float))
    ]
    ratings = [
        item["rating"]
        for item in flags["top_local_pack_items"][:3]
        if isinstance(item.get("rating"), (int, float))
    ]
    if review_counts:
        flags["top3_review_count_min"] = int(min(review_counts))
        flags["top3_review_count_avg"] = int(round(sum(review_counts) / len(review_counts)))
    if ratings:
        flags["top3_rating_avg"] = round(sum(ratings) / len(ratings), 2)
```

- [ ] **Step 5: Persist review fields into `seo_facts` rows**

Add these fields to each `rows.append({...})` payload:

```python
"top3_review_count_min": row_features.get("top3_review_count_min"),
"top3_review_count_avg": row_features.get("top3_review_count_avg"),
"top3_rating_avg": row_features.get("top3_rating_avg"),
```

Keep `top3_review_velocity_avg` null for now. Do not invent review velocity without historical review timestamps.

- [ ] **Step 6: Run parser tests**

Run:

```bash
.venv/bin/python -m pytest tests/scripts/test_benchmark_serp_parsing.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/benchmarks/run_pilot.py tests/scripts/test_benchmark_serp_parsing.py
git commit -m "feat: capture local pack review floors for benchmarks"
```

---

## Task 5: Add DFS Location Code Enrichment for Benchmark Sampling

**Files:**
- Create: `scripts/benchmarks/enrich_dfs_codes.py`
- Modify: `scripts/benchmarks/metros_sampled.json`

- [ ] **Step 1: Create enrichment script**

Create `scripts/benchmarks/enrich_dfs_codes.py`:

```python
"""Enrich benchmark sample metros with DataForSEO location codes.

Usage:
  .venv/bin/python -m scripts.benchmarks.enrich_dfs_codes --dry-run
  .venv/bin/python -m scripts.benchmarks.enrich_dfs_codes
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.clients.dataforseo import DataForSEOClient  # noqa: E402

METROS_PATH = Path(__file__).parent / "metros_sampled.json"
CITY_TYPES = {"city", "city council", "municipality", "town"}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def candidate_cities(cbsa_name: str) -> list[str]:
    prefix = cbsa_name.split(",")[0]
    return [part.strip() for part in re.split(r"[-–]", prefix) if part.strip()]


def build_index(locations: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for loc in locations:
        if str(loc.get("location_type", "")).lower() not in CITY_TYPES:
            continue
        name = str(loc.get("location_name", "")).split(",")[0]
        key = normalize(name)
        if key:
            index.setdefault(key, []).append(loc)
    return index


def resolve_codes(metro: dict, index: dict[str, list[dict]]) -> list[int]:
    state = str(metro.get("state", "")).upper()
    codes: list[int] = []
    for city in candidate_cities(metro["cbsa_name"]):
        for loc in index.get(normalize(city), []):
            if str(loc.get("country_iso_code", "")).upper() != "US":
                continue
            loc_name = str(loc.get("location_name", "")).upper()
            if state and state not in loc_name:
                continue
            code = loc.get("location_code")
            if isinstance(code, int) and code not in codes:
                codes.append(code)
    return codes


async def main() -> None:
    dry_run = "--dry-run" in sys.argv
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise SystemExit("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are required")

    metros = json.loads(METROS_PATH.read_text())
    client = DataForSEOClient(login=login, password=password, persistent_cache=False)
    locations = await client.google_locations()
    index = build_index(locations.data or [])

    changed = 0
    for metro in metros:
        if metro.get("dataforseo_location_codes"):
            continue
        codes = resolve_codes(metro, index)
        if codes:
            metro["dataforseo_location_codes"] = codes
            metro["_dfs_source"] = "enriched"
            changed += 1

    print(f"enriched={changed}")
    if not dry_run:
        METROS_PATH.write_text(json.dumps(metros, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify the DataForSEO client method exists**

Run:

```bash
rg -n "google_locations|locations" src/clients/dataforseo src/research_agent/places.py
```

If no method exists on `DataForSEOClient`, reuse the location-fetching helper from `src/research_agent/places.py` instead of inventing a second HTTP path.

- [ ] **Step 3: Dry-run enrichment**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.enrich_dfs_codes --dry-run
```

Expected: prints `enriched=<number>` and does not modify `metros_sampled.json`.

- [ ] **Step 4: Apply enrichment**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.enrich_dfs_codes
```

Expected: `scripts/benchmarks/metros_sampled.json` changes only by filling empty `dataforseo_location_codes` and `_dfs_source`.

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmarks/enrich_dfs_codes.py scripts/benchmarks/metros_sampled.json
git commit -m "feat: enrich benchmark sample with DFS location codes"
```

---

## Task 6: Add Repeatable Benchmark Recompute Function

**Files:**
- Create: `supabase/migrations/012_recompute_seo_benchmarks.sql`
- Modify: `docs/algo_spec_v2.md`

- [ ] **Step 1: Create recompute migration**

Create `supabase/migrations/012_recompute_seo_benchmarks.sql`:

```sql
-- 012_recompute_seo_benchmarks.sql
--
-- Rebuilds public.seo_benchmarks from public.seo_facts.

CREATE OR REPLACE FUNCTION public.recompute_seo_benchmarks(p_window_days INTEGER DEFAULT 90)
RETURNS TABLE (
    cells_recomputed INTEGER,
    fact_window_start DATE,
    fact_window_end DATE
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    v_start DATE := CURRENT_DATE - p_window_days;
    v_end DATE;
    v_cells INTEGER;
BEGIN
    SELECT max(snapshot_date) INTO v_end
    FROM public.seo_facts
    WHERE snapshot_date >= v_start;

    DELETE FROM public.seo_benchmarks
    WHERE fact_window_start >= v_start OR fact_window_start IS NULL;

    WITH primary_naics AS (
        SELECT DISTINCT ON (niche_normalized)
            niche_normalized,
            naics_code
        FROM public.niche_naics_mapping
        WHERE is_primary = TRUE
        ORDER BY niche_normalized, confidence DESC, weight DESC, naics_code
    ),
    fact_rollup AS (
        SELECT
            f.niche_normalized,
            f.cbsa_code,
            m.population_class,
            m.population,
            sum(coalesce(f.search_volume_monthly, 0)) FILTER (
                WHERE f.intent IN ('transactional', 'commercial')
            ) AS total_volume,
            avg(f.cpc_usd) FILTER (WHERE f.cpc_usd IS NOT NULL) AS avg_cpc,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY f.top3_review_count_min)
                FILTER (WHERE f.local_pack_present IS TRUE AND f.top3_review_count_min IS NOT NULL)
                AS median_review_floor,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY f.top3_review_velocity_avg)
                FILTER (WHERE f.local_pack_present IS TRUE AND f.top3_review_velocity_avg IS NOT NULL)
                AS median_review_velocity,
            avg(CASE WHEN f.local_pack_present IS TRUE THEN 1.0 ELSE 0.0 END) AS local_pack_rate,
            avg(f.aggregator_count_top10) FILTER (WHERE f.aggregator_count_top10 IS NOT NULL) AS avg_aggregators,
            avg(f.local_biz_count_top10) FILTER (WHERE f.local_biz_count_top10 IS NOT NULL) AS avg_local_biz,
            avg(CASE WHEN f.lsa_present IS TRUE THEN 1.0 ELSE 0.0 END) AS lsa_rate,
            avg(CASE WHEN f.ads_present IS TRUE THEN 1.0 ELSE 0.0 END) AS ads_rate,
            avg(CASE WHEN f.aio_present IS TRUE THEN 1.0 ELSE 0.0 END) AS aio_rate,
            count(*) AS observation_count,
            min(f.snapshot_date) AS first_snapshot,
            max(f.snapshot_date) AS last_snapshot
        FROM public.seo_facts f
        JOIN public.metros m USING (cbsa_code)
        WHERE f.snapshot_date >= v_start
          AND m.population_class IS NOT NULL
          AND m.population IS NOT NULL
        GROUP BY f.niche_normalized, f.cbsa_code, m.population_class, m.population
    ),
    cbp_density AS (
        SELECT
            fr.niche_normalized,
            fr.cbsa_code,
            sum(coalesce(c.est, 0) * coalesce(nm.weight, 1.0)) AS weighted_establishments
        FROM fact_rollup fr
        LEFT JOIN public.niche_naics_mapping nm
            ON nm.niche_normalized = fr.niche_normalized
        LEFT JOIN public.census_cbp_establishments c
            ON c.cbsa_code = fr.cbsa_code
           AND c.naics_code = nm.naics_code
           AND c.year = (
                SELECT max(year)
                FROM public.census_cbp_establishments
           )
        GROUP BY fr.niche_normalized, fr.cbsa_code
    ),
    rollup_with_cbp AS (
        SELECT
            fr.*,
            CASE
                WHEN fr.population > 0
                THEN (coalesce(cd.weighted_establishments, 0)::numeric / fr.population) * 100000
                ELSE NULL
            END AS establishments_per_100k
        FROM fact_rollup fr
        LEFT JOIN cbp_density cd
            ON cd.niche_normalized = fr.niche_normalized
           AND cd.cbsa_code = fr.cbsa_code
    ),
    cell_stats AS (
        SELECT
            r.niche_normalized,
            pn.naics_code,
            r.population_class,
            percentile_cont(0.25) WITHIN GROUP (
                ORDER BY (r.total_volume::numeric / nullif(r.population, 0))
            ) AS p25_total_volume_per_capita,
            percentile_cont(0.50) WITHIN GROUP (
                ORDER BY (r.total_volume::numeric / nullif(r.population, 0))
            ) AS median_total_volume_per_capita,
            percentile_cont(0.75) WITHIN GROUP (
                ORDER BY (r.total_volume::numeric / nullif(r.population, 0))
            ) AS p75_total_volume_per_capita,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY r.avg_cpc) AS p25_avg_cpc,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.avg_cpc) AS median_avg_cpc,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY r.avg_cpc) AS p75_avg_cpc,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.median_review_floor)
                FILTER (WHERE r.median_review_floor IS NOT NULL) AS median_top3_review_count_min,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.median_review_velocity)
                FILTER (WHERE r.median_review_velocity IS NOT NULL) AS median_top3_review_velocity,
            avg(r.local_pack_rate) AS pct_with_local_pack,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.avg_aggregators) AS median_aggregator_count,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.avg_local_biz) AS median_local_biz_count,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.establishments_per_100k)
                AS median_establishments_per_100k,
            avg(r.lsa_rate) AS median_lsa_present_rate,
            avg(r.ads_rate) AS median_ads_present_rate,
            avg(r.aio_rate) AS median_aio_trigger_rate,
            count(*) AS sample_size_metros,
            sum(r.observation_count)::integer AS sample_size_observations,
            min(r.first_snapshot) AS fact_window_start,
            max(r.last_snapshot) AS fact_window_end
        FROM rollup_with_cbp r
        LEFT JOIN primary_naics pn
            ON pn.niche_normalized = r.niche_normalized
        GROUP BY r.niche_normalized, pn.naics_code, r.population_class
    )
    INSERT INTO public.seo_benchmarks (
        niche_normalized,
        naics_code,
        population_class,
        p25_total_volume_per_capita,
        median_total_volume_per_capita,
        p75_total_volume_per_capita,
        p25_avg_cpc,
        median_avg_cpc,
        p75_avg_cpc,
        median_top3_review_count_min,
        median_top3_review_velocity,
        pct_with_local_pack,
        median_aggregator_count,
        median_local_biz_count,
        median_establishments_per_100k,
        median_lsa_present_rate,
        median_ads_present_rate,
        median_aio_trigger_rate,
        sample_size_metros,
        sample_size_observations,
        confidence_label,
        last_recomputed_at,
        fact_window_start,
        fact_window_end
    )
    SELECT
        niche_normalized,
        naics_code,
        population_class,
        p25_total_volume_per_capita,
        median_total_volume_per_capita,
        p75_total_volume_per_capita,
        p25_avg_cpc,
        median_avg_cpc,
        p75_avg_cpc,
        median_top3_review_count_min,
        median_top3_review_velocity,
        pct_with_local_pack,
        median_aggregator_count,
        median_local_biz_count,
        median_establishments_per_100k,
        median_lsa_present_rate,
        median_ads_present_rate,
        median_aio_trigger_rate,
        sample_size_metros,
        sample_size_observations,
        CASE
            WHEN sample_size_metros >= 20 THEN 'high'
            WHEN sample_size_metros >= 8 THEN 'medium'
            WHEN sample_size_metros >= 3 THEN 'low'
            ELSE 'insufficient'
        END AS confidence_label,
        now(),
        fact_window_start,
        fact_window_end
    FROM cell_stats
    ON CONFLICT (niche_normalized, population_class) DO UPDATE SET
        naics_code = EXCLUDED.naics_code,
        p25_total_volume_per_capita = EXCLUDED.p25_total_volume_per_capita,
        median_total_volume_per_capita = EXCLUDED.median_total_volume_per_capita,
        p75_total_volume_per_capita = EXCLUDED.p75_total_volume_per_capita,
        p25_avg_cpc = EXCLUDED.p25_avg_cpc,
        median_avg_cpc = EXCLUDED.median_avg_cpc,
        p75_avg_cpc = EXCLUDED.p75_avg_cpc,
        median_top3_review_count_min = EXCLUDED.median_top3_review_count_min,
        median_top3_review_velocity = EXCLUDED.median_top3_review_velocity,
        pct_with_local_pack = EXCLUDED.pct_with_local_pack,
        median_aggregator_count = EXCLUDED.median_aggregator_count,
        median_local_biz_count = EXCLUDED.median_local_biz_count,
        median_establishments_per_100k = EXCLUDED.median_establishments_per_100k,
        median_lsa_present_rate = EXCLUDED.median_lsa_present_rate,
        median_ads_present_rate = EXCLUDED.median_ads_present_rate,
        median_aio_trigger_rate = EXCLUDED.median_aio_trigger_rate,
        sample_size_metros = EXCLUDED.sample_size_metros,
        sample_size_observations = EXCLUDED.sample_size_observations,
        confidence_label = EXCLUDED.confidence_label,
        last_recomputed_at = now(),
        fact_window_start = EXCLUDED.fact_window_start,
        fact_window_end = EXCLUDED.fact_window_end;

    GET DIAGNOSTICS v_cells = ROW_COUNT;

    RETURN QUERY SELECT v_cells, v_start, v_end;
END;
$$;

REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM anon;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.recompute_seo_benchmarks(INTEGER) TO service_role;
```

- [ ] **Step 2: Apply to staging**

Use Supabase migration tooling against `whidby-staging` with migration name `recompute_seo_benchmarks`.

- [ ] **Step 3: Run recompute on staging**

Run via Supabase SQL:

```sql
select * from public.recompute_seo_benchmarks(120);
```

Expected: `cells_recomputed` greater than 0 once `seo_facts` has data.

- [ ] **Step 4: Audit generated cells**

Run:

```sql
select
    niche_normalized,
    population_class,
    sample_size_metros,
    sample_size_observations,
    confidence_label,
    median_total_volume_per_capita,
    median_establishments_per_100k,
    median_top3_review_count_min
from public.seo_benchmarks
order by niche_normalized, population_class;
```

Expected: rows exist. Cells without review floor remain acceptable only until Task 4 data is rerun.

- [ ] **Step 5: Update docs**

In `docs/algo_spec_v2.md`, replace the pseudo `ON CONFLICT ...` aggregation section with a pointer to:

```markdown
The executable recompute contract is `public.recompute_seo_benchmarks(p_window_days integer)` from `supabase/migrations/012_recompute_seo_benchmarks.sql`.
```

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/012_recompute_seo_benchmarks.sql docs/algo_spec_v2.md
git commit -m "feat: add seo benchmark recompute function"
```

---

## Task 7: Add Benchmark Recompute Runner and Audit Command

**Files:**
- Create: `scripts/benchmarks/recompute_benchmarks.py`
- Modify: `docs-canonical/ENVIRONMENT.md`

- [ ] **Step 1: Create runner script**

Create `scripts/benchmarks/recompute_benchmarks.py`:

```python
"""Run and audit seo_benchmarks recomputation.

This script uses Supabase PostgREST RPC, so it requires service-role credentials.
"""
from __future__ import annotations

import json
import os
import sys
from urllib import error as urlerror
from urllib import request as urlreq


SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",
)
SUPABASE_KEY = (
    os.environ.get("BENCHMARK_SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)


def rpc(function_name: str, payload: dict) -> tuple[int, str]:
    if not SUPABASE_KEY:
        raise RuntimeError("BENCHMARK_SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY is required")

    req = urlreq.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/{function_name}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlreq.urlopen(req, timeout=120) as response:
            return response.status, response.read().decode()
    except urlerror.HTTPError as exc:
        return exc.code, exc.read().decode()[:1000]


def main() -> None:
    window_days = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    status, body = rpc("recompute_seo_benchmarks", {"p_window_days": window_days})
    print(f"status={status}")
    print(body)
    if status >= 300:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the runner against staging**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.recompute_benchmarks 120
```

Expected: `status=200` and JSON containing `cells_recomputed`.

- [ ] **Step 3: Document the command**

Add to `docs-canonical/ENVIRONMENT.md`:

```markdown
| Command | Purpose |
|---------|---------|
| `.venv/bin/python -m scripts.benchmarks.recompute_benchmarks 120` | Rebuild staging `seo_benchmarks` from recent `seo_facts` |
```

- [ ] **Step 4: Commit**

```bash
git add scripts/benchmarks/recompute_benchmarks.py docs-canonical/ENVIRONMENT.md
git commit -m "feat: add benchmark recompute runner"
```

---

## Task 8: Rerun Benchmark Collection With Review Fields

**Files:**
- Modify: `scripts/benchmarks/run_pilot.py`
- Data output: Supabase `whidby-staging.public.seo_facts`

- [ ] **Step 1: Run one-pair smoke test**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.smoke_test
```

Expected:

- facts inserted or updated
- no Supabase 401
- no DataForSEO cache 401
- Supabase readback shows facts for `concrete contractor` x Phoenix

- [ ] **Step 2: Verify review fields landed**

Run against staging:

```sql
select
    count(*) filter (where top3_review_count_min is not null) as facts_with_review_floor,
    count(*) as total_facts
from public.seo_facts
where niche_normalized = 'concrete contractor'
  and cbsa_code = '38060'
  and snapshot_date = current_date;
```

Expected: `facts_with_review_floor > 0` when the SERP has local pack data.

- [ ] **Step 3: Run pilot collection**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.run_pilot
```

Expected: 200 attempted pairs, materially fewer failures than the 2026-04-26 baseline, and facts with review floors.

- [ ] **Step 4: Recompute benchmarks**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.recompute_benchmarks 120
```

Expected: `seo_benchmarks` row count greater than 0.

- [ ] **Step 5: Audit confidence coverage**

Run against staging:

```sql
select
    confidence_label,
    count(*) as cells
from public.seo_benchmarks
group by confidence_label
order by confidence_label;
```

Expected: pilot may produce mostly `low` and `medium`. Record this in the final implementation note; do not claim high-confidence benchmarks unless `sample_size_metros >= 20`.

- [ ] **Step 6: Commit code changes only**

```bash
git add scripts/benchmarks/run_pilot.py
git commit -m "feat: run benchmark pilot with review floor facts"
```

Do not commit secrets or generated Supabase data.

---

## Task 9: Expand From Pilot to Benchmark Coverage Targets

**Files:**
- Modify: `scripts/benchmarks/run_pilot.py` or create `scripts/benchmarks/run_collection.py`
- Modify: `scripts/benchmarks/metros_sampled.json`
- Modify: `tests/scripts/test_benchmark_sampling.py`
- Modify: `tests/unit/test_dataforseo_client.py`
- Modify: `src/clients/dataforseo/client.py`

- [ ] **Step 1: Define minimum coverage target**

Use this acceptance target for staging:

```text
Minimum usable benchmark cell: sample_size_metros >= 8
Stable benchmark cell: sample_size_metros >= 20
Required before production cutover: every launch niche has at least one medium cell in its most common population class.
```

- [ ] **Step 2: Add paid eligibility controls to runner**

Add default paid-collection pruning to `run_pilot.py`:

```text
Default paid eligible:
- native DataForSEO code exists
- population_class is mega_5m_plus, metro_1m_5m, large_300k_1m, or validated medium_100_300k

Default excluded:
- small_50_100k
- micro_under_50k
- no native DFS code
- state-borrowed DFS code
```

Add `--include-low-signal` as an explicit diagnostic escape hatch and `--preflight-only` to run keyword-volume validation without SERP pulls or Supabase writes.

- [ ] **Step 3: Run a cheap keyword-volume preflight**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.run_pilot --preflight-only --niche plumber --niche concrete\ contractor --limit-pairs 10
```

Expected: no systemic `invalid_keyword_volume_code`, `keyword_volume_empty`, or `task_queue_timeout` bucket across the filtered launch sample.

- [ ] **Step 4: Run filtered launch-niche collection**

Run:

```bash
.venv/bin/python -m scripts.benchmarks.run_pilot --full-sample
.venv/bin/python -m scripts.benchmarks.recompute_benchmarks 120
```

Expected: paid collection uses the 60-metro filtered launch sample unless preflight data reduces the valid location-code set further. Do not spend on small/micro metros by default.

- [ ] **Step 5: Document remaining thin cells**

Record any remaining insufficient/low cells in this plan's execution status and `.Codex/ACTIVE_WORK.md`. Do not create duplicate validation reports.

- [ ] **Step 6: Commit**

```bash
git add scripts/benchmarks/run_pilot.py src/clients/dataforseo/client.py tests/scripts/test_benchmark_sampling.py tests/unit/test_dataforseo_client.py docs/superpowers/plans/2026-05-12-phase-7-benchmark-completion.md
git commit -m "feat: prune benchmark sampling for paid collection"
```

---

## Task 10: Wire Benchmark Reads Into V2 Scoring Planning

**Files:**
- Modify: `docs/algo_spec_v2.md`
- Modify: `docs-canonical/ARCHITECTURE.md`
- Optional future implementation file: `src/scoring/benchmark_repository.py`

- [ ] **Step 1: Record current boundary**

Add this note to `docs/algo_spec_v2.md`:

```markdown
Current boundary: Phase 7 completes when `seo_benchmarks` can be recomputed and audited in staging. V2 scoring integration is the next implementation slice and should add a repository around `seo_benchmarks` rather than querying Supabase ad hoc from scoring formulas.
```

- [ ] **Step 2: Add architecture note**

Add to `docs-canonical/ARCHITECTURE.md` near the scoring engine component:

```markdown
V2 benchmark inputs are stored in Supabase `seo_benchmarks`, recomputed from `seo_facts`, ACS-backed `metros`, and CBP-backed `census_cbp_establishments`. Scoring code should consume them through a repository boundary so tests can use fixtures without network access.
```

- [ ] **Step 3: Commit**

```bash
git add docs/algo_spec_v2.md docs-canonical/ARCHITECTURE.md
git commit -m "docs: define benchmark-to-v2 scoring boundary"
```

---

## Task 11: Add Sonar Slice-Lite Persistence and Metric Builder

**Files:**
- Create: `supabase/migrations/013_sonar_slice_lite.sql`
- Create: `scripts/sonar/__init__.py`
- Create: `scripts/sonar/build_slice_lite.py`
- Create: `tests/scripts/test_sonar_slice_metrics.py`
- Modify: `docs-canonical/DATA-MODEL.md`

- [ ] **Step 1: Create the Sonar slice-lite migration file**

Create `supabase/migrations/013_sonar_slice_lite.sql` with this body:

```sql
-- 013_sonar_slice_lite.sql
--
-- Sonar slice-lite persistence. This stores a single cell record built from
-- currently available Widby benchmark tables. Full Sonar residuals remain
-- gated on geo crosswalk, NES, BDS, and historical CBP inputs.

CREATE SCHEMA IF NOT EXISTS sonar;

CREATE TABLE IF NOT EXISTS sonar.cells (
    cell_id           TEXT PRIMARY KEY,
    naics_code        TEXT NOT NULL REFERENCES public.census_target_naics(naics_code),
    naics_version     TEXT NOT NULL DEFAULT 'NAICS2017',
    geo_id            TEXT NOT NULL,
    geo_level         TEXT NOT NULL CHECK (geo_level IN ('msa')),
    geo_name          TEXT NOT NULL,
    year              INTEGER NOT NULL,
    latest_run_id     UUID,
    latest_score      NUMERIC,
    latest_score_ts   TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'partial_sources', 'suppressed', 'insufficient_peers')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sonar.cell_runs (
    run_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id           TEXT NOT NULL REFERENCES sonar.cells(cell_id) ON DELETE CASCADE,
    cell_record       JSONB NOT NULL,
    score             NUMERIC,
    score_version     TEXT NOT NULL DEFAULT 'sonar-lite-0.1',
    parquet_root      TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sonar.scoring_weights (
    version           TEXT PRIMARY KEY,
    weights           JSONB NOT NULL,
    notes             TEXT NOT NULL,
    active            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO sonar.scoring_weights (version, weights, notes, active)
VALUES (
    'sonar-lite-0.1',
    '{"demand_supply_tension":0.40,"commercial_intent":0.20,"monetization_headroom":0.20,"serp_entry":0.20}'::jsonb,
    'Slice-lite weights for available ACS, CBP, and DataForSEO facts. Not the full Sonar residual score.',
    TRUE
)
ON CONFLICT (version) DO UPDATE SET
    weights = EXCLUDED.weights,
    notes = EXCLUDED.notes,
    active = EXCLUDED.active;

CREATE INDEX IF NOT EXISTS idx_sonar_cells_lookup
    ON sonar.cells(naics_code, geo_level, geo_id, year);

CREATE INDEX IF NOT EXISTS idx_sonar_cell_runs_cell
    ON sonar.cell_runs(cell_id, created_at DESC);

ALTER TABLE sonar.cells ENABLE ROW LEVEL SECURITY;
ALTER TABLE sonar.cell_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sonar.scoring_weights ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sonar_cells_service_all ON sonar.cells;
CREATE POLICY sonar_cells_service_all ON sonar.cells
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS sonar_cell_runs_service_all ON sonar.cell_runs;
CREATE POLICY sonar_cell_runs_service_all ON sonar.cell_runs
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS sonar_scoring_weights_service_all ON sonar.scoring_weights;
CREATE POLICY sonar_scoring_weights_service_all ON sonar.scoring_weights
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

COMMENT ON SCHEMA sonar IS
    'Cell-level Sonar outputs. Slice-lite stores available Widby benchmark-derived records; full residuals require additional source layers.';

COMMENT ON TABLE sonar.cells IS
    'Registry for Sonar cells keyed by NAICS, geo, geo level, and year.';

COMMENT ON TABLE sonar.cell_runs IS
    'Versioned Sonar CellRecord JSONB output and score lineage.';
```

- [ ] **Step 2: Add the metric-builder tests**

Create `tests/scripts/test_sonar_slice_metrics.py`:

```python
from scripts.sonar.build_slice_lite import build_metric_block, compute_lite_score


def test_build_metric_block_preserves_provenance():
    block = build_metric_block(
        value=2.9149,
        raw_inputs={"estab": 3793, "pop": 13012469},
        source="cbp_2023 + acs_2023_5yr",
        vintage="2023",
        suppression_flag=False,
    )

    assert block["value"] == 2.9149
    assert block["raw_inputs"] == {"estab": 3793, "pop": 13012469}
    assert block["source"] == "cbp_2023 + acs_2023_5yr"
    assert block["vintage"] == "2023"
    assert block["suppression_flag"] is False
    assert block["computed_at"].endswith("Z")


def test_compute_lite_score_penalizes_serp_consolidation():
    score = compute_lite_score(
        searches_per_household=0.025716,
        establishments_per_10k_pop=2.9149,
        avg_cpc=35.27,
        commercial_intent_share=1.0,
        serp_consolidation_index=0.60,
    )

    easier_serp_score = compute_lite_score(
        searches_per_household=0.025716,
        establishments_per_10k_pop=2.9149,
        avg_cpc=35.27,
        commercial_intent_share=1.0,
        serp_consolidation_index=0.20,
    )

    assert 0 <= score <= 1
    assert easier_serp_score > score
```

- [ ] **Step 3: Verify the tests fail before implementation**

Run:

```bash
.venv/bin/python -m pytest tests/scripts/test_sonar_slice_metrics.py -v
```

Expected: fails because `scripts.sonar.build_slice_lite` does not exist.

- [ ] **Step 4: Create the Sonar script package**

Create `scripts/sonar/__init__.py`:

```python
"""Sonar cell-building scripts."""
```

- [ ] **Step 5: Implement the slice-lite builder helpers**

Create `scripts/sonar/build_slice_lite.py` with these helper functions at the top:

```python
"""Build a Sonar slice-lite CellRecord from existing Widby benchmark tables."""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib import request as urlreq

SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",
)
SUPABASE_KEY = (
    os.environ.get("BENCHMARK_SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_metric_block(
    *,
    value: int | float | None,
    raw_inputs: dict[str, Any],
    source: str,
    vintage: str,
    suppression_flag: bool = False,
) -> dict[str, Any]:
    return {
        "value": value,
        "raw_inputs": raw_inputs,
        "source": source,
        "vintage": vintage,
        "computed_at": utc_now_iso(),
        "suppression_flag": suppression_flag,
    }


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def compute_lite_score(
    *,
    searches_per_household: float,
    establishments_per_10k_pop: float,
    avg_cpc: float,
    commercial_intent_share: float,
    serp_consolidation_index: float,
) -> float:
    demand_supply = clamp((searches_per_household / 0.02) - (establishments_per_10k_pop / 10.0))
    intent = clamp(commercial_intent_share)
    monetization = clamp(avg_cpc / 50.0)
    serp_entry = clamp(1.0 - serp_consolidation_index)
    score = (
        0.40 * demand_supply
        + 0.20 * intent
        + 0.20 * monetization
        + 0.20 * serp_entry
    )
    return round(clamp(score), 4)
```

- [ ] **Step 6: Add PostgREST read/write helpers**

Append this code to `scripts/sonar/build_slice_lite.py`:

```python
def postgrest_get(path: str) -> Any:
    if not SUPABASE_KEY:
        raise RuntimeError("Missing BENCHMARK_SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY")
    req = urlreq.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urlreq.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def postgrest_upsert(path: str, rows: list[dict[str, Any]]) -> None:
    if not SUPABASE_KEY:
        raise RuntimeError("Missing BENCHMARK_SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY")
    req = urlreq.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        data=json.dumps(rows).encode("utf-8"),
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        method="POST",
    )
    with urlreq.urlopen(req, timeout=60) as resp:
        resp.read()
```

- [ ] **Step 7: Add `build_cell_record()`**

Append this code to `scripts/sonar/build_slice_lite.py`:

```python
def build_cell_record(
    *,
    metro: dict[str, Any],
    cbp: dict[str, Any],
    seo: dict[str, Any],
    peer_count: int,
    year: int,
) -> dict[str, Any]:
    population = metro["population"]
    households = metro["households"]
    establishments = cbp["est"]
    employees = cbp["emp"]
    payroll_thousands = cbp["ap"]
    volume = seo["cluster_monthly_volume"]
    avg_cpc = seo["avg_cpc_volume_weighted"] or seo["avg_cpc_unweighted"] or 0
    commercial_intent_share = seo["commercial_transactional_volume"] / max(volume, 1)
    establishments_per_10k = establishments / max(population / 10_000, 1)
    searches_per_household = volume / max(households, 1)
    avg_employees_per_estab = employees / max(establishments, 1)
    payroll_per_emp = (payroll_thousands * 1000) / max(employees, 1)
    top_size_class_share = (
        (cbp["n50_99"] or 0)
        + (cbp["n100_249"] or 0)
        + (cbp["n250_499"] or 0)
        + (cbp["n500_999"] or 0)
        + (cbp["n1000"] or 0)
    ) / max(establishments, 1)
    serp_consolidation_index = (seo["avg_aggregator_count_top10"] or 0) / 10
    score = compute_lite_score(
        searches_per_household=searches_per_household,
        establishments_per_10k_pop=establishments_per_10k,
        avg_cpc=avg_cpc,
        commercial_intent_share=commercial_intent_share,
        serp_consolidation_index=serp_consolidation_index,
    )

    return {
        "cell_id": f"238220__msa__{metro['cbsa_code']}__{year}",
        "naics_code": "238220",
        "naics_version": "NAICS2017",
        "geo_id": metro["cbsa_code"],
        "geo_level": "msa",
        "geo_name": metro["cbsa_name"],
        "year": year,
        "extract_run_ts": utc_now_iso(),
        "supply": {
            "establishments_per_10k_pop": build_metric_block(
                value=round(establishments_per_10k, 4),
                raw_inputs={"estab": establishments, "pop": population},
                source="cbp_2023 + acs_2023_5yr",
                vintage=str(year),
                suppression_flag=cbp["suppressed"],
            ),
            "avg_employees_per_estab": build_metric_block(
                value=round(avg_employees_per_estab, 4),
                raw_inputs={"emp": employees, "estab": establishments},
                source="cbp_2023",
                vintage=str(year),
                suppression_flag=cbp["suppressed"],
            ),
            "top_size_class_share": build_metric_block(
                value=round(top_size_class_share, 4),
                raw_inputs={
                    "n50_99": cbp["n50_99"],
                    "n100_249": cbp["n100_249"],
                    "n250_499": cbp["n250_499"],
                    "n500_999": cbp["n500_999"],
                    "n1000": cbp["n1000"],
                    "estab": establishments,
                },
                source="cbp_2023",
                vintage=str(year),
                suppression_flag=cbp["suppressed"],
            ),
        },
        "demand": {
            "cluster_monthly_volume": build_metric_block(
                value=volume,
                raw_inputs={"seo_fact_rows": seo["keyword_rows"]},
                source="seo_facts",
                vintage=str(seo["fact_window_end"]),
            ),
            "commercial_intent_share": build_metric_block(
                value=round(commercial_intent_share, 4),
                raw_inputs={
                    "commercial_transactional_volume": seo["commercial_transactional_volume"],
                    "cluster_monthly_volume": volume,
                },
                source="seo_facts + intent_classifier",
                vintage=str(seo["fact_window_end"]),
            ),
            "searches_per_household": build_metric_block(
                value=round(searches_per_household, 6),
                raw_inputs={"cluster_monthly_volume": volume, "households": households},
                source="seo_facts + acs_2023_5yr",
                vintage=str(year),
            ),
        },
        "monetization_capacity": {
            "median_hh_income": build_metric_block(
                value=metro["median_household_income_usd"],
                raw_inputs={"median_household_income_usd": metro["median_household_income_usd"]},
                source="acs_2023_5yr",
                vintage=str(year),
            ),
            "owner_occupied_share": build_metric_block(
                value=float(metro["owner_occupancy_rate"]),
                raw_inputs={"owner_occupancy_rate": float(metro["owner_occupancy_rate"])},
                source="acs_2023_5yr",
                vintage=str(year),
            ),
            "payroll_per_emp": build_metric_block(
                value=round(payroll_per_emp, 2),
                raw_inputs={"payroll_thousands": payroll_thousands, "emp": employees},
                source="cbp_2023",
                vintage=str(year),
                suppression_flag=cbp["suppressed"],
            ),
        },
        "seo_economics": {
            "cpc_top_low_weighted": build_metric_block(
                value=round(avg_cpc, 2),
                raw_inputs={"cluster_monthly_volume": volume},
                source="seo_facts.cpc_usd",
                vintage=str(seo["fact_window_end"]),
            ),
            "serp_local_pack_rate": build_metric_block(
                value=round(seo["serp_local_pack_rate"], 4),
                raw_inputs={"keyword_rows": seo["keyword_rows"]},
                source="seo_facts.local_pack_present",
                vintage=str(seo["fact_window_end"]),
            ),
            "serp_consolidation_index": build_metric_block(
                value=round(serp_consolidation_index, 4),
                raw_inputs={"avg_aggregator_count_top10": seo["avg_aggregator_count_top10"]},
                source="seo_facts.aggregator_count_top10",
                vintage=str(seo["fact_window_end"]),
            ),
        },
        "derived_ratios": {
            "monetization_headroom": build_metric_block(
                value=round((avg_cpc * commercial_intent_share) / max(payroll_per_emp / 1000, 0.01), 4),
                raw_inputs={
                    "avg_cpc": avg_cpc,
                    "commercial_intent_share": commercial_intent_share,
                    "payroll_per_emp": payroll_per_emp,
                },
                source="derived",
                vintage=str(year),
            )
        },
        "residuals": {},
        "data_quality": {
            "suppression_count": 1 if cbp["suppressed"] else 0,
            "suppressed_fields": ["cbp"] if cbp["suppressed"] else [],
            "imputed_fields": [],
            "freshness_lag_days": None,
            "warnings": [
                "slice_lite_no_nes",
                "slice_lite_no_bds",
                "slice_lite_no_trends",
                "slice_lite_no_geo_crosswalk",
                "slice_lite_no_residual_model",
            ],
            "peer_count_238220": peer_count,
        },
        "score": {
            "underserved_score": score,
            "score_components": {
                "searches_per_household": round(searches_per_household, 6),
                "establishments_per_10k_pop": round(establishments_per_10k, 4),
                "commercial_intent_share": round(commercial_intent_share, 4),
                "avg_cpc": round(avg_cpc, 2),
                "serp_consolidation_index": round(serp_consolidation_index, 4),
            },
            "score_version": "sonar-lite-0.1",
        },
    }
```

- [ ] **Step 8: Add the CLI path for LA plumbing**

Append this code to `scripts/sonar/build_slice_lite.py`:

```python
def fetch_la_plumber_inputs(year: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
    metro = postgrest_get(
        "metros?cbsa_code=eq.31080&select=cbsa_code,cbsa_name,population,households,"
        "owner_occupancy_rate,median_household_income_usd,acs_vintage"
    )[0]
    cbp = postgrest_get(
        "census_cbp_establishments?cbsa_code=eq.31080&naics_code=eq.238220"
        f"&year=eq.{year}&select=*"
    )[0]
    seo_rows = postgrest_get(
        "seo_facts?cbsa_code=eq.31080&niche_normalized=eq.plumber"
        "&intent=in.(transactional,commercial)&select=*"
    )
    volume = sum(row["search_volume_monthly"] or 0 for row in seo_rows)
    volume_with_cpc = sum(
        row["search_volume_monthly"] or 0
        for row in seo_rows
        if row.get("cpc_usd") is not None
    )
    weighted_cpc_numerator = sum(
        (row["search_volume_monthly"] or 0) * float(row["cpc_usd"] or 0)
        for row in seo_rows
        if row.get("cpc_usd") is not None
    )
    seo = {
        "keyword_rows": len(seo_rows),
        "cluster_monthly_volume": volume,
        "commercial_transactional_volume": volume,
        "avg_cpc_unweighted": (
            sum(float(row["cpc_usd"] or 0) for row in seo_rows) / max(len(seo_rows), 1)
        ),
        "avg_cpc_volume_weighted": (
            weighted_cpc_numerator / volume_with_cpc if volume_with_cpc else None
        ),
        "serp_local_pack_rate": (
            sum(1 for row in seo_rows if row["local_pack_present"]) / max(len(seo_rows), 1)
        ),
        "avg_aggregator_count_top10": (
            sum(row["aggregator_count_top10"] or 0 for row in seo_rows) / max(len(seo_rows), 1)
        ),
        "fact_window_end": max(
            (row.get("snapshot_date") for row in seo_rows if row.get("snapshot_date")),
            default=None,
        ),
    }
    peers = postgrest_get(
        "census_cbp_establishments?naics_code=eq.238220&year=eq.2023"
        "&est=gt.50&suppressed=eq.false&select=cbsa_code"
    )
    return metro, cbp, seo, len(peers)


def persist_cell_record(record: dict[str, Any]) -> None:
    postgrest_upsert(
        "sonar.cells?on_conflict=cell_id",
        [{
            "cell_id": record["cell_id"],
            "naics_code": record["naics_code"],
            "naics_version": record["naics_version"],
            "geo_id": record["geo_id"],
            "geo_level": record["geo_level"],
            "geo_name": record["geo_name"],
            "year": record["year"],
            "latest_score": record["score"]["underserved_score"],
            "latest_score_ts": record["extract_run_ts"],
            "status": "partial_sources",
        }],
    )
    postgrest_upsert(
        "sonar.cell_runs",
        [{
            "cell_id": record["cell_id"],
            "cell_record": record,
            "score": record["score"]["underserved_score"],
            "score_version": record["score"]["score_version"],
        }],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()
    metro, cbp, seo, peer_count = fetch_la_plumber_inputs(args.year)
    record = build_cell_record(
        metro=metro,
        cbp=cbp,
        seo=seo,
        peer_count=peer_count,
        year=args.year,
    )
    print(json.dumps(record, indent=2, sort_keys=True))
    if args.persist:
        persist_cell_record(record)


if __name__ == "__main__":
    main()
```

- [ ] **Step 9: Run the unit tests**

Run:

```bash
.venv/bin/python -m pytest tests/scripts/test_sonar_slice_metrics.py -v
```

Expected: pass.

- [ ] **Step 10: Apply the migration to staging only**

Apply `supabase/migrations/013_sonar_slice_lite.sql` to `whidby-staging` using Supabase migration tooling after Task 6 and Task 7 are already green.

Expected: `sonar.cells`, `sonar.cell_runs`, and `sonar.scoring_weights` exist in staging.

- [ ] **Step 11: Build the LA plumbing slice without persistence**

Run:

```bash
.venv/bin/python -m scripts.sonar.build_slice_lite --year 2023
```

Expected: prints a JSON `CellRecord` with `cell_id` equal to `238220__msa__31080__2023`, `score.score_version` equal to `sonar-lite-0.1`, and `data_quality.warnings` containing all five `slice_lite_*` warnings.

- [ ] **Step 12: Persist the LA plumbing slice in staging**

Run:

```bash
.venv/bin/python -m scripts.sonar.build_slice_lite --year 2023 --persist
```

Expected: one row in `sonar.cells` for `238220__msa__31080__2023` and at least one row in `sonar.cell_runs` for that cell.

- [ ] **Step 13: Document the Sonar entities**

Add this concise section to `docs-canonical/DATA-MODEL.md` after the Supabase entity table:

```markdown
### Sonar Slice-Lite Entities

| Entity | Storage | Primary Key | Description |
| --- | --- | --- | --- |
| SonarCell | Supabase `sonar.cells` | `cell_id` | Cell registry keyed by NAICS, geo level, geo id, and year. |
| SonarCellRun | Supabase `sonar.cell_runs` | `run_id` | Versioned CellRecord JSONB output. Slice-lite records include explicit data-quality warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs. |
| SonarScoringWeights | Supabase `sonar.scoring_weights` | `version` | Active score weights by Sonar score version. |
```

- [ ] **Step 14: Commit**

```bash
git add supabase/migrations/013_sonar_slice_lite.sql scripts/sonar/__init__.py scripts/sonar/build_slice_lite.py tests/scripts/test_sonar_slice_metrics.py docs-canonical/DATA-MODEL.md
git commit -m "feat: add sonar slice-lite cell record path"
```

---

## Task 12: Plan the Full Sonar Residual Closure After Slice-Lite

**Files:**
- Modify: `docs/algo_spec_v2.md`
- Modify: `docs-canonical/DATA-MODEL.md`
- Future create: `supabase/migrations/014_sonar_geo_crosswalk.sql`
- Future create: `src/sonar/residuals.py`
- Future create: `tests/sonar/test_residuals.py`

- [ ] **Step 1: Add a Sonar feasibility section to `docs/algo_spec_v2.md`**

Add this section after the benchmark computation section:

```markdown
## Sonar Compatibility Boundary

The current benchmark tables can produce a Sonar slice-lite CellRecord for LA plumbing (`238220__msa__31080__2023`) using ACS-backed `metros`, CBP-backed `census_cbp_establishments`, NAICS mapping, and DataForSEO-derived `seo_facts`.

The full Sonar residual spec remains blocked on these source layers:

| Required layer | Current status | Blocking effect |
| --- | --- | --- |
| `geo.canonical_geo` and `geo.crosswalk` | Not loaded | Cannot roll county-level NES or BDS to MSA with auditable weights. |
| NES county extracts | Not loaded | Cannot compute `nonemp_to_emp_ratio`. |
| BDS 2018-2023 extracts | Not loaded | Cannot compute establishment exit/churn trajectory. |
| CBP 2018-2022 history | Not loaded | Cannot compute five-year establishment CAGR. |
| Google Trends 24-month series | Adapter exists, not stored by cell | Cannot compute `trends_slope_24mo` or `seasonality_index`. |
| Top-3 review floors | `seo_facts` columns exist, current rows are null | Cannot compute Sonar local-pack review barriers. |
| Residual peer matrix | Not materialized | Cannot rank cells on actual-minus-expected residuals. |

Slice-lite scores must use `score_version = "sonar-lite-0.1"` and include data-quality warnings for each missing layer. Full Sonar scores must use a distinct score version after residuals are backed by a peer matrix.
```

- [ ] **Step 2: Add the full residual migration sketch to `docs-canonical/DATA-MODEL.md`**

Add this note below the Sonar Slice-Lite section:

```markdown
Full Sonar residuals require additional canonical layers before implementation: `geo.canonical_geo`, `geo.crosswalk`, county-level NES source tables, BDS source tables, historical CBP source tables, and residual model artifact storage. Do not mark a Sonar cell as full-spec unless residuals are computed from a peer matrix with `peer_count >= 30` and recorded model quality.
```

- [ ] **Step 3: Define the future residual model contract**

When the missing source layers are available, create `src/sonar/residuals.py` with this public contract:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResidualResult:
    metric: str
    actual: float
    expected: float
    residual: float
    model_r2: float
    peer_count: int
    quality_label: str


def quality_label(model_r2: float, peer_count: int) -> str:
    if peer_count < 30:
        return "insufficient_peers"
    if model_r2 < 0.3:
        return "low_confidence"
    return "usable"
```

- [ ] **Step 4: Define the future residual tests**

When `src/sonar/residuals.py` is created, create `tests/sonar/test_residuals.py`:

```python
from src.sonar.residuals import quality_label


def test_quality_label_requires_minimum_peer_count():
    assert quality_label(model_r2=0.8, peer_count=29) == "insufficient_peers"


def test_quality_label_marks_low_r2_as_low_confidence():
    assert quality_label(model_r2=0.29, peer_count=250) == "low_confidence"


def test_quality_label_accepts_strong_peer_model():
    assert quality_label(model_r2=0.4, peer_count=250) == "usable"
```

- [ ] **Step 5: Commit**

```bash
git add docs/algo_spec_v2.md docs-canonical/DATA-MODEL.md
git commit -m "docs: define sonar full-spec closure gates"
```

---

## Task 13: Promote to Production Only After Staging Is Green

**Files:**
- Supabase migrations: `009`, `010`, reconciled `011`, `012`, and `013` if Sonar slice-lite is approved for production
- Modify: `docs-canonical/ENVIRONMENT.md`

- [ ] **Step 1: Verify staging migration list**

Run via Supabase:

```text
List migrations for whidby-staging.
```

Expected: includes `metros_and_census`, `v2_benchmarks`, reconciled provider migration if applied, and `recompute_seo_benchmarks`.

- [ ] **Step 2: Verify staging benchmark health**

Run:

```sql
select
    count(*) as benchmark_cells,
    count(*) filter (where confidence_label in ('medium', 'high')) as usable_cells,
    count(*) filter (where median_top3_review_count_min is not null) as cells_with_review_floor
from public.seo_benchmarks;
```

Expected: non-zero `benchmark_cells`; non-zero `usable_cells` before production promotion.

- [ ] **Step 3: Apply migrations to production**

Apply migrations to `whidby` production in order:

1. `009_metros_and_census.sql`
2. `010_v2_benchmarks.sql`
3. reconciled `011_data_provider_tables.sql`, if still needed
4. `012_recompute_seo_benchmarks.sql`
5. `013_sonar_slice_lite.sql`, only after the LA plumbing slice-lite record has been validated in staging

Use Supabase migration tooling. Do not manually paste partial SQL into production.

- [ ] **Step 4: Load production reference data**

Load or copy only reference data needed for launch:

- `metros`
- `census_cbp_establishments`
- `census_target_naics`
- `niche_naics_mapping`

Do not copy staging `seo_facts` unless product wants staging pilot observations to seed production benchmarks.

- [ ] **Step 5: Run production smoke queries**

Run against production:

```sql
select count(*) from public.metros;
select count(*) from public.census_cbp_establishments;
select count(*) from public.seo_benchmarks;
```

Expected: reference counts are non-zero. `seo_benchmarks` can remain zero until production facts are collected, but the recompute function must execute successfully.

- [ ] **Step 6: Commit production notes**

Add a concise production status note to `docs-canonical/ENVIRONMENT.md` with the exact date migrations were applied and whether `seo_benchmarks` is staging-only or production-seeded.

```bash
git add docs-canonical/ENVIRONMENT.md
git commit -m "docs: record benchmark production setup status"
```

---

## Task 14: Final Validation

**Files:**
- All changed files

- [ ] **Step 1: Run Phase 7 focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/clients/census/ tests/clients/bls/ tests/clients/trends/ tests/clients/test_composite_providers.py tests/scripts/test_benchmark_serp_parsing.py -v
.venv/bin/python -m pytest tests/scripts/test_sonar_slice_metrics.py -v
```

Expected: pass.

- [ ] **Step 2: Run architecture checks**

Run:

```bash
.venv/bin/python scripts/check_domain_imports.py
.venv/bin/python -m pytest tests/architecture/ -v
```

Expected: pass.

- [ ] **Step 3: Run Python lint**

Run:

```bash
.venv/bin/python -m ruff check src tests scripts
```

Expected: pass.

- [ ] **Step 4: Run benchmark staging audit**

Run against staging:

```sql
select
    count(*) as benchmark_cells,
    min(last_recomputed_at) as oldest_recompute,
    max(last_recomputed_at) as newest_recompute
from public.seo_benchmarks;
```

Expected: `benchmark_cells > 0`.

- [ ] **Step 5: Run Sonar staging audit if Task 11 was applied**

Run against staging:

```sql
select
    c.cell_id,
    c.status,
    c.latest_score,
    count(r.run_id) as run_count
from sonar.cells c
left join sonar.cell_runs r on r.cell_id = c.cell_id
where c.cell_id = '238220__msa__31080__2023'
group by c.cell_id, c.status, c.latest_score;
```

Expected: one row, `status = 'partial_sources'`, and `run_count >= 1`.

- [ ] **Step 6: Run DocGuard after docs changes**

Run:

```bash
npx docguard-cli guard
```

Expected: pass.

- [ ] **Step 7: Final git status**

Run:

```bash
git status --short
```

Expected: only intentional changes remain.

---

## Execution Order

1. Task 1 - local test environment
2. Task 2 - benchmark env separation
3. Task 3 - reconcile unapplied provider migration
4. Task 4 - capture review floors
5. Task 5 - enrich DFS location codes
6. Task 6 - recompute SQL function
7. Task 7 - recompute runner
8. Task 8 - rerun pilot with review fields
9. Task 9 - expand benchmark coverage
10. Task 10 - define V2 scoring boundary
11. Task 11 - add Sonar slice-lite cell record path
12. Task 12 - define full Sonar residual closure gates
13. Task 13 - production promotion
14. Task 14 - final validation

## Self-Review

- Spec coverage: The plan covers Phase 7 provider health, Supabase benchmark schema reconciliation, benchmark fact collection, benchmark aggregation, staging validation, Sonar slice-lite feasibility, Sonar full-spec blockers, and production setup.
- Placeholder scan: No task depends on an undefined "later" implementation. Known deferred items are review velocity and full Sonar residuals, both explicitly gated on missing source data instead of being treated as complete.
- Type consistency: The plan uses existing table names from migrations `009` and `010`: `metros`, `census_cbp_establishments`, `niche_naics_mapping`, `seo_facts`, `seo_benchmarks`, and `metro_score_v2`. The new Sonar persistence path uses schema-qualified tables `sonar.cells`, `sonar.cell_runs`, and `sonar.scoring_weights`.
