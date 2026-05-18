# Active Work

## Supabase Staging Auth and Entitlements

Status: staging schema and seeded personas verified; GitHub Environment secret upload still requires explicit user approval.

Completed:

- Added `018_internal_user_entitlements.sql` for service-role-managed quota exemptions, `ensure_account_for_user_admin(...)`, and `get_account_entitlement()` with `fresh_report_quota_exempt`.
- App fresh-report gates now allow internal quota-exempt admins to run fresh scoring/strategy/onboarding city reports without consuming monthly report quota.
- Added migration parity and seed scripts under `scripts/supabase/`.
- Added GitHub Actions workflows for staging migration deploys and manual test-account seeding from the `staging` Environment.
- Applied staging migrations `014_user_management_billing` through `018_internal_user_entitlements` to Supabase project `whidby-staging` (`wuybidpvqhhgkukpyyhq`).
- Seeded staging Auth/account entitlements for `admin-test@widby.dev`, `user-test@widby.dev`, `henock@covariance.studio`, `antwoine@covariance.studio`, and `lm13vand@gmail.com`.
- Stored seed passwords locally in the repo-root `.env`; do not commit or print them.

Verified:

- Staging migration ledger includes `014_user_management_billing`, `015_explore_refresh_control`, `016_consumer_onboarding`, `017_strategy_discovery_system`, and `018_internal_user_entitlements`.
- Staging SQL verification shows `admin-test`, Henock, and Antwoine are `admin`/`free`/quota-exempt; Luke is `owner`/`pro`/non-exempt; normal test user is `owner`/`free`/non-exempt.
- Password-auth smoke passes for all five seeded users when using the valid staging service-role API key.

Current blockers:

- GitHub `staging` Environment secrets were not uploaded from Codex because the escalation reviewer rejected transmitting service-role and password secrets to GitHub without explicit user approval.
- Local `.env` value `STAGING_NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` appears invalid for `whidby-staging`; browser/client login will fail until the staging publishable key is refreshed in local env and Vercel Preview env.

## CI/CD AI Review and Visual QA

- CI/CD AI review and visual QA workflow implementation is complete on `codex/ai-review-visual-qa-cicd` and in closeout review.
- Plan: `docs/superpowers/plans/2026-05-17-ai-review-visual-qa-cicd.md`
- Next: merge after Greptile follow-up fixes land and hosted checks pass; then dispatch Visual QA from `dev` or `main` with `preview_url` and `pr_number`.

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
