# Project Context

## AI Review and Visual QA CI/CD

Added CI/CD review scaffolding for Greptile PR review policy, Playwright visual QA, optional Codex/Claude artifact critique, preview URL resolution, and environment manifest checks. The workflow keeps `dev -> main` as the release spine, uses preview/staging/production environment separation, and avoids printing or committing secret values.

Greptile review execution remains owned by the Greptile GitHub App and local Greptile MCP use in Cursor/Codex/Claude Code. PR `visual-qa` labels now create a no-secret request summary; the secret-bearing Visual QA run is maintainer-dispatched from `dev` or `main` with `workflow_dispatch`, validates the preview URL against the allowed HTTPS host list, and uses trusted checkout code so PR-controlled code does not receive Vercel, auth, GitHub, or agent credentials. Visual QA can post review JSON back to a PR when `pr_number` is supplied, and agent critique is capped by workflow and subprocess timeouts. Supabase preview branches require external Supabase GitHub/Vercel integration setup before manual Visual QA should be dispatched for schema-changing previews.

The env sync scripts are intentionally planning-only at this stage. Use the `env:plan:*` package scripts to audit required provider names; do not treat them as live sync/apply commands until provider write implementations are added.

## Phase 7 Benchmark and Sonar Slice-Lite

Phase 7 now has a staging-first benchmark recompute path. `public.recompute_seo_benchmarks(p_window_days integer)` rebuilds `seo_benchmarks` from `seo_facts`, ACS-backed `metros`, CBP-backed `census_cbp_establishments`, and weighted `niche_naics_mapping`; `scripts/benchmarks/recompute_benchmarks.py` calls that RPC through benchmark-specific Supabase env vars.

Benchmark collection is safer but not complete: `scripts/benchmarks/run_pilot.py` can run pilot or full-sample batches, rejects unknown niches/population classes before paid API calls, and captures top-three local-pack review metrics into `seo_facts`. Existing staging facts still need a paid rerun before review-floor benchmarks become populated.

Sonar slice-lite is implemented in staging through `sonar.cells`, `sonar.cell_runs`, `sonar.scoring_weights`, and the service-role-only `public.persist_sonar_slice_lite(p_record jsonb)` RPC. `scripts/sonar/build_slice_lite.py` builds the LA plumbing cell (`238220__msa__31080__2023`) from current Widby data and persists it with `score_version = sonar-lite-0.1` plus warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs.
