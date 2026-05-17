# Project Context

## AI Review and Visual QA CI/CD

Added CI/CD review scaffolding for Greptile PR review policy, Playwright visual QA, optional Codex/Claude artifact critique, preview URL resolution, Supabase preview readiness waits, and environment manifest checks. The workflow keeps `dev -> main` as the release spine, uses preview/staging/production environment separation, and avoids printing or committing secret values.

Greptile review execution remains owned by the Greptile GitHub App and local Greptile MCP use in Cursor/Codex/Claude Code. PR `visual-qa` labels now create a no-secret request summary; the secret-bearing Visual QA run is maintainer-dispatched with `workflow_dispatch` and a `preview_url` so PR-controlled code does not receive Vercel, auth, GitHub, or agent credentials. Supabase preview branches require external Supabase GitHub/Vercel integration setup before the `Supabase Preview` wait can pass.

## Phase 7 Benchmark and Sonar Slice-Lite

Phase 7 now has a staging-first benchmark recompute path. `public.recompute_seo_benchmarks(p_window_days integer)` rebuilds `seo_benchmarks` from `seo_facts`, ACS-backed `metros`, CBP-backed `census_cbp_establishments`, and weighted `niche_naics_mapping`; `scripts/benchmarks/recompute_benchmarks.py` calls that RPC through benchmark-specific Supabase env vars.

Benchmark collection is safer but not complete: `scripts/benchmarks/run_pilot.py` can run pilot or full-sample batches, rejects unknown niches/population classes before paid API calls, and captures top-three local-pack review metrics into `seo_facts`. Existing staging facts still need a paid rerun before review-floor benchmarks become populated.

Sonar slice-lite is implemented in staging through `sonar.cells`, `sonar.cell_runs`, `sonar.scoring_weights`, and the service-role-only `public.persist_sonar_slice_lite(p_record jsonb)` RPC. `scripts/sonar/build_slice_lite.py` builds the LA plumbing cell (`238220__msa__31080__2023`) from current Widby data and persists it with `score_version = sonar-lite-0.1` plus warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs.
