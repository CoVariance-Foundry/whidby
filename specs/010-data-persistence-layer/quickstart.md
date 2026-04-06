# Quickstart: Data Persistence Layer

**Branch**: `010-data-persistence-layer` | **Date**: 2026-04-06

## Prerequisites

- Python 3.11+
- Supabase project with Storage enabled
- Environment variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`

## 1. Apply Migrations

```bash
supabase db push
```

New migrations (in order):
- `005_observation_store.sql` — `observations` table + indexes
- `006_canonical_reference.sql` — `canonical_metros`, `canonical_benchmarks`, `canonical_niches`
- `007_anchor_system.sql` — `anchor_configs`, `anchor_runs`, `signal_snapshots`
- `008_observation_rls.sql` — RLS policies for new tables

## 2. Create Storage Bucket

```bash
# Via Supabase CLI or dashboard
supabase storage create observations --public=false
```

## 3. Run Tests

```bash
# Unit tests (no network, no API keys needed)
pytest tests/unit/test_observation_store.py -v
pytest tests/unit/test_query_hash.py -v
pytest tests/unit/test_benchmark_resolver.py -v

# Integration tests (requires API keys)
pytest tests/integration/test_m0_write_through.py -v -m integration
```

## 4. Verify Pipeline Compatibility

Run the existing M5→M9 pipeline with the refactored M0 client and confirm
identical scoring output:

```bash
pytest tests/integration/test_pipeline_regression.py -v -m integration
```

## 5. Seed Canonical Data (Phase 2)

```bash
# Seed metros from census data
python -m src.scripts.seed_canonical_metros

# Seed niche taxonomy (20 target niches)
python -m src.scripts.seed_canonical_niches

# Seed external benchmarks
python -m src.scripts.seed_external_benchmarks
```

## 6. Cold Start (Phase 2)

```bash
# Run 100 simulated pipeline executions
python -m src.scripts.cold_start --matrix configs/cold_start_matrix.json --batch-size 20

# Compute benchmarks from simulation data
python -m src.scripts.compute_benchmarks
```

## 7. Enable Anchors (Phase 3)

```bash
# Auto-configure anchors for cold-start niches
python -m src.scripts.seed_anchors --from-cold-start

# Set up pg_cron schedule (via Supabase dashboard or migration)
# Schedule: every hour, invoke anchor-runner Edge Function
```

## Key Files

| File | Purpose |
|------|---------|
| `src/clients/dataforseo/observation_store.py` | Observation persistence + cache lookup |
| `src/clients/dataforseo/query_hash.py` | Deterministic query hash computation |
| `src/clients/dataforseo/client.py` | Refactored M0 client (write-through) |
| `src/canonical/benchmark_resolver.py` | Benchmark priority chain (computed > external > stale) |
| `src/canonical/benchmark_compute.py` | Weekly benchmark computation job |
| `src/anchor/runner.py` | Anchor data collection executor |
| `src/anchor/snapshot_extractor.py` | Signal snapshot derivation from observations |
| `src/scripts/cold_start.py` | Cold start batch executor |
| `supabase/migrations/005_observation_store.sql` | Observation table DDL |
| `supabase/migrations/006_canonical_reference.sql` | Canonical tables DDL |
| `supabase/migrations/007_anchor_system.sql` | Anchor system DDL |
