# Widby Niche Finder Foundation — Progress

**Branch:** `015-niche-finder-product-v1`
**Worktree:** `.worktrees/015-niche-finder-product-v1`
**Date:** 2026-04-21

## Status: COMPLETE

All Foundation phases (A through E) are implemented, tested, and committed. Branch is ready for review/merge.

## Post-completion operational update

- **2026-04-22:** Production Render env updated with `MAPBOX_ACCESS_TOKEN` for FastAPI `/api/places/suggest`. Verified end-to-end autocomplete behavior for small cities (Tuskegee, AL and Macon, GA) in consumer `/niche-finder`.

## References

- **Design spec:** [docs/superpowers/specs/2026-04-21-widby-niche-finder-v1-design.md](../specs/2026-04-21-widby-niche-finder-v1-design.md)
- **Implementation plan:** [docs/superpowers/plans/2026-04-21-widby-niche-finder-foundation.md](../plans/2026-04-21-widby-niche-finder-foundation.md)
- **Design bundle (visual source of truth):** [docs/designs/widby-niche-finder-v1/project/lib/](../../designs/widby-niche-finder-v1/project/lib/)

## Phases

### Phase A — Foundation integration (DONE)

Merges + baseline on `015-niche-finder-product-v1`:

- `f99029e` Merge 013-niche-operational-wiring (backend scoring, Supabase persistence, FastAPI `/api/niches/*`, `/api/metros/suggest`, admin wiring)
- `027b93c` Merge 014-consumer-niche-finder-wiring (consumer scaffolding — niche-finder page, reports SSR, proxies, RLS migration 005, CityAutocomplete)
- `3964526` fix(app): wire `@testing-library/jest-dom` types into tsconfig (baseline-green fix for apps/app tsc)
- `3331c8b` Landed design spec + design bundle

Baseline green:
- Python: 298 / 298 (ruff clean)
- apps/app vitest: 24 / 24 (tsc clean)
- apps/admin vitest: 35 / 35 (tsc clean)

### Phase B — Home page (DONE: 7 / 7)

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| B1 StatCardRow | ✅ | `118d66f` | Plan had a duplicate-"42" test bug; fixed in plan + test data |
| B2 HeroQuickSearch | ✅ | `106b35d` | |
| B3 RecommendedMetros | ✅ | `044ce5f` | |
| B4 RecentActivityFeed | ✅ | `7a30980` | |
| B5 SavedSearchesBlock | ✅ | `327a2bf` | |
| B6 loadDashboard loader | ✅ | `40a0545` | Fixed mock chain bug (limit→resolvedValue, not limit→order→resolvedValue) |
| B7 Home page assembly | ✅ | `1c2b587` | Adjusted Sidebar/Topbar props to match actual signatures (active/crumbs) |

### Phase C — Niche Finder command-center upgrade (DONE: 4 / 4)

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| C1 NicheFinderTabs | ✅ | `bd40543` | |
| C2 StrategyPresetRail | ✅ | `39afa9f` | |
| C3 PinnedRecentRail + history-storage | ✅ | `3494197` | Fixed pushRecent cap test — needed unique city/service combos due to dedup |
| C4 Niche Finder page rewrite | ✅ | `9331f0e` | Preserved existing CityAutocomplete onChange signature + validation API |

### Phase D — Reports chip-filter re-skin (DONE: 4 / 4)

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| D1 deriveArchetype | ✅ | `23678b4` | |
| D2 ArchetypeChipFilter | ✅ | `4ea3f8a` | |
| D3 ReportsTable | ✅ | `a1906c3` | |
| D4 Reports page rewrite | ✅ | `9adabcf` | Split into server component + ReportsPageClient |

### Phase E — Polish (DONE: 2 / 2)

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| E1 Playwright E2E | ✅ | `1545c6d` | Spec only (not run — needs dev server + auth) |
| E2 CLAUDE.md refresh | ✅ | — | Already up to date from earlier commit |

## Known issues / lessons learned

**Plan defects found in execution:**
1. **B1 test duplicate-42 bug** — `getByText("42")` failed because two stat cards rendered `42`. Fix applied to both the plan and the test file: changed `Reports: "42"` → `Reports: "38"` so both values are unique and testable. Remaining plan tasks have been skimmed for similar issues; watch for them during each task's "verify test fails → implement → verify test passes" cycle.

**Subagent scope violations to guard against:**
1. First B1-B5 dispatch (replaced by a fresh one) modified `apps/app/src/app/api/agent/scoring/route.ts` and its test unprompted — a drive-by "improvement" to add `state` propagation. Reverted manually. Subsequent dispatches were given a stricter scope boundary clause: "You may create files ONLY inside `apps/app/src/components/home/`. You may NOT modify any other file under any circumstance." That language worked for B2-B5.

**Convention reminders for subagents:**
- Never use `[docs-sync-skip]` on this branch (the repo CLAUDE.md now forbids it outright).
- Use explicit `git add <path>` — never `git add -A`.
- Commit messages: exactly as the plan specifies for each task's Step 5.

## Final verification

```
apps/app: tsc ✅ | vitest 19 files, 56 tests ✅
apps/admin: tsc ✅ | vitest 9 files, 35 tests ✅
```

## Commands reference

From the worktree root:

```bash
# Baseline checks (should all be green before + after each task)
pytest tests/unit/ -q --tb=no
ruff check src/ tests/
cd apps/app && npx tsc --noEmit && npx vitest run
cd ../admin && npx tsc --noEmit && npx vitest run

# Playwright E2E (not needed until Task E1)
cd apps/app && NEXT_PUBLIC_NICHE_DRY_RUN=1 npx playwright test e2e/niche-foundation.spec.ts
```
