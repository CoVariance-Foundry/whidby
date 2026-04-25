# Niche Finder Autocomplete → Scoring Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Diagnose and fix the niche finder autocomplete-to-scoring pipeline that returns a user-visible error after city selection + submit.

**Architecture:** The bug lives somewhere in a 4-hop chain: CityAutocomplete (React) → `/api/agent/places/suggest` (Next.js proxy) → FastAPI `/api/places/suggest` (Mapbox + DFS bridge) → `/api/agent/scoring` (Next.js proxy) → FastAPI `/api/niches/score` (orchestrator). Five candidate failure paths were identified; Phase 1 diagnoses which path is active, Phase 2 fixes it.

**Tech Stack:** Next.js 16 (App Router), FastAPI, Python 3.11+, Mapbox Geocoding API, DataForSEO API, Supabase, Playwright (E2E)

> **IMPORTANT — Unconfirmed hypothesis.** The lead hypothesis (Path B → C) is based on code analysis + a known-broken E2E test, NOT on live reproduction. **You MUST complete Phase 1 (Task 1) and confirm which failure path is active before executing any Phase 2 task (Tasks 2–7).** If Phase 1 reveals a different path, see the routing table at the bottom of this plan.

---

## Investigation Summary

The user reports "no report generated" after using the niche finder city autocomplete. That exact string does not exist in the codebase. The three actual error messages the user could be seeing are:

| Message | Source | Trigger |
|---------|--------|---------|
| `"Scoring engine did not return a result."` | `apps/app/src/app/api/agent/scoring/route.ts:58` | FastAPI returned non-2xx status |
| `"Scoring unavailable (HTTP {n}). Try again shortly."` | `apps/app/src/app/(protected)/niche-finder/NicheFinderClient.tsx:156` | JSON parse failure or non-success status |
| `"Full report not yet available."` | `apps/app/src/app/(protected)/niche-finder/NicheFinderClient.tsx:411` | Success response but `report_id` is null |

### Five Candidate Failure Paths

| Path | Where it breaks | Root cause | Symptom |
|------|----------------|------------|---------|
| **A: Autocomplete proxy unreachable** | `/api/agent/places/suggest` proxy | `NEXT_PUBLIC_API_URL` not set on Vercel for consumer app, or FastAPI down | Autocomplete dropdown never appears; user types freely then scoring fails |
| **B: Metadata cleared after selection** | `CityAutocomplete` → `handleInputChange` | Any keystroke after selecting clears `state`, `place_id`, `dataforseo_location_code` (documented in E2E test `autocomplete-scoring-flow.spec.ts:246-329`) | Scoring submits bare city string without DFS code or state |
| **C: City resolution fails in orchestrator** | `src/pipeline/orchestrator.py:104` | City not in CBSA seed, no DFS code, no state → `ValueError("no CBSA match")` → 400 | "Scoring engine did not return a result." |
| **D: Pipeline exception (DFS/LLM)** | `src/pipeline/orchestrator.py` M4–M9 | DataForSEO or Anthropic API credentials missing, quota exceeded, or network failure → 500 | "Scoring engine did not return a result." |
| **E: Persistence failure with null report_id** | `src/research_agent/api.py:516-522` | `_persist_report` throws AND `result.report.get("report_id")` is None → response has null `report_id` | Score card shows but "Full report not yet available." |

**Lead hypothesis:** Path B → C chain. User selects from autocomplete (metadata attached), then makes any edit (even a space), which clears metadata. Submission hits orchestrator with bare city string, city isn't in CBSA seed, no state fallback available → `ValueError`. The E2E test at `apps/app/e2e/autocomplete-scoring-flow.spec.ts:246-329` explicitly asserts this buggy behavior exists.

---

## Phase 1: Diagnose (confirm which path is active)

### Task 1: Verify FastAPI reachability from consumer app

**Files:**
- Read: `apps/app/src/app/api/agent/scoring/route.ts:4` (API_BASE default)
- Read: `apps/app/src/app/api/agent/places/suggest/route.ts:3` (API_BASE default)

- [ ] **Step 1: Check if NEXT_PUBLIC_API_URL is set locally**

```bash
# From repo root
grep -r "NEXT_PUBLIC_API_URL" .env .env.local apps/app/.env apps/app/.env.local 2>/dev/null
```

Expected: Find the var set to `https://whidby-1.onrender.com` (production) or `http://localhost:8000` (local dev).
If NOT found: This is a strong signal for Path A.

- [ ] **Step 2: Check Vercel env vars for the consumer app project**

```bash
# If Vercel CLI is installed:
cd apps/app && vercel env ls
# Otherwise: check Vercel dashboard → project "whidby" or consumer app project → Settings → Environment Variables
```

Verify `NEXT_PUBLIC_API_URL` exists for Preview and Production environments.
If missing: **Path A confirmed.** The proxy routes default to `http://localhost:8000` which doesn't exist on Vercel.

- [ ] **Step 3: Verify FastAPI health**

```bash
curl -s https://whidby-1.onrender.com/health
# Expected: {"status":"ok"}
```

If it fails or returns error: **Path D likely** (FastAPI service is down).

- [ ] **Step 4: Test autocomplete endpoint directly**

```bash
curl -s "https://whidby-1.onrender.com/api/places/suggest?q=Phoenix&limit=5" | python3 -m json.tool
```

Expected: Array of `PlaceSuggestion` objects with `city`, `region`, `country`, and optionally `dataforseo_location_code`.
If 503: `MAPBOX_ACCESS_TOKEN` not set on Render → **Path A variant**.
If 502: Mapbox API failure → **Path A variant**.
Check if `dataforseo_location_code` is present on results. If missing on all results: DFS bridge is failing silently.

- [ ] **Step 5: Test scoring endpoint directly**

```bash
# With metadata (should succeed)
curl -s -X POST https://whidby-1.onrender.com/api/niches/score \
  -H "Content-Type: application/json" \
  -d '{"niche":"roofing","city":"Phoenix","state":"AZ","dry_run":true}' | python3 -m json.tool

# Without metadata (might fail for non-CBSA cities)
curl -s -X POST https://whidby-1.onrender.com/api/niches/score \
  -H "Content-Type: application/json" \
  -d '{"niche":"roofing","city":"Tuskegee","dry_run":true}' | python3 -m json.tool
```

First should succeed. If second returns 400 with "no CBSA match": **Path C confirmed** for non-CBSA cities.

- [ ] **Step 6: Reproduce in browser with Network tab open**

1. Open consumer app `/niche-finder`
2. Open browser DevTools → Network tab
3. Type a city in the autocomplete field
4. Note: Does `/api/agent/places/suggest` fire? What status? What response?
5. Select a suggestion from the dropdown
6. Type one more character in the city field (triggers metadata clear)
7. Click "Score niche"
8. Note: What does `/api/agent/scoring` POST body contain? Does it have `state`, `place_id`, `dataforseo_location_code`?
9. What status code and response body does the scoring request return?

This step confirms exactly which path is active. Record the findings before proceeding.

---

## Phase 2: Fix (execute based on Phase 1 diagnosis)

### Task 2: Fix Path A — Missing NEXT_PUBLIC_API_URL on consumer Vercel project

**Condition:** Only execute if Phase 1 Step 2 confirmed the env var is missing.

**Files:**
- Create: `apps/app/.env.local` (local dev convenience, gitignored)

- [ ] **Step 1: Add env var to Vercel**

```bash
# Via Vercel CLI (install first if needed: npm i -g vercel)
cd apps/app
vercel env add NEXT_PUBLIC_API_URL
# Enter value: https://whidby-1.onrender.com
# Select environments: Production, Preview, Development
```

Or manually in Vercel dashboard → consumer app project → Settings → Environment Variables.

- [ ] **Step 2: Create local .env.local for dev**

```bash
# apps/app/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 3: Verify .env.local is gitignored**

```bash
grep ".env.local" .gitignore
# Expected: .env.local is listed
```

- [ ] **Step 4: Redeploy and verify**

```bash
vercel deploy --prod
# Then test autocomplete + scoring on the production URL
```

- [ ] **Step 5: Commit**

```bash
git add apps/app/.env.local
git commit -m "fix(app): add NEXT_PUBLIC_API_URL for consumer scoring proxy"
```

---

### Task 3: Fix Path B → C — Metadata cleared after autocomplete selection

**Condition:** Execute if Phase 1 Step 6 confirmed metadata is cleared when typing after selection. This is the lead hypothesis.

**Files:**
- Modify: `apps/app/src/components/niche-finder/CityAutocomplete.tsx:100-104`
- Modify: `apps/admin/src/components/niche-finder/CityAutocomplete.tsx` (mirror — same change)
- Test: `apps/app/e2e/autocomplete-scoring-flow.spec.ts`

The core bug is in `handleInputChange` (line 100-104 of CityAutocomplete.tsx):

```tsx
const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    onChange(q);          // <-- calls parent with NO suggestion, which clears all metadata
    fetchSuggestions(q);
};
```

When the user types after selecting a suggestion, `onChange(q)` is called without a suggestion object. In the parent `NicheFinderClient.handleCityChange`, the `else` branch clears `state`, `placeId`, and `dataforseoLocationCode`. This is correct behavior (typing means the selection is invalidated) — but the problem is that submitting with ONLY a city string and no metadata causes the orchestrator to fail for non-CBSA cities.

**Fix strategy:** Two complementary changes:
1. **CityAutocomplete:** Track whether the current value came from a selection. Show a visual indicator (e.g., the formatted "City, ST" stays visible). If the user edits, properly clear and re-fetch — this behavior is actually correct.
2. **Orchestrator fallback:** When no `state` or `dataforseo_location_code` is provided, try to parse "City, ST" format from the city string as a last resort before raising ValueError.

- [ ] **Step 1: Write failing test for orchestrator city-state parsing fallback**

Create `tests/unit/test_orchestrator_city_parsing.py`:

```python
"""Test that the orchestrator can parse 'City, ST' format when state is not provided separately."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.pipeline.orchestrator import score_niche_for_metro


@pytest.mark.asyncio
async def test_city_with_comma_state_parsed():
    """When city='Phoenix, AZ' and state=None, orchestrator should parse state from city string."""
    with patch("src.pipeline.orchestrator.MetroDB") as MockMetroDB:
        mock_db = MagicMock()
        mock_metro = MagicMock()
        mock_metro.cbsa_code = "38060"
        mock_metro.cbsa_name = "Phoenix-Mesa-Chandler, AZ"
        mock_metro.state = "AZ"
        mock_metro.population = 4900000
        mock_metro.principal_cities = ["Phoenix"]
        mock_metro.dataforseo_location_codes = [1012873]
        mock_db.find_by_city.return_value = mock_metro
        MockMetroDB.from_seed.return_value = mock_db

        result = await score_niche_for_metro(
            niche="roofing",
            city="Phoenix, AZ",
            state=None,
            llm_client=None,
            dataforseo_client=None,
            dry_run=True,
        )

        # Should have parsed "AZ" from the city string and searched with just "Phoenix"
        mock_db.find_by_city.assert_called()
        call_args = mock_db.find_by_city.call_args
        # First positional arg should be the cleaned city name
        assert call_args[0][0] == "Phoenix"


@pytest.mark.asyncio
async def test_city_with_comma_state_no_cbsa_uses_state_fallback():
    """When city='Tuskegee, AL' (not in CBSA) and state parsed from string,
    should use state-level DFS fallback."""
    with patch("src.pipeline.orchestrator.MetroDB") as MockMetroDB:
        mock_db = MagicMock()
        # First call with parsed city returns None (not in CBSA)
        mock_db.find_by_city.return_value = None

        # State-level fallback: return a donor metro from AL
        donor_metro = MagicMock()
        donor_metro.cbsa_code = "13820"
        donor_metro.cbsa_name = "Birmingham-Hoover, AL"
        donor_metro.state = "AL"
        donor_metro.population = 1100000
        donor_metro.dataforseo_location_codes = [1012853]
        mock_db.all_metros.return_value = [donor_metro]
        MockMetroDB.from_seed.return_value = mock_db

        result = await score_niche_for_metro(
            niche="roofing",
            city="Tuskegee, AL",
            state=None,
            llm_client=None,
            dataforseo_client=None,
            dry_run=True,
        )

        assert result.opportunity_score is not None


@pytest.mark.asyncio
async def test_city_with_comma_and_explicit_state_strips_suffix():
    """When city='Phoenix, AZ' AND state='AZ' (both provided — e.g., after Task 4 display fix),
    the comma suffix should be stripped from city before MetroDB lookup."""
    with patch("src.pipeline.orchestrator.MetroDB") as MockMetroDB:
        mock_db = MagicMock()
        mock_metro = MagicMock()
        mock_metro.cbsa_code = "38060"
        mock_metro.cbsa_name = "Phoenix-Mesa-Chandler, AZ"
        mock_metro.state = "AZ"
        mock_metro.population = 4900000
        mock_metro.principal_cities = ["Phoenix"]
        mock_metro.dataforseo_location_codes = [1012873]
        mock_db.find_by_city.return_value = mock_metro
        MockMetroDB.from_seed.return_value = mock_db

        result = await score_niche_for_metro(
            niche="roofing",
            city="Phoenix, AZ",
            state="AZ",  # explicit state AND comma in city
            llm_client=None,
            dataforseo_client=None,
            dry_run=True,
        )

        # Should have stripped ", AZ" from city and searched with just "Phoenix"
        call_args = mock_db.find_by_city.call_args
        assert call_args[0][0] == "Phoenix"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_orchestrator_city_parsing.py -v
```

Expected: FAIL — orchestrator does not parse "City, ST" format.

- [ ] **Step 3: Implement city-state parsing in orchestrator**

Modify `src/pipeline/orchestrator.py`. Add parsing logic at line ~62 (after `resolved_state` is set, before the `if dataforseo_location_code` branch):

```python
import re

# ... existing code up to line 64 ...
    resolved_state = state.strip().upper() if isinstance(state, str) and state.strip() else None

    # Always strip "City, ST" suffix — city may arrive formatted even when state is set separately
    parsed_city = city.strip()
    match = re.match(r"^(.+),\s*([A-Za-z]{2})$", parsed_city)
    if match:
        parsed_city = match.group(1).strip()
        if not resolved_state:
            resolved_state = match.group(2).strip().upper()
        logger.info(
            "Stripped state suffix from city string: city=%r state=%r (original=%r)",
            parsed_city, resolved_state, city,
        )
```

Then update all downstream references from `city` to `parsed_city` within the function:
- Line 67: `synthetic_code` uses `parsed_city`
- Line 70: `cbsa_name` uses `parsed_city`
- Line 73: `principal_cities` uses `parsed_city`
- Line 77: `find_by_city(parsed_city, state=resolved_state)`
- Line 94: synthetic_code uses `parsed_city`
- Line 97: `cbsa_name` uses `parsed_city`
- Line 100: `principal_cities` uses `parsed_city`
- Line 104: error message uses both `parsed_city` and original `city`

Full replacement for lines 62-104:

```python
    metros_db = metro_db or MetroDB.from_seed()
    target: Metro | None = None
    resolved_state = state.strip().upper() if isinstance(state, str) and state.strip() else None

    parsed_city = city.strip()
    match = re.match(r"^(.+),\s*([A-Za-z]{2})$", parsed_city)
    if match:
        parsed_city = match.group(1).strip()
        if not resolved_state:
            resolved_state = match.group(2).strip().upper()
        logger.info(
            "Stripped state suffix from city string: city=%r state=%r (original=%r)",
            parsed_city, resolved_state, city,
        )

    if isinstance(dataforseo_location_code, int) and dataforseo_location_code > 0:
        synthetic_code = f"mapbox:{place_id}" if place_id else f"manual:{parsed_city.lower().replace(' ', '-')}"
        target = Metro(
            cbsa_code=synthetic_code,
            cbsa_name=parsed_city if not resolved_state else f"{parsed_city}, {resolved_state}",
            state=resolved_state or "",
            population=0,
            principal_cities=[parsed_city],
            dataforseo_location_codes=[dataforseo_location_code],
        )
    else:
        target = metros_db.find_by_city(parsed_city, state=resolved_state)
        if target is None and resolved_state:
            state_metros = [
                m for m in metros_db.all_metros()
                if m.state == resolved_state and m.dataforseo_location_codes
            ]
            if state_metros:
                state_metros.sort(key=lambda m: m.population, reverse=True)
                donor = state_metros[0]
                logger.warning(
                    "City %r not in CBSA seed; falling back to state-level DFS code "
                    "from %s (code=%d) for state=%s",
                    parsed_city, donor.cbsa_name,
                    donor.dataforseo_location_codes[0], resolved_state,
                )
                synthetic_code = f"mapbox:{place_id}" if place_id else f"fallback:{parsed_city.lower().replace(' ', '-')}"
                target = Metro(
                    cbsa_code=synthetic_code,
                    cbsa_name=f"{parsed_city}, {resolved_state}",
                    state=resolved_state,
                    population=0,
                    principal_cities=[parsed_city],
                    dataforseo_location_codes=donor.dataforseo_location_codes[:1],
                )
        if target is None:
            raw = f" (raw input: {city!r})" if parsed_city != city.strip() else ""
            raise ValueError(f"no CBSA match for city={parsed_city!r} state={resolved_state!r}{raw}")
        if not resolved_state:
            resolved_state = target.state
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_orchestrator_city_parsing.py -v
```

Expected: PASS

- [ ] **Step 5: Run full unit test suite for regressions**

```bash
pytest tests/unit/ -v
```

Expected: All existing tests still pass.

- [ ] **Step 6: Commit orchestrator fix**

```bash
git add src/pipeline/orchestrator.py tests/unit/test_orchestrator_city_parsing.py
git commit -m "fix(orchestrator): parse 'City, ST' format when state not provided separately"
```

---

### Task 4: Fix Path B — Preserve metadata display in CityAutocomplete

**Condition:** Execute after Task 3. This is a UX improvement that prevents the metadata-clearing problem at the source.

**Files:**
- Modify: `apps/app/src/components/niche-finder/CityAutocomplete.tsx`
- Modify: `apps/admin/src/components/niche-finder/CityAutocomplete.tsx` (mirror)

The fix: after a suggestion is selected, display the formatted "City, ST" text and treat further typing as a new search that clears the old selection (current behavior). But add a `import re` to orchestrator as defense-in-depth (done in Task 3).

The real UX fix is to show the selected suggestion as the display value so the user sees "Phoenix, AZ" in the input and is less likely to edit it. Currently `setCity(suggestion.city)` sets the value to "Phoenix" (without state), which may prompt the user to type ", AZ" manually — triggering metadata loss.

- [ ] **Step 1: Update handleCityChange to display formatted suggestion**

In `apps/app/src/app/(protected)/niche-finder/NicheFinderClient.tsx`, change `handleCityChange`:

```tsx
  const handleCityChange = (newCity: string, suggestion?: PlaceSuggestion) => {
    if (suggestion) {
      // Display the formatted "City, ST" string but store metadata separately
      const region = suggestion.region?.trim().toUpperCase();
      const displayCity = region && region.length === 2
        ? `${suggestion.city}, ${region}`
        : suggestion.city;
      setCity(displayCity);
      setState(region && region.length === 2 ? region : undefined);
      setPlaceId(suggestion.place_id?.trim() || undefined);
      setDataforseoLocationCode(
        typeof suggestion.dataforseo_location_code === "number"
          ? suggestion.dataforseo_location_code
          : undefined,
      );
    } else {
      setCity(newCity);
      setState(undefined);
      setPlaceId(undefined);
      setDataforseoLocationCode(undefined);
    }
  };
```

- [ ] **Step 2: Apply same change to admin mirror**

Apply the identical change to `apps/admin/src/app/(protected)/niche-finder/NicheFinderClient.tsx` (or equivalent admin file using `handleCityChange`).

- [ ] **Step 3: Test manually**

```bash
npm run dev:app
```

1. Go to `http://localhost:3002/niche-finder`
2. Type "Phoenix" in city field
3. Select "Phoenix" from autocomplete dropdown
4. Verify input now shows "Phoenix, AZ" (not just "Phoenix")
5. Enter a service and submit
6. Verify scoring succeeds

- [ ] **Step 4: Commit**

```bash
git add apps/app/src/app/\(protected\)/niche-finder/NicheFinderClient.tsx
git add apps/admin/  # if admin mirror was updated
git commit -m "fix(niche-finder): display 'City, ST' after autocomplete selection to prevent accidental edits"
```

---

### Task 5: Fix Path D — Add upstream error detail passthrough

**Condition:** Execute if Phase 1 showed a 500 from FastAPI (pipeline failure). Also good to do regardless as an observability improvement.

**Files:**
- Modify: `apps/app/src/app/api/agent/scoring/route.ts:48-63`
- Modify: `apps/app/src/app/(protected)/niche-finder/NicheFinderClient.tsx:152-158`

The current scoring proxy swallows the upstream error body and shows a generic "Scoring engine did not return a result." message. The fix: parse the upstream JSON `detail` field and pass it through.

- [ ] **Step 1: Update scoring proxy to forward upstream detail**

In `apps/app/src/app/api/agent/scoring/route.ts`, replace lines 48-63:

```typescript
    if (!upstream.ok) {
      let upstreamDetail = "Scoring engine did not return a result.";
      try {
        const upstreamJson = await upstream.json();
        if (typeof upstreamJson?.detail === "string") {
          upstreamDetail = upstreamJson.detail;
        }
      } catch {
        // upstream body wasn't JSON — use default message
      }

      const proxyMs = Date.now() - proxyStart;
      console.warn(
        "[scoring-proxy] FAIL upstream_status=%d proxy_ms=%d detail=%s",
        upstream.status,
        proxyMs,
        upstreamDetail,
      );
      return NextResponse.json(
        {
          status: "unavailable",
          message: upstreamDetail,
          upstream_status: upstream.status,
        },
        { status: 502 },
      );
    }
```

- [ ] **Step 2: Test with a known bad input**

```bash
npm run dev:app
# In another terminal:
curl -s -X POST http://localhost:3002/api/agent/scoring \
  -H "Content-Type: application/json" \
  -d '{"city":"xyznonexistent","service":"roofing"}' | python3 -m json.tool
```

Expected: Response includes the specific error from FastAPI (e.g., `"no CBSA match for city='xyznonexistent'"`) instead of the generic message.

- [ ] **Step 3: Commit**

```bash
git add apps/app/src/app/api/agent/scoring/route.ts
git commit -m "fix(scoring-proxy): forward upstream error detail instead of generic message"
```

---

### Task 6: Update E2E test to assert correct metadata behavior

**Condition:** Execute after Tasks 3 and 4.

**Files:**
- Modify: `apps/app/e2e/autocomplete-scoring-flow.spec.ts:246-329`

The existing test at lines 246-329 ("Regression: typing after selection clears metadata") asserts that metadata IS cleared — it's testing the buggy behavior. After Task 3 (orchestrator parsing) and Task 4 (display fix), update the test.

- [ ] **Step 1: Update regression test expectations**

The test should now verify:
1. After selection, input shows "City, ST" format
2. If user types after selection, metadata is still cleared (this is correct — a new search invalidates old selection)
3. But the orchestrator can still handle "City, ST" format even without metadata (Task 3 fix)

```typescript
// In autocomplete-scoring-flow.spec.ts, update the test at ~line 246:
test("typing after selection clears metadata but orchestrator handles City, ST format", async ({ page }) => {
  // ... existing setup code ...

  // After selection, input should show formatted "City, ST"
  const inputValue = await page.getByTestId("city-input").inputValue();
  expect(inputValue).toMatch(/,\s*[A-Z]{2}$/);

  // Type additional character — metadata should clear
  await page.getByTestId("city-input").press("End");
  await page.getByTestId("city-input").type(" ");

  // Submit — should still succeed because orchestrator parses "City, ST"
  // (assuming the city or its state has CBSA/DFS coverage)
});
```

- [ ] **Step 2: Run E2E tests**

```bash
npx playwright test autocomplete-scoring-flow --config=apps/app/playwright.config.ts
```

Expected: Tests pass with updated assertions.

- [ ] **Step 3: Commit**

```bash
git add apps/app/e2e/autocomplete-scoring-flow.spec.ts
git commit -m "test(e2e): update autocomplete metadata test to reflect City, ST parsing fix"
```

---

### Task 7: Lint and full regression

- [ ] **Step 1: Lint Python**

```bash
ruff check src/ tests/
```

Expected: Zero errors.

- [ ] **Step 2: Run full Python unit tests**

```bash
pytest tests/unit/ -v
```

Expected: All pass.

- [ ] **Step 3: TypeScript type check**

```bash
cd apps/app && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 4: Run scoring regression E2E**

```bash
npx playwright test scoring-regression --config=apps/app/playwright.config.ts
```

Expected: All pass (Huntsville, city normalization, validation, duplicate submit).

- [ ] **Step 5: Final commit if any lint fixes needed**

```bash
git add -A
git commit -m "chore: lint fixes for autocomplete scoring fix"
```

---

## Unconfirmed Hypothesis Warning

**This plan's lead hypothesis (Path B → C) is unconfirmed.** Phase 1 (Task 1) MUST be completed before executing Phase 2 (Tasks 2-7). If Phase 1 reveals a different active path:

- **Path A only:** Execute Task 2, skip Tasks 3-4.
- **Path B → C:** Execute Tasks 3, 4, 5, 6, 7 (the main plan).
- **Path D only:** Execute Task 5, then investigate API credentials on Render.
- **Path E only:** Investigate `_persist_report` and `generate_report` for null report_id edge case.
- **Multiple paths:** Execute relevant tasks in order.
