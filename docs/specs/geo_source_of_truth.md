# Geo Source of Truth — Migration Spec

**Status:** Draft
**Author:** Antwoine Flowers / Kael
**Date:** 2026-04-27
**Spec Version:** 1.0
**Linked work:** V2 scoring (`docs/algo_spec_v2.md`), migration `010_v2_benchmarks.sql`

---

## 1. Problem

`src/data/seed/cbsa_seed.json` is the de facto geo source of truth for the scoring engine. It loads into `MetroDB` (in-memory) at startup and feeds `MetroDBGeoLookup`, which the orchestrator uses to resolve cities. Two structural problems:

1. **Stale by design.** Census redefines CBSAs every release (e.g., the 2023 vintage split Cleveland-Elyria 17460 into Cleveland 17410 + Elyria as separate entities). The JSON seed has obsolete codes; the new `metros` Supabase table has the current ones. We are now running with two sources of truth that already disagree.

2. **Coverage gap.** The seed contains 60 metros (the original V1 launch set) and is hand-curated. The new `metros` table has all 935 CBSAs from ACS, but the geo resolution layer can't see them. Scoring runs for any non-seeded metro currently fall back to a state-level borrow code, which produces noisy SERP geotargeting.

3. **Mapbox→DFS bridge is uncached.** The `apps/admin/api/places/suggest` route fetches DataForSEO's full ~95K-row locations list on demand to resolve a place_id to a DFS location code. That's slow on first hit and expensive in aggregate. The resolutions are not written back anywhere, so we re-resolve identical places forever.

Coral's call surfaced #1 directly ("the codes in the seed are old"). #2 and #3 are downstream consequences.

---

## 2. Goal

Make `public.metros` the single authoritative geo store. Eliminate `cbsa_seed.json` and `MetroDB`. The Mapbox→DFS bridge writes through to `metros` and benefits all future lookups.

**Non-goals:**
- Not changing the `GeoLookup` port contract — adapter pattern stays.
- Not changing how DataForSEO geo-targeting works at the API layer.
- Not adding international support yet (US CBSAs only, same as today).

---

## 3. Requirements

### 3.1 Functional

| Requirement | Acceptance criterion |
|---|---|
| Geo lookup reads from Supabase, not JSON | `from src.data.seed.cbsa_seed` produces no imports anywhere in `src/`, `apps/admin/`, `apps/app/` |
| All 935 CBSAs resolvable | `geo_lookup.find_by_city("Boise", "ID")` returns a `City` even though Boise is not in the old seed |
| Mapbox→DFS bridge writes through to metros | After a successful place resolution, `metros.dataforseo_location_codes` contains the resolved code and `metros.place_id` contains the Mapbox ID |
| Cleveland-style drift is resolved at the source | A scheduled or manual reconciliation job updates `metros` from a fresh ACS pull; no per-row patching |
| Tests don't require live Supabase | `pytest tests/unit/` passes without network using an in-memory fixture-backed lookup |

### 3.2 Non-functional

| Requirement | Target |
|---|---|
| `find_by_city` p99 latency | < 50 ms (hot cache), < 500 ms (cold) |
| Memory footprint of in-process cache | < 5 MB for 935 metros |
| Cache staleness tolerance | 1 hour TTL acceptable; explicit refresh on demand |
| Backward compat for V1.1 callers | One release cycle of dual-read; existing `score_niche_for_metro` keeps working |

---

## 4. Schema changes

Minimal — `metros` already has most of what we need. Two additions:

```sql
ALTER TABLE public.metros
  ADD COLUMN IF NOT EXISTS place_id TEXT,                  -- Mapbox feature.id
  ADD COLUMN IF NOT EXISTS place_id_resolved_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_metros_place_id ON public.metros(place_id)
  WHERE place_id IS NOT NULL;
```

Optional indexes for the lookup paths:

```sql
-- Fast city-name match. Trigram for typo tolerance + prefix matching.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_metros_principal_cities_trgm
  ON public.metros USING gin (principal_cities gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_metros_cbsa_name_trgm
  ON public.metros USING gin (cbsa_name gin_trgm_ops);
```

`metro_location_cache` already exists and is populated; it serves the autocomplete fast path. Migration `010_v2_benchmarks.sql` already added the trigram index there. We extend `metros` with the same pattern for direct lookups.

Migration target: `supabase/migrations/011_metros_place_id.sql`

---

## 5. New adapter

`src/data/supabase_metros_adapter.py`:

```python
from __future__ import annotations

import os
import time
from typing import Optional

import httpx

from src.domain.entities import City
from src.domain.ports import GeoLookup


class SupabaseMetrosGeoLookup(GeoLookup):
    """GeoLookup backed by the public.metros table.

    Loads all 935 metros into memory at construction and refreshes on TTL.
    Optimizes for hot-path lookups by city name + state.
    """

    def __init__(
        self,
        supabase_url: str,
        publishable_key: str,
        ttl_seconds: int = 3600,
    ) -> None:
        self._url = supabase_url.rstrip("/")
        self._key = publishable_key
        self._ttl = ttl_seconds
        self._cache: list[City] = []
        self._by_code: dict[str, City] = {}
        self._by_city_state: dict[tuple[str, str], City] = {}
        self._loaded_at: float = 0.0

    def _maybe_refresh(self) -> None:
        if time.time() - self._loaded_at < self._ttl and self._cache:
            return
        self._reload()

    def _reload(self) -> None:
        url = (
            f"{self._url}/rest/v1/metros"
            "?select=cbsa_code,cbsa_name,state,population,population_class,"
            "principal_cities,dataforseo_location_codes,place_id"
            "&order=population.desc"
        )
        headers = {"apikey": self._key, "Authorization": f"Bearer {self._key}"}
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, headers=headers)
            r.raise_for_status()
            rows = r.json()
        cities = [self._row_to_city(row) for row in rows]
        self._cache = cities
        self._by_code = {c.cbsa_code: c for c in cities}
        self._by_city_state = {}
        for c in cities:
            for pc in c.principal_cities:
                self._by_city_state[(pc.lower(), c.state)] = c
        self._loaded_at = time.time()

    @staticmethod
    def _row_to_city(row: dict) -> City:
        return City(
            city_id=row["cbsa_code"],
            name=row["cbsa_name"],
            state=row["state"],
            population=row.get("population") or 0,
            cbsa_code=row["cbsa_code"],
            dataforseo_location_codes=row.get("dataforseo_location_codes") or [],
            principal_cities=row.get("principal_cities") or [],
        )

    # GeoLookup port -------------------------------------------------------

    def find_by_city(self, city: str, state: Optional[str] = None) -> Optional[City]:
        self._maybe_refresh()
        if state:
            return self._by_city_state.get((city.lower(), state))
        # Fallback: linear scan with substring match (rare path)
        c_lower = city.lower()
        for ent in self._cache:
            if any(c_lower == pc.lower() for pc in ent.principal_cities):
                return ent
        return None

    def all_metros(self) -> list[City]:
        self._maybe_refresh()
        return list(self._cache)

    # Extension methods (not part of the GeoLookup protocol) ---------------

    def find_by_cbsa_code(self, cbsa_code: str) -> Optional[City]:
        self._maybe_refresh()
        return self._by_code.get(cbsa_code)

    def find_by_place_id(self, place_id: str) -> Optional[City]:
        self._maybe_refresh()
        for c in self._cache:
            if getattr(c, "place_id", None) == place_id:
                return c
        return None
```

A test-only `InMemoryGeoLookup` already implicit in `MetroDBGeoLookup`'s shape — wrap it explicitly:

```python
# src/data/in_memory_geo_lookup.py — test fixture support
class InMemoryGeoLookup(GeoLookup):
    def __init__(self, cities: list[City]) -> None:
        self._cities = cities
        self._by_code = {c.cbsa_code: c for c in cities}
        self._by_city_state = {
            (pc.lower(), c.state): c
            for c in cities for pc in c.principal_cities
        }

    def find_by_city(self, city, state=None):
        if state:
            return self._by_city_state.get((city.lower(), state))
        return next((c for c in self._cities
                     if any(pc.lower() == city.lower() for pc in c.principal_cities)),
                    None)

    def all_metros(self) -> list[City]:
        return list(self._cities)
```

---

## 6. Mapbox→DFS bridge: write-through caching

Today (in `apps/admin/src/app/api/places/suggest/route.ts`):

```ts
// 1. Hit Mapbox for place suggestions
// 2. For each candidate, fetch DFS /serp/google/locations and string-match
// 3. Return [{place_id, dataforseo_location_code}, ...]
```

Add step 4: when a user selects a candidate that produced a successful DFS resolution, write back to `metros`:

```ts
// 4. Write-through: if cbsa_code resolved, persist place_id + DFS code
await supabase
  .from("metros")
  .update({
    place_id: chosen.place_id,
    place_id_resolved_at: new Date().toISOString(),
    dataforseo_location_codes: arrayUnion(
      existing.dataforseo_location_codes,
      [chosen.dataforseo_location_code]
    ),
  })
  .eq("cbsa_code", chosen.cbsa_code);
```

`arrayUnion` is a server-side function we'll write as a Postgres `update_metros_dfs_codes(cbsa_code, code)` RPC to avoid race conditions on the array column.

**Result:** the second user who searches for the same city pulls from `metros` directly via `find_by_place_id`, never hits Mapbox or DFS for resolution. Only the first lookup pays the cold cost.

---

## 7. Cutover plan

Five phases. Each is independently shippable.

### Phase 1 — Migration + new adapter (no callers yet)

- Apply `011_metros_place_id.sql`
- Add `src/data/supabase_metros_adapter.py` and `src/data/in_memory_geo_lookup.py`
- Add unit tests for both adapters using fixture-backed `InMemoryGeoLookup`
- No production code paths use the new adapter yet

**Gate:** unit tests pass; staging migration applied.

### Phase 2 — Wire orchestrator behind feature flag

- Add `WIDBY_GEO_BACKEND` env var: `seed` (default) or `supabase`
- Update `score_niche_for_metro` factory to instantiate the right adapter
- Add integration test: same scoring run with both backends produces the same `report_id` and metro signals (within DFS tolerance)

**Gate:** integration test passes against staging.

### Phase 3 — Flip default to `supabase` in staging

- Set `WIDBY_GEO_BACKEND=supabase` in staging .env
- Run smoke test against staging for one week — 50+ scoring runs across pop classes
- Monitor: no "metro not found" errors; latency within target

**Gate:** zero seed-specific failures over 7-day window.

### Phase 4 — Bridge write-through

- Update `places/suggest` route to write back resolved `place_id` + DFS code
- Add Postgres RPC `metros_add_dfs_code(cbsa_code, code)` for race-safe array updates
- Backfill: one-time script that resolves Mapbox place_ids for the 60 already-seeded metros and writes them in

**Gate:** for any city looked up twice, second lookup hits zero external APIs.

### Phase 5 — Delete the seed

- Remove `src/data/seed/cbsa_seed.json`
- Remove `src/data/metro_db.py` and `src/data/metro_db_adapter.py`
- Remove the `WIDBY_GEO_BACKEND` flag (only `supabase` remains)
- Update `CLAUDE.md` to reflect the new geo flow

**Gate:** no remaining imports of `MetroDB` anywhere; CI green.

---

## 8. File-by-file changes (Phase 1-2 scope)

| File | Action |
|---|---|
| `supabase/migrations/011_metros_place_id.sql` | Create — adds `place_id`, `place_id_resolved_at`, indexes |
| `src/data/supabase_metros_adapter.py` | Create — `SupabaseMetrosGeoLookup` |
| `src/data/in_memory_geo_lookup.py` | Create — test fixture adapter |
| `src/pipeline/orchestrator.py` | Modify — read `WIDBY_GEO_BACKEND`, choose adapter |
| `src/research_agent/api.py` | Modify — same factory swap |
| `tests/unit/test_supabase_metros_adapter.py` | Create — fixture-backed tests |
| `tests/unit/test_metro_db.py` | Keep as-is for one release; add deprecation note |
| `docs/data_flow.md` | Update — geo flow now starts at Supabase |
| `docs-canonical/DATA-MODEL.md` | Update — `metros` is authoritative |

| File (Phase 4-5) | Action |
|---|---|
| `apps/admin/src/app/api/places/suggest/route.ts` | Modify — write-through after successful resolution |
| `supabase/migrations/012_metros_rpc.sql` | Create — `metros_add_dfs_code` RPC |
| `scripts/backfill_metros_place_ids.py` | Create — one-time backfill of place_ids for seeded metros |
| `src/data/seed/cbsa_seed.json` | Delete |
| `src/data/metro_db.py` | Delete |
| `src/data/metro_db_adapter.py` | Delete |

---

## 9. Test strategy

- **Unit tests** use `InMemoryGeoLookup` with hand-built `City` fixtures. Zero network. Same shape as current tests.
- **Integration tests** use `SupabaseMetrosGeoLookup` against the staging project (or a docker'd Supabase). One test per port method.
- **Contract test** asserts `MetroDBGeoLookup` and `SupabaseMetrosGeoLookup` produce equivalent results for the 60 seeded metros — proves drop-in compatibility before flipping the flag.

---

## 10. Rollback

Each phase is independently revertible:

- Phase 1-2: feature flag defaults to `seed`. Just don't flip it.
- Phase 3: set `WIDBY_GEO_BACKEND=seed` in staging .env, restart. Behavior reverts.
- Phase 4: write-through is additive — disabling the writeback doesn't break reads.
- Phase 5 (seed deleted): rollback requires git revert + redeploy. By this point staging has had ≥ 1 week of `supabase` backend; if it failed we wouldn't reach Phase 5.

---

## 11. Open questions

1. **Alias resolution.** Coral types "Albany" and means "Albany, NY" — but the seed/metros has 3 Albanys (NY, GA, OR). Today the autocomplete forces a state suffix; should the adapter accept a fuzzy state-less query? Probable answer: NO — keep the state argument required to avoid silent miscoring.
2. **Mapbox quota.** Once we cache aggressively, our Mapbox quota use drops. Worth verifying we don't break the autocomplete by removing pre-emptive Mapbox calls. Probable answer: the autocomplete still calls Mapbox for typeahead; only the DFS resolution moves to cache.
3. **CBSA drift cadence.** Census redefines CBSAs roughly every 10 years (2013, 2023, 2033). Between vintages, individual CBSAs occasionally split/merge in mid-decade releases. We need a "metros refresh" job that re-syncs from ACS quarterly. Defer to V2.1.
4. **Multi-state metros (e.g., New York-Newark-Jersey City, NY-NJ-PA).** The `state` column today stores only the primary state. Lookups for "Newark" with `state="NJ"` need to match. The current fix is the principal_cities array, which already includes Newark. Verify in test.

---

## 12. References

- `docs/algo_spec_v2.md` — V2 scoring spec
- `supabase/migrations/010_v2_benchmarks.sql` — current `metros` schema
- `src/domain/ports.py` — `GeoLookup` protocol
- `src/data/seed/cbsa_seed.json` — the artifact being deprecated
- `apps/admin/src/app/api/places/suggest/route.ts` — Mapbox+DFS bridge
- SME call: Luke <> Henock <> Antwoine, 2026-04-26 ([Fireflies](https://app.fireflies.ai/view/01KQ5A4P91TCSXJ1YBYHJWFSX1))
