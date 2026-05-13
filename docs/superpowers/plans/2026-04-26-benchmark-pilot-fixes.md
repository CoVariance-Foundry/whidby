# Benchmark Pilot Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the three failure buckets in `run_pilot.py` that caused 155/200 reports to fail, then re-run to validate.

**Architecture:** Three independent fixes — each addresses one failure category and is validated independently before moving on. No new abstractions; minimal changes to existing scripts and data files.

**Tech Stack:** Python 3.11+, DataForSEO API, Supabase PostgREST, asyncio

---

## Pilot Results Baseline (2026-04-26 run)

| Metric | Value |
|--------|-------|
| Total pairs | 200 (10 niches × 20 metros) |
| Succeeded | 45 (22.5%) |
| Failed — no DFS code | 70 (7 metros × 10 niches) |
| Failed — empty volume | 85 (DFS code exists but keyword_volume returned null) |
| Failed — upsert errors | 0 (cache 401s are non-blocking) |
| Facts inserted | 1,200 |
| Runtime | 785s |

### Failure Bucket Summary

1. **Supabase credentials** — `run_pilot.py` hardcodes staging URL (`wuybidpvqhhgkukpyyhq`) but reads `SUPABASE_SERVICE_ROLE_KEY` from `.env`. If `.env` has prod credentials, the key won't authenticate against staging. The `PersistentResponseCache` also reads `NEXT_PUBLIC_SUPABASE_URL` from `.env` (prod URL), causing 401s on every cache read/write.

2. **Missing DFS location codes** — 7 of 20 pilot metros have empty `dataforseo_location_codes` in `metros_sampled.json`. All are medium/small/micro class metros. The script skips them entirely. The existing DFS location bridge in `src/research_agent/places.py` can resolve city→DFS code but isn't wired into the benchmark sampling.

3. **Empty volume from wrong DFS code** — 85 reports have valid DFS codes but `keyword_volume` returns null for every keyword. Root cause: metros with multiple DFS codes (e.g., LA has 3) only use `loc_codes[0]`, which may be a suburb/subregion code that doesn't return volume data. Also, some DFS codes in the sample may be stale or mismatched.

---

## Fix 1: Supabase Staging Credentials

**Problem:** The benchmark runner and persistent cache use mismatched Supabase credentials.

**Files:**
- Modify: `scripts/benchmarks/run_pilot.py:54-58`
- Modify: `.env` (add `BENCHMARK_SUPABASE_URL` and `BENCHMARK_SUPABASE_KEY`)

### Task 1.1: Add staging-specific env vars to `.env`

- [ ] **Step 1: Add benchmark-specific Supabase env vars to `.env`**

The user has staging credentials already. Add two new vars so the benchmark runner uses staging without disturbing prod credentials used by the apps:

```
# Benchmark staging (whidby_staging project)
BENCHMARK_SUPABASE_URL=https://wuybidpvqhhgkukpyyhq.supabase.co
BENCHMARK_SUPABASE_KEY=<staging service role key from Supabase dashboard>
```

The user must paste the actual staging service role key from the Supabase dashboard → Settings → API → `service_role` key for the `wuybidpvqhhgkukpyyhq` project.

### Task 1.2: Update `run_pilot.py` to read staging-specific key

- [ ] **Step 1: Update the credential loading in `run_pilot.py`**

In `scripts/benchmarks/run_pilot.py`, change lines 54-58 from:

```python
SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",  # staging
)
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
```

To:

```python
SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",  # staging
)
SUPABASE_KEY = os.environ.get("BENCHMARK_SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
```

- [ ] **Step 2: Suppress persistent cache for benchmarks**

The `PersistentResponseCache` inside `DataForSEOClient` reads `NEXT_PUBLIC_SUPABASE_URL` (prod). For benchmarks we don't need the cache — it adds noise and 401 spam. Add an env var override before creating the DFS client in `run_pilot.py`, after line 397 (`dfs = DataForSEOClient(...)`):

Actually, cleaner: set the env vars before the DataForSEOClient is created. Add this block right before `dfs = DataForSEOClient(...)` at line 397:

```python
    # Point persistent cache at staging (or disable it)
    os.environ["NEXT_PUBLIC_SUPABASE_URL"] = SUPABASE_URL
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = SUPABASE_KEY or ""
```

This ensures the DFS client's internal cache also talks to staging.

- [ ] **Step 3: Validate the upsert works**

Run a quick smoke test — score one (niche, metro) pair and check that `seo_facts` rows land in staging:

```bash
source .venv/bin/activate
python3 -c "
from scripts.benchmarks.run_pilot import upsert_facts, SUPABASE_URL, SUPABASE_KEY
print(f'URL: {SUPABASE_URL}')
print(f'Key present: {bool(SUPABASE_KEY)}')
status, body = upsert_facts([{
    'niche_keyword': 'test', 'niche_normalized': 'test',
    'cbsa_code': '35620', 'keyword': 'test keyword',
    'keyword_tier': 1, 'intent': 'transactional',
    'search_volume_monthly': 100, 'cpc_usd': 5.00,
    'aio_present': False, 'local_pack_present': True,
    'local_pack_position': 3, 'aggregator_count_top10': 2,
    'local_biz_count_top10': 5, 'featured_snippet_present': False,
    'paa_count': 4, 'ads_present': True, 'lsa_present': False,
    'snapshot_date': '2026-04-26', 'source': 'manual',
}])
print(f'Status: {status}, Body: {body[:200]}')
"
```

Expected: `Status: 201, Body: ` (empty body with 201 Created).

If you get 401: the key doesn't match the staging project. If you get 404: the `seo_facts` table doesn't exist on staging — run migration `010_v2_benchmarks.sql` against the staging project first.

- [ ] **Step 4: Commit**

```bash
git add scripts/benchmarks/run_pilot.py
git commit -m "fix(benchmarks): use staging-specific Supabase key for pilot runner"
```

Do NOT commit `.env` changes (secrets).

---

## Fix 2: Enrich Missing DFS Location Codes

**Problem:** 7 of 20 pilot metros have empty `dataforseo_location_codes` in `metros_sampled.json`. All are in medium/small/micro population classes.

| CBSA | Metro | Pop Class |
|------|-------|-----------|
| 43300 | Sherman-Denison, TX | medium_100_300k |
| 18260 | Cookeville, TN | medium_100_300k |
| 49020 | Winchester, VA-WV | medium_100_300k |
| 18900 | Crossville, TN | small_50_100k |
| 24180 | Granbury, TX | small_50_100k |
| 41820 | Sanford, NC | small_50_100k |
| 37940 | Peru, IN | micro_under_50k |

**Approach:** Write a one-shot enrichment script that calls the free DFS `GET /serp/google/locations` endpoint, builds a city index (same logic as `src/research_agent/places.py`), and patches `metros_sampled.json` in place.

**Files:**
- Create: `scripts/benchmarks/enrich_dfs_codes.py`
- Modify: `scripts/benchmarks/metros_sampled.json` (output — updated by script)

### Task 2.1: Write the DFS enrichment script

- [ ] **Step 1: Write the failing test — verify the script enriches a known metro**

No separate test file — this is a one-shot data script. The script itself validates output.

- [ ] **Step 2: Create `scripts/benchmarks/enrich_dfs_codes.py`**

```python
"""One-shot DFS location code enrichment for metros_sampled.json.

Calls the free DataForSEO GET /serp/google/locations endpoint,
builds a city name index, and patches metros that have empty
dataforseo_location_codes.

Usage:
  cd whidby
  source .venv/bin/activate
  python -m scripts.benchmarks.enrich_dfs_codes [--dry-run]
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.clients.dataforseo import DataForSEOClient  # noqa: E402
import os

DFS_LOGIN = os.environ.get("DATAFORSEO_LOGIN")
DFS_PASS = os.environ.get("DATAFORSEO_PASSWORD")

METROS_PATH = Path(__file__).parent / "metros_sampled.json"

# DFS location types that are city-level
CITY_TYPES = {"city", "city council", "municipality", "town"}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def extract_city_from_cbsa(cbsa_name: str) -> list[str]:
    """Extract candidate city names from a CBSA name like 'Sherman-Denison, TX'."""
    prefix = cbsa_name.split(",")[0]
    parts = re.split(r"[-–]", prefix)
    return [p.strip() for p in parts if p.strip()]


def build_city_index(locations: list[dict]) -> dict[str, list[dict]]:
    """Build normalized city name → location rows index."""
    index: dict[str, list[dict]] = {}
    for loc in locations:
        loc_type = str(loc.get("location_type", "")).lower()
        if loc_type not in CITY_TYPES:
            continue
        loc_name = str(loc.get("location_name", ""))
        parts = [p.strip() for p in loc_name.split(",") if p.strip()]
        if parts:
            key = normalize(parts[0])
            if key:
                index.setdefault(key, []).append(loc)
    return index


def resolve_metro(metro: dict, index: dict[str, list[dict]]) -> list[int]:
    """Try to find DFS location codes for a metro by matching city names."""
    cbsa_name = metro["cbsa_name"]
    state = metro.get("state", "")
    candidates = extract_city_from_cbsa(cbsa_name)

    codes = []
    for city in candidates:
        key = normalize(city)
        matches = index.get(key, [])
        for m in matches:
            loc_name = str(m.get("location_name", ""))
            country = str(m.get("country_iso_code", "")).upper()
            if country != "US":
                continue
            # State disambiguation: check if state abbreviation appears in location_name
            if state and state.upper() in loc_name.upper():
                code = m.get("location_code")
                if isinstance(code, int) and code not in codes:
                    codes.append(code)
        # Also try without state filter for small cities
        if not codes:
            for m in matches:
                country = str(m.get("country_iso_code", "")).upper()
                if country != "US":
                    continue
                code = m.get("location_code")
                if isinstance(code, int) and code not in codes:
                    codes.append(code)
    return codes


async def main():
    dry_run = "--dry-run" in sys.argv

    if not (DFS_LOGIN and DFS_PASS):
        print("ERROR: DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required in .env")
        sys.exit(1)

    dfs = DataForSEOClient(login=DFS_LOGIN, password=DFS_PASS)
    print("Fetching DFS locations (free endpoint)...")
    resp = await dfs.locations()
    if resp.status != "ok" or not resp.data:
        print(f"ERROR: locations() failed: {resp.error}")
        sys.exit(1)

    raw = resp.data if isinstance(resp.data, list) else [resp.data]
    # Flatten if nested
    locations = []
    for item in raw:
        if isinstance(item, list):
            locations.extend(item)
        elif isinstance(item, dict):
            locations.append(item)
    print(f"  {len(locations)} total location rows")

    index = build_city_index(locations)
    print(f"  {len(index)} city index keys")

    metros = json.loads(METROS_PATH.read_text())
    enriched = 0
    for metro in metros:
        if metro.get("dataforseo_location_codes"):
            continue
        codes = resolve_metro(metro, index)
        if codes:
            metro["dataforseo_location_codes"] = codes
            enriched += 1
            print(f"  ENRICHED {metro['cbsa_code']} {metro['cbsa_name']}: {codes}")
        else:
            print(f"  MISS     {metro['cbsa_code']} {metro['cbsa_name']}")

    still_empty = sum(1 for m in metros if not m.get("dataforseo_location_codes"))
    print(f"\nEnriched: {enriched}, Still empty: {still_empty}")

    if dry_run:
        print("(dry run — not writing)")
    else:
        METROS_PATH.write_text(json.dumps(metros, indent=2) + "\n")
        print(f"Wrote {METROS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run with --dry-run first**

```bash
source .venv/bin/activate
python -m scripts.benchmarks.enrich_dfs_codes --dry-run
```

Expected: see ENRICHED lines for some of the 7 metros (especially Sherman, Cookeville, Winchester, Sanford). Some micro metros (Peru, IN / Crossville, TN / Granbury, TX) may still miss if DFS doesn't have them as cities.

- [ ] **Step 4: Run for real**

```bash
python -m scripts.benchmarks.enrich_dfs_codes
```

Verify the file was updated:

```bash
cat scripts/benchmarks/metros_sampled.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
empty = [m for m in data if not m.get('dataforseo_location_codes')]
print(f'Still empty: {len(empty)}')
for m in empty:
    print(f'  {m[\"cbsa_code\"]} {m[\"cbsa_name\"]}')
"
```

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmarks/enrich_dfs_codes.py scripts/benchmarks/metros_sampled.json
git commit -m "feat(benchmarks): enrich metros_sampled.json with DFS location codes from API"
```

---

## Fix 3: Try Multiple DFS Codes for Volume Lookups

**Problem:** 85 reports had DFS codes but `keyword_volume` returned null for every keyword. The script uses `loc_codes[0]` which may be a suburb or subregion code that doesn't return volume data. Some metros succeeded with only 1 out of 10 niches (e.g., LA, Boston, Phoenix).

**Root cause in `run_pilot.py:287-288`:**

```python
loc_codes = metro.get("dataforseo_location_codes") or []
loc_code = loc_codes[0] if loc_codes else None
```

**Fix:** Try each DFS code until one returns non-empty volume data. Fall back to all codes exhausted = skip.

**Files:**
- Modify: `scripts/benchmarks/run_pilot.py:274-307` (the volume lookup section of `score_one`)

### Task 3.1: Add multi-code fallback to volume lookup

- [ ] **Step 1: Modify `score_one()` to try multiple DFS codes**

Replace the location code resolution and volume lookup block in `score_one()` (lines 285-307) from:

```python
        # Resolve location code (use first DFS code if seeded)
        loc_codes = metro.get("dataforseo_location_codes") or []
        loc_code = loc_codes[0] if loc_codes else None
        if loc_code is None:
            log.info(f"  no DFS code for {cbsa}; skipping in pilot")
            stats.reports_failed += 1
            return 0

        # 1) Keyword volume (one batched task per metro)
        kw_strs = [k["keyword"] for k in actionable[:50]]
        vol_resp = await dfs.keyword_volume(keywords=kw_strs, location_code=loc_code)
        volume_by_kw: dict[str, dict] = {}
        # Client returns data = task.result for queued endpoints (a list of items)
        if vol_resp.status == "ok" and vol_resp.data:
            vol_items = vol_resp.data if isinstance(vol_resp.data, list) else [vol_resp.data]
            for r in vol_items:
                if not isinstance(r, dict):
                    continue
                volume_by_kw[(r.get("keyword") or "").lower()] = {
                    "search_volume": r.get("search_volume"),
                    "cpc": r.get("cpc"),
                }
```

To:

```python
        # Resolve location code — try each DFS code until one returns volume data
        loc_codes = metro.get("dataforseo_location_codes") or []
        if not loc_codes:
            log.info(f"  no DFS code for {cbsa}; skipping in pilot")
            stats.reports_failed += 1
            return 0

        kw_strs = [k["keyword"] for k in actionable[:50]]
        volume_by_kw: dict[str, dict] = {}
        loc_code = loc_codes[0]  # default for SERP calls later

        for try_code in loc_codes:
            vol_resp = await dfs.keyword_volume(keywords=kw_strs, location_code=try_code)
            trial: dict[str, dict] = {}
            if vol_resp.status == "ok" and vol_resp.data:
                vol_items = vol_resp.data if isinstance(vol_resp.data, list) else [vol_resp.data]
                for r in vol_items:
                    if not isinstance(r, dict):
                        continue
                    sv = r.get("search_volume")
                    cpc = r.get("cpc")
                    if sv is not None or cpc is not None:
                        trial[(r.get("keyword") or "").lower()] = {
                            "search_volume": sv,
                            "cpc": cpc,
                        }
            if trial:
                volume_by_kw = trial
                loc_code = try_code
                if len(loc_codes) > 1:
                    log.info(f"  DFS code {try_code} returned {len(trial)} volume rows (tried {loc_codes.index(try_code)+1}/{len(loc_codes)})")
                break
            elif len(loc_codes) > 1:
                log.info(f"  DFS code {try_code} returned no volume — trying next")
```

- [ ] **Step 2: Also use the winning `loc_code` for SERP calls**

The SERP section below (around line 309 in the original) already uses `loc_code`. Since we now reassign `loc_code` to the code that returned volume data, the SERP calls will also use the winning code. No change needed — just verify the variable name matches.

- [ ] **Step 3: Run a targeted test — LA metro (3 DFS codes, previously 1/10 niches)**

```bash
source .venv/bin/activate
python3 -c "
import asyncio, os, sys
sys.path.insert(0, '.')
from src.clients.dataforseo import DataForSEOClient

async def test():
    dfs = DataForSEOClient(
        login=os.environ['DATAFORSEO_LOGIN'],
        password=os.environ['DATAFORSEO_PASSWORD'],
    )
    codes = [1013962, 1013849, 1013549]  # LA DFS codes
    kws = ['concrete contractor near me', 'concrete contractor los angeles']
    for code in codes:
        resp = await dfs.keyword_volume(keywords=kws, location_code=code)
        has_data = False
        if resp.status == 'ok' and resp.data:
            items = resp.data if isinstance(resp.data, list) else [resp.data]
            has_data = any(r.get('search_volume') is not None for r in items if isinstance(r, dict))
        print(f'  code={code} has_data={has_data}')

asyncio.run(test())
"
```

Expected: at least one code returns `has_data=True`.

- [ ] **Step 4: Commit**

```bash
git add scripts/benchmarks/run_pilot.py
git commit -m "fix(benchmarks): try all DFS location codes for volume, not just first"
```

---

## Validation: Re-run Pilot

After all three fixes are applied:

- [ ] **Step 1: Re-run the full pilot**

```bash
source .venv/bin/activate
python3 -m scripts.benchmarks.run_pilot 2>&1 | tee /tmp/pilot_run2.log
```

- [ ] **Step 2: Compare results**

```bash
grep "DONE in" /tmp/pilot_run2.log
```

**Success criteria:**
- No Supabase 401 errors in the log
- Reports succeeded > 100/200 (>50%, up from 45)
- DFS-skip count reduced from 70 to <20
- Facts inserted > 2,500 (up from 1,200)

- [ ] **Step 3: Verify facts landed in staging**

```bash
curl -s "${BENCHMARK_SUPABASE_URL}/rest/v1/seo_facts?select=count&limit=1" \
  -H "apikey: ${BENCHMARK_SUPABASE_KEY}" \
  -H "Authorization: Bearer ${BENCHMARK_SUPABASE_KEY}" \
  -H "Prefer: count=exact"
```
