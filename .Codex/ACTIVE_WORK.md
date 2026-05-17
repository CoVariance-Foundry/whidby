# Active Work

## Active Work

- CI/CD AI review and visual QA workflow implementation.
- Plan: `docs/superpowers/plans/2026-05-17-ai-review-visual-qa-cicd.md`
- Next: implement MCP config, env manifest, visual QA scripts, and GitHub workflows in separate reviewed commits.

## Prior/Archived Context

## Phase 7 Benchmark Completion

Status: closeout validation.

Completed: staging benchmark recompute path, benchmark runner controls, Sonar slice-lite persistence, and LA plumbing slice-lite staging record.

Latest update: paid benchmark sampling is pruned to DFS-native, keyword-volume-capable metros by default. Filtered full-sample launch scope is 60 metros (9 mega, 37 metro, 12 large, 2 medium); small/micro metros stay census-only unless `--include-low-signal` is used for diagnostics. A 2026-05-12 live preflight for plumber + concrete contractor succeeded 10/10 with zero Supabase writes; New York now keeps separate validated `keyword_volume_location_codes` to avoid a known invalid volume code.

Current blockers before production:

- Paid DataForSEO full-sample collection has not been run with the new review-floor fields.
- Staging benchmark confidence remains below usable coverage: 43 insufficient cells, 12 low cells, 0 medium/high cells after the latest recompute.
- Production promotion requires explicit approval and a staging health review.

Next implementation slice: V2 scoring should read `seo_benchmarks` through a repository boundary instead of ad hoc Supabase queries.
