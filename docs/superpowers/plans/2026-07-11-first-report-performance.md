# First-Report 60-Second / 500-MB Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one real first-report request return a durable, immediately readable report in no more than 60.0 seconds while the API container keeps cgroup `memory.peak <= 500000000` bytes.

**Architecture:** Keep the public request synchronous, but make it an explicit `interactive` collection profile with a bounded core evidence set. Remove the full DataForSEO location catalog from autocomplete, remove serial per-keyword LLM work, cap provider work and memory-retaining state, and measure the complete FastAPI plus persistence boundary in the production container. Preserve the current `full` collection profile for offline/benchmark acquisition. Optional enrichments may not block the first readable report.

**Tech Stack:** Python 3.11, FastAPI, Anthropic async SDK, DataForSEO, Supabase, pytest, Docker/cgroup v2, Next.js BFF.

---

## Global constraints

- `POST /api/niches/score` must return HTTP 2xx with a non-null `report_id`, no `persist_warning`, and a report that `GET /api/niches/{report_id}` can immediately read.
- The measured interval begins immediately before the POST and ends only after the successful report GET, including parsing and contract validation. One shared deadline covers both calls and it must be `<= 60.0` seconds.
- The GET body must repeat the exact POST `report_id` and satisfy the existing required report paths: `generated_at`, `spec_version`, `input`, `keyword_expansion`, `metros`, and `meta`.
- Container `memory.peak` from cgroup v2 must be `<= 500000000` bytes. Use decimal MB because that is stricter than 500 MiB.
- Use a fresh production-image container for cold runs. Also run three reports sequentially in one container, wait five seconds after each run, and prove `memory.current <= 500000000` bytes and process RSS `<= 500000000` bytes while neither post-quiescence metric grows by more than 50,000,000 bytes from the first to the third run.
- Run paid acceptance calls against staging Supabase by mapping `STAGING_SUPABASE_URL` and `STAGING_SUPABASE_SERVICE_ROLE_KEY` to the runtime variable names. Never print or persist secret values.
- A partial upstream failure may lower confidence, but may not make the report unreadable or silently weaken either performance limit.
- Preserve snake_case wire payloads and the existing report schema.
- Preserve the generic `full` M5 profile for non-interactive acquisition. Generic/domain `ScoreRequest` and M5 helpers default to `full`; only public `NicheScoreRequest` and the customer-facing scoring proxy select `interactive`, with the BFF payload explicit.
- Interactive persistence is core-first by contract: only the durable report and critical score rows may block the response. Cost logging, KB evidence, feedback logging, and generated guidance must not execute synchronously on the interactive response path. Do not replace them with an untracked in-process task.
- The Next.js scoring proxy must abort its upstream request and refund consumed quota before the user-visible 60-second limit; a direct FastAPI benchmark alone is not sufficient customer-path coverage.
- Do not touch or stage the user-owned `AGENTS.md` change.
- Do not change `render.yaml` until the live Render plan/configuration is reconciled.
- Canonical documentation changes precede production-code changes.
- Method A is the bounded interactive pipeline. Method B is the mandatory core-first persistence path. If the full production-image gate still fails after both and one targeted retention-copy reduction, stop and report measured infeasibility. Do not raise either limit.

## Measured baseline

- Cold-ish live M4-M9 integration: `96.38s` pytest time, `154,386,432` bytes max RSS, `219,236,736` bytes peak footprint. This excludes persistence and FastAPI.
- Warm live M4-M9 integration: `45.87s` pipeline, `223,150,080` bytes max RSS. M4 was `29.11s`; M5 was `16.27s`.
- M4's default model is no longer available, which triggers about 50 serial Haiku intent calls.
- Interactive autocomplete can hydrate and hash the full DataForSEO locations catalog; production sequence, code history, and the prior identical regression make it a high-confidence causal link to the OOM, but no heap snapshot proves exact byte ownership.
- Pure M6-M9 computation is not the bottleneck: a synthetic 40-MB M5 payload completed M6-M9 in about 9 ms under 80 MB RSS.

## Budget

| Boundary | Budget |
| --- | ---: |
| M4 expansion | 8 s |
| M5 interactive collection | 32 s |
| M6-M9 deterministic work | 2 s |
| Durable core persistence and immediate read | 5 s |
| Safety margin | 8 s |
| FastAPI internal target | 55 s |
| End-to-end hard maximum | 60 s |

Constants introduced by this work must use these exact values unless a later benchmark proves a lower value is required:

```python
FIRST_REPORT_MAX_SECONDS = 60.0
FIRST_REPORT_INTERNAL_TARGET_SECONDS = 55.0
FIRST_REPORT_MAX_MEMORY_BYTES = 500_000_000
M4_INTERACTIVE_TIMEOUT_SECONDS = 8.0
M5_INTERACTIVE_TIMEOUT_SECONDS = 32.0
M5_INTERACTIVE_SERP_LIMIT = 6
M5_MAX_CONCURRENCY = 8
M5_LIVE_TASK_TIMEOUT_SECONDS = 12.0
M5_QUEUED_TASK_TIMEOUT_SECONDS = 20.0
DFS_CACHE_MAX_ENTRIES = 128
DFS_CACHE_MAX_VALUE_BYTES = 2_000_000
```

---

## Task 1: Canonicalize the hard contract and remediation boundary

**Files:**
- Modify: `docs-canonical/REQUIREMENTS.md`
- Modify: `docs-canonical/ARCHITECTURE.md`
- Modify: `docs-canonical/TEST-SPEC.md`
- Create: `specs/016-first-report-performance/spec.md`
- Modify: `specs/013-niche-operational-wiring/spec.md`
- Modify: `docs/first-report-execution-system-review.md`

- [ ] **Step 1: Replace the stale report-time requirement**

Change `NFR-001` to define the complete POST-plus-immediate-GET measurement and the `<= 60.0s` target. Add `NFR-012` for cgroup `memory.peak <= 500000000` and `NFR-013` for bounded repeated-run state.

- [ ] **Step 2: Add the interactive core-report requirement**

Add `FR-042`: interactive first reports must make bounded attempts for one volume batch, at most six representative eligible organic SERPs, one maps SERP, GBP info, and business listings. Backlinks, Lighthouse, review-velocity acquisition, and generated M8 copy are optional enrichment and may not block the first readable report. When providers fail, the minimum degraded result contains the normalized seed keyword, resolved target, complete report schema, deterministic fallback signals/scores, low confidence, and structured provider failures; it must still be durable and readable.

- [ ] **Step 3: Correct the architecture description**

Replace the architecture text that requires a full locations-catalog hydration with Mapbox-only interactive autocomplete plus the existing state/MetroDB resolution fallback. Document the `interactive` versus `full` collection profiles and the 60-second boundary.

- [ ] **Step 4: Add canonical test obligations**

Document the exact Docker/cgroup test, shared POST-plus-GET deadline, GET-body schema validation, cold-run rule, five-second post-run quiescence, `memory.current`/RSS retained-growth bound, three-run repeated-state test, autocomplete no-catalog regression, M4 no-per-keyword fanout, interactive task cap, bounded concurrency, cache cap, context-scoped cost drain, core-first persistence, and BFF abort/refund behavior.

- [ ] **Step 5: Add the feature spec and retire conflicting acceptance text**

Create `specs/016-first-report-performance/spec.md` with user stories, acceptance scenarios, constraints, and Method A/Method B stop rule. Update `specs/013-niche-operational-wiring/spec.md` so its former 30-90-second allowance points to the new hard contract.

- [ ] **Step 6: Reframe the incident artifact**

Record the live baseline measurements. Replace the 4-GB/90-second recommendation with: scaling is temporary containment only; the accepted target is 500,000,000 bytes and 60 seconds. Preserve evidence versus hypothesis labels.

- [ ] **Step 7: Run documentation validation**

Run:

```bash
npx docguard-cli guard
```

Expected: no new documentation violations. If the command hangs or reports a known baseline violation, record the exact result in the artifact and prove the changed docs are internally consistent with targeted searches.

- [ ] **Step 8: Commit**

```bash
git add docs-canonical/REQUIREMENTS.md docs-canonical/ARCHITECTURE.md docs-canonical/TEST-SPEC.md specs/016-first-report-performance/spec.md specs/013-niche-operational-wiring/spec.md docs/first-report-execution-system-review.md docs/superpowers/plans/2026-07-11-first-report-performance.md
git commit -m "docs: define first-report performance contract"
```

---

## Task 2: Add the authoritative performance harness before optimization

**Files:**
- Create: `scripts/perf/first_report_benchmark.py`
- Create: `tests/unit/test_first_report_benchmark.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing unit tests for the benchmark verdict**

Test a pure result validator with all of these cases:

```python
validate_run(elapsed_seconds=60.0, memory_peak_bytes=500_000_000,
             memory_current_bytes=400_000_000, process_rss_bytes=350_000_000,
             post_status=200, read_status=200, post_report_id="report-1",
             read_report_id="report-1", required_read_paths_ok=True,
             persist_warning=None, container_oom=False)  # passes
```

Values above either hard limit, an exhausted shared deadline, non-2xx POST/GET, mismatched/null report IDs, a malformed read body, `persist_warning`, retained-growth overflow, or container OOM must fail.

Run:

```bash
python3.11 -m pytest -q tests/unit/test_first_report_benchmark.py
```

Expected: FAIL because the validator and runner do not exist.

- [ ] **Step 2: Implement a production-image Docker runner**

The script must:

1. Refuse paid calls unless `--allow-paid-provider-calls` is present.
2. Build `Dockerfile.api` or accept `--image`.
3. Write secrets to a mode-0600 temporary `--env-file`, map staging Supabase variables, and delete the file in `finally`.
4. Launch with `--memory=500000000 --memory-swap=500000000` and a random localhost port.
5. Wait for `/health` without including warm-up in report latency.
6. Set one monotonic deadline 60 seconds after the POST begins; pass only the remaining time to POST and then GET so their combined work cannot exceed it.
7. Immediately GET `/api/niches/{report_id}`, parse the JSON, require the same ID, and validate `generated_at`, `spec_version`, `input`, `keyword_expansion`, `metros`, and `meta`.
8. Read `/sys/fs/cgroup/memory.peak`, `/sys/fs/cgroup/memory.current`, aggregate service-container process RSS by summing `VmRSS` for every numeric `/proc` PID, and the container OOM state.
9. For sequential mode, wait `--quiescence-seconds 5` after each validated GET, capture `memory.current` and RSS, and fail if either run-three metric exceeds its run-one value by more than `--max-retained-growth-bytes 50000000`.
10. Emit a redacted JSON result containing timings, status, report ID, memory samples, and verdict; never payload secrets.
11. Define `--fresh-containers N` as N containers with exactly one report each. Define `--sequential-runs N` as one additional container with N reports in sequence.
12. Bound health startup with `--health-timeout-seconds 30`, then bound the complete report/read run with the shared deadline; no HTTP request may lack a timeout.

Canonical payload:

```json
{
  "niche": "plumbing",
  "city": "Tampa",
  "state": "FL",
  "dataforseo_location_code": 1015270,
  "cbsa_code": "45300",
  "cbsa_name": "Tampa-St. Petersburg-Clearwater, FL",
  "population": 3175275,
  "metadata_source": "explicit_cbsa",
  "collection_profile": "interactive"
}
```

- [ ] **Step 3: Make unit tests pass**

Run:

```bash
python3.11 -m pytest -q tests/unit/test_first_report_benchmark.py
```

Expected: PASS.

- [ ] **Step 4: Capture the failing pre-optimization baseline**

Run:

```bash
node scripts/dev/sync_worktree_env.mjs -- python3.11 scripts/perf/first_report_benchmark.py \
  --dockerfile Dockerfile.api \
  --image whidby-first-report-perf:local \
  --fresh-containers 1 \
  --sequential-runs 0 \
  --timeout-seconds 60 \
  --memory-bytes 500000000 \
  --health-timeout-seconds 30 \
  --quiescence-seconds 5 \
  --max-retained-growth-bytes 50000000 \
  --results artifacts/performance/first-report-baseline.json \
  --allow-paid-provider-calls
```

Expected: FAIL latency while retaining the actual memory verdict. Add `artifacts/performance/` to `.gitignore`; summarize the redacted result in the incident artifact without committing the generated JSON.

- [ ] **Step 5: Commit**

```bash
git add scripts/perf/first_report_benchmark.py tests/unit/test_first_report_benchmark.py .gitignore docs/first-report-execution-system-review.md
git commit -m "test: add first-report performance gate"
```

---

## Task 3: Remove the bulk-location OOM risk path from autocomplete

**Files:**
- Modify: `tests/unit/test_api_places_suggest.py`
- Modify: `src/research_agent/api.py`

- [ ] **Step 1: Write the failing no-catalog regression**

Replace bridge-success expectations on the interactive route with a sentinel whose `locations()` raises `AssertionError`. Assert `/api/places/suggest` still returns a usable Mapbox row with:

```python
assert row["dataforseo_location_code"] is None
assert row["enrichment_status"] == "mapbox_only"
```

Also make 226,000 synthetic location rows available behind the sentinel and assert none are iterated.

Run:

```bash
python3.11 -m pytest -q tests/unit/test_api_places_suggest.py
```

Expected: FAIL because the route still invokes `DataForSEOLocationBridge.enrich()`.

- [ ] **Step 2: Remove the route-level bridge**

Delete `_PLACES_DATAFORSEO_BRIDGE`, `_places_dataforseo_bridge`, the timeout, and the route call to `bridge.enrich`. Keep `DataForSEOLocationBridge` only if another non-interactive caller still uses it. Always return Mapbox suggestions as `mapbox_only` with a safe explanation.

- [ ] **Step 3: Verify**

Run:

```bash
python3.11 -m pytest -q tests/unit/test_api_places_suggest.py
rg -n "locations\(\)|DataForSEOLocationBridge" src/research_agent/api.py
```

Expected: tests pass; no interactive route reference remains.

- [ ] **Step 4: Commit**

```bash
git add src/research_agent/api.py tests/unit/test_api_places_suggest.py
git commit -m "fix: remove bulk location hydration from autocomplete"
```

---

## Task 4: Bound M4 and remove serial LLM amplification

**Files:**
- Modify: `tests/unit/test_llm_client.py`
- Modify: `tests/unit/test_keyword_expansion.py`
- Modify: `tests/unit/test_intent_classifier.py`
- Modify: `src/config/constants.py`
- Modify: `src/clients/llm/client.py`
- Modify: `src/pipeline/keyword_expansion.py`

- [ ] **Step 1: Write failing async-client and fanout tests**

Add tests proving:

- `LLMClient` uses an awaitable Anthropic messages call with the current `claude-sonnet-4-6` default, an 8-second timeout, and zero SDK retries.
- LLM expansion and DFS suggestions overlap in time.
- Fifty opaque DFS suggestions cause zero `classify_intent` calls.
- A source timeout returns at least the normalized seed keyword with low confidence in at most the M4 budget.

Run:

```bash
python3.11 -m pytest -q tests/unit/test_llm_client.py tests/unit/test_keyword_expansion.py tests/unit/test_intent_classifier.py
```

Expected: FAIL on the synchronous SDK call, obsolete model, sequential sources, and classifier fanout.

- [ ] **Step 2: Use the async Anthropic SDK**

Construct:

```python
anthropic.AsyncAnthropic(
    api_key=self._api_key,
    timeout=M4_INTERACTIVE_TIMEOUT_SECONDS,
    max_retries=0,
)
```

Await `messages.create`. Update the default model to `claude-sonnet-4-6`; keep `claude-haiku-4-5-20251001` for explicit non-critical classification uses.

- [ ] **Step 3: Run both M4 sources concurrently and classify deterministically**

Start expansion and suggestions together under an 8-second stage budget. Preserve completed results if one source fails. For candidates lacking a structured intent, use `infer_intent_from_rules(keyword) or "commercial"`; do not make one LLM call per keyword. Sort and cap exactly as today.

- [ ] **Step 4: Verify**

Run:

```bash
python3.11 -m pytest -q tests/unit/test_llm_client.py tests/unit/test_keyword_expansion.py tests/unit/test_intent_classifier.py tests/integration/test_keyword_expansion_integration.py
```

The integration test may be skipped without credentials; unit tests must pass.

- [ ] **Step 5: Commit**

```bash
git add src/config/constants.py src/clients/llm/client.py src/pipeline/keyword_expansion.py tests/unit/test_llm_client.py tests/unit/test_keyword_expansion.py tests/unit/test_intent_classifier.py
git commit -m "perf: bound keyword expansion latency"
```

---

## Task 5: Add the bounded interactive M5 profile

**Files:**
- Modify: `tests/unit/test_collection_plan.py`
- Modify: `tests/unit/test_batch_executor.py`
- Modify: `tests/unit/test_data_collection.py`
- Modify: `tests/unit/test_pipeline_orchestrator.py`
- Modify: `tests/unit/test_api_niches.py`
- Modify: `tests/domain/services/test_market_service.py`
- Modify: `apps/app/src/app/api/agent/scoring/route.test.ts`
- Modify: `src/pipeline/types.py`
- Modify: `src/pipeline/collection_plan.py`
- Modify: `src/pipeline/batch_executor.py`
- Modify: `src/pipeline/data_collection.py`
- Modify: `src/pipeline/orchestrator.py`
- Modify: `src/domain/services/market_service.py`
- Modify: `src/research_agent/api.py`
- Modify: `apps/app/src/app/api/agent/scoring/route.ts`

- [ ] **Step 1: Write failing profile-contract tests**

For `interactive`, assert one metro creates no more than ten actual calls:

- one keyword-volume task containing all keywords;
- at most six deterministic eligible organic SERPs;
- one maps SERP;
- GBP info and business listings dependents;
- no backlinks, Lighthouse, or Google reviews.

For `full`, assert existing behavior is unchanged. Assert generic/domain `ScoreRequest` defaults to `full`, public `NicheScoreRequest` defaults to `interactive`, the Next scoring proxy sends `collection_profile: "interactive"`, FastAPI validates that snake_case field, and the selected profile reaches the orchestrator. Preserve the existing exact FastAPI response keys and report-read contract.

- [ ] **Step 2: Write failing concurrency and timeout tests**

Use a real async fake that counts concurrent entries and blocks on an event. Assert observed concurrency never exceeds eight. Patch timeout constants to milliseconds in unit tests; do not sleep for real 12- or 20-second intervals. Assert live and queued overruns become `FailureRecord`s while other results survive.

In the Next route test, use fake timers and a fetch implementation that observes `AbortSignal`. Assert the proxy aborts at 58,000 ms, returns the existing unavailable response, and refunds consumed quota exactly once.

Run:

```bash
python3.11 -m pytest -q tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_data_collection.py tests/unit/test_pipeline_orchestrator.py tests/unit/test_api_niches.py tests/domain/services/test_market_service.py
npm --workspace apps/app test -- --run src/app/api/agent/scoring/route.test.ts
```

Expected: FAIL because profiles, task caps, timeouts, and bounded concurrency do not exist.

- [ ] **Step 3: Implement profile propagation**

Add `CollectionProfile = Literal["interactive", "full"]`. Keep generic M5 helpers and domain `ScoreRequest` defaulting to `full` so ExploreRefreshService and other non-customer callers preserve existing acquisition behavior. Make public `NicheScoreRequest` default to `interactive`, and make the Next BFF payload explicit. Set its upstream abort to exactly 58,000 ms so the 55-second FastAPI target leaves proxy/refund margin.

- [ ] **Step 4: Implement deterministic interactive planning**

Select up to six eligible keywords in existing sorted M4 order. Keep full keyword volume. Exclude optional dependent templates. In M8, use the deterministic template (`llm_client=None`) for `interactive`; keep generated enhancement for `full`.

- [ ] **Step 5: Implement bounded execution**

Use one semaphore with limit eight. Bound each dispatched task with its category timeout, convert timeout to a structured failure, and preserve successful siblings. Do not add test-only production hooks.

- [ ] **Step 6: Verify**

Run the commands from Step 2. Expected: PASS.

- [ ] **Step 7: Run Method A live M4-M9 benchmark**

Run:

```bash
node scripts/dev/sync_worktree_env.mjs -- /usr/bin/time -l \
  python3.11 -m pytest -q \
  tests/integration/test_pipeline_orchestrator_live.py::TestOrchestrator::test_end_to_end_plumbing_denver \
  -s --log-cli-level=INFO
```

Expected: pipeline comfortably below 50 seconds and peak RSS `<= 500000000` bytes. This is directional only; Task 7 is authoritative.

- [ ] **Step 8: Commit**

```bash
git add src/pipeline/types.py src/pipeline/collection_plan.py src/pipeline/batch_executor.py src/pipeline/data_collection.py src/pipeline/orchestrator.py src/domain/services/market_service.py src/research_agent/api.py apps/app/src/app/api/agent/scoring/route.ts tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_data_collection.py tests/unit/test_pipeline_orchestrator.py tests/unit/test_api_niches.py tests/domain/services/test_market_service.py apps/app/src/app/api/agent/scoring/route.test.ts
git commit -m "perf: add interactive report collection profile"
```

---

## Task 6: Bound app-lifetime memory and provider state

**Files:**
- Create: `tests/unit/test_response_cache.py`
- Modify: `tests/unit/test_persistent_cache.py`
- Modify: `tests/unit/test_dataforseo_client.py`
- Modify: `tests/integration/test_dataforseo_integration.py`
- Modify: `tests/unit/test_pipeline_orchestrator.py`
- Modify: `tests/domain/services/test_market_service.py`
- Modify: `src/config/constants.py`
- Modify: `src/clients/dataforseo/cache.py`
- Modify: `src/clients/dataforseo/persistent_cache.py`
- Modify: `src/clients/dataforseo/cost_tracker.py`
- Modify: `src/clients/dataforseo/client.py`
- Modify: `src/pipeline/orchestrator.py`
- Modify: `src/domain/services/market_service.py`
- Modify: `src/research_agent/api.py`

- [ ] **Step 1: Write failing bounded-state tests**

Prove:

- 1,000 unique cache inserts leave no more than 128 entries;
- expired entries are pruned without rereading their exact keys;
- a value larger than 2,000,000 serialized bytes is not retained in L1;
- `None` is not written to persistent cache;
- `ScoreNicheResult.collection_context_id` exposes the exact run context to `MarketService`;
- flushing one full-profile collection context inserts and drains only that context;
- completing an interactive report drains its context without synchronously flushing optional usage telemetry;
- three report contexts flush `N`, `N`, `N`, not `N`, `2N`, `3N`;
- response hashing does not build a second full serialized byte string;
- one `httpx.AsyncClient` is reused and closed by FastAPI lifespan.

Run:

```bash
python3.11 -m pytest -q tests/unit/test_response_cache.py tests/unit/test_persistent_cache.py tests/unit/test_dataforseo_client.py tests/unit/test_pipeline_orchestrator.py tests/domain/services/test_market_service.py
```

Expected: FAIL on unbounded cache/tracker state and per-call HTTP clients.

- [ ] **Step 2: Implement bounded L1 and safe L2 policy**

Use an `OrderedDict` LRU with active expiry, 128 entries, and a 2,000,000-byte per-value admission limit. Never cache `None`; do not cache the locations endpoint even if a non-interactive caller uses it later.

- [ ] **Step 3: Make cost tracking collection-context scoped**

Add `collection_context_id` to `ScoreNicheResult`, set it to the orchestrator run ID, and return it to `MarketService`. Add `records_for_context(context_id)` and `drain_context(context_id)`. Make `flush_to_supabase(report_id, context_id=..., drain=True)` insert only the active full-profile report's rows and drain only after a successful insert. The interactive path drains without a synchronous optional flush. Compute M9 totals from that same context.

- [ ] **Step 4: Reuse the provider HTTP client**

Create one configured `httpx.AsyncClient` per `DataForSEOClient`, expose `aclose()`, and close the shared instance in FastAPI lifespan. Use connect/read/write/pool timeouts that fit the 12-second live-task budget and no blind retry loop beyond that budget.

- [ ] **Step 5: Stream response hashing**

Feed `json.JSONEncoder(...).iterencode(value)` chunks into SHA-256 rather than materializing `json.dumps(...).encode()` for the entire response. Update `tests/integration/test_dataforseo_integration.py::TestRealAPI::test_caching` so it no longer requires the intentionally excluded locations catalog to be cached.

- [ ] **Step 6: Verify and commit**

Run Step 1 tests, then:

```bash
git add src/config/constants.py src/clients/dataforseo/cache.py src/clients/dataforseo/persistent_cache.py src/clients/dataforseo/cost_tracker.py src/clients/dataforseo/client.py src/pipeline/orchestrator.py src/domain/services/market_service.py src/research_agent/api.py tests/unit/test_response_cache.py tests/unit/test_persistent_cache.py tests/unit/test_dataforseo_client.py tests/integration/test_dataforseo_integration.py tests/unit/test_pipeline_orchestrator.py tests/domain/services/test_market_service.py
git commit -m "perf: bound provider memory and request state"
```

---

## Task 7: Make interactive persistence core-first, then run the full gate

**Files:**
- Modify: `tests/domain/services/test_market_service.py`
- Modify: `tests/unit/test_pipeline_orchestrator.py`
- Modify: `src/domain/services/market_service.py`
- Modify: `src/pipeline/orchestrator.py`
- Modify: `docs/first-report-execution-system-review.md`

- [ ] **Step 1: Write the failing core-first persistence tests**

For `interactive`, require the durable report and critical score rows to be persisted before return. Assert cost flush, KB entity/snapshot/evidence writes, feedback logging, and generated guidance are not invoked synchronously; the cost context is drained; `entity_id`/`snapshot_id` may be null; and an optional collaborator failure cannot create `persist_warning` after the core report is durable.

For `full`, assert the existing cost, KB, feedback, and generated-guidance behavior is unchanged.

Run:

```bash
python3.11 -m pytest -q tests/domain/services/test_market_service.py tests/unit/test_pipeline_orchestrator.py
```

Expected: FAIL because the current service runs all optional persistence synchronously.

- [ ] **Step 2: Implement Method B: mandatory core-first persistence**

Branch on `request.collection_profile`. For `interactive`, execute only `market_store.persist_report(...)` and the required child-score writes it already owns, then drain the exact `collection_context_id`. Do not call cost logging, KB, feedback, or an untracked background task. For `full`, preserve current behavior. Record the omitted interactive optional work explicitly in the system-review artifact.

- [ ] **Step 3: Verify Method B unit behavior**

Run Step 1 again. Expected: PASS.

- [ ] **Step 4: Run the authoritative Method A + Method B gate**

Run:

```bash
node scripts/dev/sync_worktree_env.mjs -- python3.11 scripts/perf/first_report_benchmark.py \
  --dockerfile Dockerfile.api \
  --image whidby-first-report-perf:local \
  --fresh-containers 2 \
  --sequential-runs 3 \
  --timeout-seconds 60 \
  --memory-bytes 500000000 \
  --health-timeout-seconds 30 \
  --quiescence-seconds 5 \
  --max-retained-growth-bytes 50000000 \
  --results artifacts/performance/first-report-method-ab.json \
  --allow-paid-provider-calls
```

Pass only if all five requests and reads satisfy the hard latency/memory/schema requirements, both cold containers stay below the memory limit, and the sequential container satisfies the retained-growth rule.

- [ ] **Step 5: Attribute any remaining miss**

Use existing stage logs plus `MarketService.pipeline_ms`, `MarketService.total_ms`, `persist_report` timings, cgroup peak/current, and process RSS. Do not optimize an unmeasured component.

- [ ] **Step 6: If memory still fails, write one failing retention test and remove the measured copy**

Potential changes are permitted only when the profiler identifies them: replace `asdict(metro_result)` with an exact shallow M6 view, avoid `deepcopy(result.report)` when persistence can consume an immutable copy, and release raw M5 containers before optional persistence. Preserve the API/report schema.

- [ ] **Step 7: Rerun the full gate**

Repeat the exact Step 4 command with `--results artifacts/performance/first-report-method-ab-retention.json`.

- [ ] **Step 8: Apply the stop rule**

If the bounded interactive pipeline, mandatory core-first persistence, and the one measured retention-copy reduction still fail either hard limit, stop implementation. Record each method, exact timings, cgroup peak/current, RSS, failing stage, and why further work would require a materially different product/architecture contract. Do not relax the target.

- [ ] **Step 9: Commit**

```bash
git add src/domain/services/market_service.py src/pipeline/orchestrator.py tests/domain/services/test_market_service.py tests/unit/test_pipeline_orchestrator.py docs/first-report-execution-system-review.md
git commit -m "perf: shorten first-report persistence path"
```

---

## Task 8: Final verification, artifact reconciliation, and handoff

**Files:**
- Modify: `docs/first-report-execution-system-review.md`
- Modify: `specs/016-first-report-performance/spec.md`
- Modify: `docs-canonical/TEST-SPEC.md` only if the executed command differs from the documented gate

- [ ] **Step 1: Run the focused suite**

```bash
python3.11 -m pytest -q tests/unit/test_api_places_suggest.py tests/unit/test_llm_client.py tests/unit/test_keyword_expansion.py tests/unit/test_intent_classifier.py tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_data_collection.py tests/unit/test_response_cache.py tests/unit/test_persistent_cache.py tests/unit/test_dataforseo_client.py tests/unit/test_pipeline_orchestrator.py tests/unit/test_api_niches.py tests/domain/services/test_market_service.py tests/unit/test_first_report_benchmark.py
npm --workspace apps/app test -- --run src/app/api/agent/scoring/route.test.ts
```

- [ ] **Step 2: Run broader Python quality gates**

```bash
ruff check src tests scripts/perf
python3.11 -m pytest -q tests/unit tests/domain/services/test_market_service.py
```

- [ ] **Step 3: Run documentation gate**

```bash
npx docguard-cli guard
```

- [ ] **Step 4: Run final authoritative performance proof**

Run the exact Task 7 Step 4 command with `--results artifacts/performance/first-report-final.json`. Attach that redacted JSON result path to the artifact. The artifact must say `verified` only for measured claims and separately list live Render deployment/configuration as unverified until deployed.

- [ ] **Step 5: Reconcile project source of truth**

Create or update the dedicated Linear issue for this hard performance contract with exact test commands, redacted result artifact, remaining risks, and the commit range. Correct the stale “System design links” document only after the canonical docs are committed.

- [ ] **Step 6: Independent whole-branch review**

Use `superpowers:requesting-code-review` with a review package from the branch merge base. Resolve every Critical/Important finding and rerun covering tests.

- [ ] **Step 7: Final commit**

```bash
git add docs/first-report-execution-system-review.md specs/016-first-report-performance/spec.md docs-canonical/TEST-SPEC.md
git commit -m "docs: record first-report performance proof"
```

## Completion definition

This work is complete only when the exact production-image acceptance run proves:

```text
cold POST + immediate GET <= 60.0 seconds
cgroup memory.peak <= 500000000 bytes
HTTP POST/GET successful
report_id non-null
GET report_id matches POST and required report fields validate
persist_warning absent
three sequential reports pass
post-quiescence memory.current and RSS <= 500000000 bytes
run-three memory.current and RSS growth from run one <= 50000000 bytes each
```

Passing unit tests, a faster M4-M9 integration test, a larger Render instance, or a report that is not immediately readable are not completion.
