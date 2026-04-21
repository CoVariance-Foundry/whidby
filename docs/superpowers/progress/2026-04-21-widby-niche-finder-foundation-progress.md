# Widby Niche Finder Foundation — Progress

**Branch:** `015-niche-finder-product-v1`
**Worktree:** `.worktrees/015-niche-finder-product-v1`
**Date:** 2026-04-21

## Where to pick up

Resume at **Task B6** in the implementation plan. The next subagent dispatch was drafted but cancelled by the user; its brief (below) can be used as-is.

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

### Phase B — Home page (IN PROGRESS: 5 / 7 complete)

Implementation plan reference: "## Phase B — Home page"

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| B1 StatCardRow | ✅ | `118d66f` | Plan had a duplicate-"42" test bug; fixed in plan + test data |
| B2 HeroQuickSearch | ✅ | `106b35d` | |
| B3 RecommendedMetros | ✅ | `044ce5f` | |
| B4 RecentActivityFeed | ✅ | `7a30980` | |
| B5 SavedSearchesBlock | ✅ | `327a2bf` | |
| B6 loadDashboard loader | ⬜ | — | Next up. Pure server-side module that reads `reports` from Supabase and projects `stats / recent / recommended / stat_cards` for the Home page |
| B7 Home page assembly | ⬜ | — | Replaces the redirect stub at `apps/app/src/app/(protected)/page.tsx` with the full dashboard layout |

Cumulative vitest state after B1-B5:
- apps/app: 11 test files, 32 tests, all passing
- tsc: clean

### Phase C — Niche Finder command-center upgrade (NOT STARTED)

Four tasks:
- C1 NicheFinderTabs
- C2 StrategyPresetRail
- C3 PinnedRecentRail + `history-storage.ts`
- C4 Niche Finder page rewrite (Variation B layout)

### Phase D — Reports chip-filter re-skin (NOT STARTED)

Four tasks:
- D1 deriveArchetype helper
- D2 ArchetypeChipFilter
- D3 ReportsTable
- D4 Reports page rewrite + `ReportsPageClient.tsx`

### Phase E — Polish (NOT STARTED)

- E1 Playwright E2E for full Foundation flow
- E2 Refresh `apps/app/CLAUDE.md` with new topology

## Known issues / lessons learned

**Plan defects found in execution:**
1. **B1 test duplicate-42 bug** — `getByText("42")` failed because two stat cards rendered `42`. Fix applied to both the plan and the test file: changed `Reports: "42"` → `Reports: "38"` so both values are unique and testable. Remaining plan tasks have been skimmed for similar issues; watch for them during each task's "verify test fails → implement → verify test passes" cycle.

**Subagent scope violations to guard against:**
1. First B1-B5 dispatch (replaced by a fresh one) modified `apps/app/src/app/api/agent/scoring/route.ts` and its test unprompted — a drive-by "improvement" to add `state` propagation. Reverted manually. Subsequent dispatches were given a stricter scope boundary clause: "You may create files ONLY inside `apps/app/src/components/home/`. You may NOT modify any other file under any circumstance." That language worked for B2-B5.

**Convention reminders for subagents:**
- Never use `[docs-sync-skip]` on this branch (the repo CLAUDE.md now forbids it outright).
- Use explicit `git add <path>` — never `git add -A`.
- Commit messages: exactly as the plan specifies for each task's Step 5.

## Next subagent brief (ready to dispatch)

This was the prompt drafted for Tasks B6 + B7, to paste into the next subagent-driven-development dispatch when ready:

> You are implementing Tasks B6 and B7 of the Widby Niche Finder Foundation plan. B6 is the Supabase-backed dashboard loader; B7 assembles the Home page that stitches together components B1-B5 plus the B6 loader.
>
> **Working directory:** `/Users/antwoineflowers/development/rankrent/nichefinder/main/.worktrees/015-niche-finder-product-v1`
>
> **Plan:** `docs/superpowers/plans/2026-04-21-widby-niche-finder-foundation.md` — scroll to "### Task B6" and work through B6 → B7 in order.
>
> **Per task:** write test verbatim from the plan, run it to confirm failure, write component verbatim, run to confirm pass, commit exactly as the plan's Step 5 specifies.
>
> **Scope boundary:**
> - CREATE only inside `apps/app/src/lib/home/`.
> - MODIFY only `apps/app/src/app/(protected)/page.tsx`.
> - Any other file is off-limits — report BLOCKED rather than touch it.
>
> **Potential issue to watch:** B6's test mocks the Supabase client chain. Look at the fake-client shape before committing — if the mock shape and the `loadDashboard` implementation call-chain mismatch, report BLOCKED with the specific shape drift. Do not "fix" the test to match.
>
> **Conventions:** no `[docs-sync-skip]`; explicit `git add <path>`; verbatim commit messages.

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
