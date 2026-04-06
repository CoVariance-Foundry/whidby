# Research: Data Persistence Layer

**Branch**: `010-data-persistence-layer` | **Date**: 2026-04-06

## R1: Observation Store Integration with M0 Client

**Decision**: Inject an `ObservationStore` into `DataForSEOClient` that wraps the existing `ResponseCache` and `CostTracker` with persistent, Postgres-backed cache and Supabase Storage payload persistence.

**Rationale**: The client already has two internal write points (cache put + cost record) in both `_queued_request` and `_live_request`. The observation store replaces the in-memory `ResponseCache` for freshness checks and augments `CostTracker` with durable cost attribution. The `APIResponse` return type is unchanged — persistence is a transparent side effect.

**Alternatives considered**:
- Middleware wrapper around the client (rejected: duplicates cache-key logic, requires exposing internals)
- New client subclass (rejected: fragile coupling, Python MRO complications with async)
- Post-pipeline batch persistence (rejected: loses per-call granularity, no cache reuse mid-run)

## R2: Cache Key Strategy

**Decision**: Reuse the existing `ResponseCache._key()` hashing approach (SHA-256 of `{"endpoint": ..., **params}` sorted). Extract it into a shared `query_hash.py` module so both the in-memory fallback and the Postgres-backed observation store use the same deterministic key.

**Rationale**: The existing hash is already proven stable across the 10 M0 endpoints. The only change is excluding non-semantic fields (`tag`, `postback_url`, `pingback_url`) which the current cache already ignores by not including them in the params dict passed to `_key()`.

**Alternatives considered**:
- Separate hash per endpoint type (rejected: unnecessary complexity, no benefit)
- Include API version in hash (rejected: DataForSEO doesn't version endpoints in a way that changes response shape)

## R3: TTL Category Assignment

**Decision**: Map endpoints to TTL categories at the `Endpoint` definition level (in `endpoints.py`). Add a `ttl_category: str` field to the existing frozen `Endpoint` dataclass. The observation store reads the category from the endpoint and computes `expires_at = observed_at + TTL_DURATIONS[category]`.

**Rationale**: Endpoint → TTL mapping is stable and deterministic. Placing it on the `Endpoint` dataclass means no runtime inference is needed.

**Alternatives considered**:
- Caller-specified TTL per request (rejected: violates encapsulation, callers shouldn't know data freshness semantics)
- Response-based TTL from API headers (rejected: DataForSEO doesn't provide cache-control headers)

## R4: Supabase Storage for Payloads

**Decision**: Store gzipped JSON payloads in a Supabase Storage bucket (`observations/`). Path convention: `{endpoint_group}/{YYYY}/{MM}/{DD}/{query_hash}_{observation_id}.json.gz`. The observation index row holds `storage_path` as a pointer.

**Rationale**: DataForSEO responses can be 50KB–2MB. Storing them inline in Postgres JSONB would bloat the `observations` table and slow index scans. Supabase Storage provides cheap object storage with the same auth model.

**Alternatives considered**:
- Postgres JSONB column (rejected: row-size bloat, index performance)
- External S3 (rejected: adds infra dependency outside Supabase, complicates auth)
- Postgres TOAST (rejected: still affects table scan performance, harder to purge independently)

## R5: Benchmark Integration with M7 Scoring

**Decision**: Benchmark integration is **opt-in and deferred** from Phase 1. The observation store and canonical tables ship first. Benchmark-blended scoring (modifying `compute_demand_score` to blend `percentile_rank` with `get_benchmark()`) ships as a separate, flagged change in Phase 2.

**Rationale**: Constitution principle VI (simplicity, YAGNI) — the persistence layer must not change scoring output in Phase 1. FR-012 explicitly requires backward compatibility until benchmarks are explicitly enabled. Shipping persistence independently de-risks the refactor.

**Alternatives considered**:
- Ship everything at once (rejected: too much risk surface, scoring regression hard to attribute)
- Feature flag on benchmark blending (chosen for Phase 2: allows A/B comparison of relative-only vs. blended)

## R6: Canonical Metro vs. Existing metro_location_cache

**Decision**: The new `canonical_metros` table supersedes both `metro_location_cache` (from `003_shared_tables.sql`) and the in-memory `MetroDB.from_seed()` JSON file. It adds `region`, `population_year`, `population_growth_pct`, and `metro_size_tier` fields. `MetroDB` will read from the new table instead of the seed file, with the seed file retained as a fallback.

**Rationale**: The existing `metro_location_cache` has the right columns but lacks size-tier classification and growth data needed for benchmark stratification. Rather than bolting fields onto the existing table, a clean `canonical_metros` table with richer schema provides a stable foundation.

**Alternatives considered**:
- ALTER existing `metro_location_cache` (rejected: migration complexity, table is used in existing RLS policies)
- Keep both tables (rejected: data duplication, drift risk)

## R7: Anchor Runner Execution Environment

**Decision**: Anchor runner is a Supabase Edge Function triggered by `pg_cron`. It calls the M0 client (Python) via a thin FastAPI endpoint that the Edge Function invokes over HTTP.

**Rationale**: The M0 client is Python (`httpx`, `asyncio`). Supabase Edge Functions run Deno. Rather than rewriting M0 in TypeScript, the Edge Function acts as a scheduler that invokes a Python-side API endpoint for the actual data collection. This reuses all existing M0 logic including the write-through observation store.

**Alternatives considered**:
- Pure Python cron via external scheduler (rejected: requires separate infra, not in Supabase ecosystem)
- Rewrite M0 in TypeScript (rejected: massive duplication, loses existing test coverage)
- Supabase Database Functions (PL/pgSQL) calling `http_extension` (rejected: limited error handling, hard to debug)

## R8: Cold Start Batch Execution

**Decision**: Cold start runner is a Python script (`src/scripts/cold_start.py`) that reads a niche×metro matrix config and executes full pipeline runs in serial, with configurable concurrency and rate limiting. It uses the same M0 client and pipeline functions as normal runs.

**Rationale**: The cold start needs to run the full M4→M9 pipeline, which is all Python. A simple script with a matrix config and progress logging is the simplest approach. Rate limiting is handled by the existing M0 token-bucket limiter.

**Alternatives considered**:
- Parallel execution via task queue (rejected: premature for a one-time batch, adds Celery/Redis dependency)
- Supabase Edge Function (rejected: 60s timeout limit, Python ecosystem needed)
