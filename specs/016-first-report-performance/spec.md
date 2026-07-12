# Feature 016 — First-Report Performance and Memory Contract

## Status

Planned. This specification defines the acceptance boundary before production-code remediation begins. Current measurements are baselines, not proof that the contract passes.

## Problem

The customer first-report path is synchronous but its previous documentation allowed up to ten minutes and its older operational smoke accepted 30-90 seconds. The current path can also hydrate the complete DataForSEO locations catalog during autocomplete, fan out unbounded provider work, retain app-lifetime state, and perform optional persistence before returning. Production has already recorded a recurring over-2-GB Render OOM, while the user-facing BFF waited until a 300-second host timeout.

A successful pipeline object is not enough. The customer needs the report to be durable and readable immediately, the quota path must settle correctly, and the serving process must remain bounded across repeated reports.

## Goal

Make the customer-facing `interactive` first-report path return a durable, immediately readable report within `60.0` seconds while the production API image stays at or below `500000000` bytes peak memory and retains no more than `50000000` bytes of additional quiescent state from the first to the third sequential run.

## User Stories

- As a new customer, I want my first report to open within one minute so that onboarding reaches a useful result instead of a timeout.
- As a customer on a degraded provider run, I want a complete low-confidence report with explicit failure context so that partial upstream availability does not produce a broken or missing report.
- As a customer whose scoring request exceeds its deadline, I want the request stopped and my consumed quota refunded exactly once so that a timeout does not spend an entitlement.
- As an operator, I want cold and repeated production-image measurements so that a passing unit test or larger Render plan cannot be mistaken for production readiness.
- As a scoring maintainer, I want the broader `full` acquisition profile preserved so that first-report limits do not silently weaken offline or benchmark collection.

## Hard Acceptance Contract

An accepted run satisfies all of the following:

1. One monotonic deadline begins immediately before `POST /api/niches/score` and covers the POST, immediate GET, JSON parsing, and contract validation. Total elapsed time is `<= 60.0` seconds.
2. POST returns HTTP 2xx, a non-null `report_id`, and no `persist_warning`.
3. `GET /api/niches/{report_id}` begins immediately after POST, returns HTTP 2xx, repeats the exact POST `report_id`, and contains `generated_at`, `spec_version`, `input`, `keyword_expansion`, `metros`, and `meta`.
4. The production image runs under cgroup v2 with `--memory=500000000 --memory-swap=500000000`; `memory.peak <= 500000000` bytes and the container is not OOM-killed.
5. Two fresh containers each pass one cold canonical Tampa/Plumbing report.
6. One additional container passes three reports sequentially. Five seconds after each validated GET, cgroup `memory.current` and process-1 RSS remain below `500000000` bytes. From run one to run three, neither quiescent value grows by more than `50000000` bytes.
7. The customer BFF sends `collection_profile: "interactive"`, aborts the upstream request at 58 seconds, and refunds consumed quota exactly once on timeout before the user-visible limit.

Passing M4-M9 integration timing alone, increasing Render memory, returning an unreadable report, or persisting a report with `persist_warning` does not satisfy this contract.

## Collection Profiles

| Profile | Required behavior |
| --- | --- |
| `interactive` | Customer first-report profile. Make bounded attempts for one keyword-volume batch, at most six representative eligible organic SERPs, one maps SERP, GBP info, and business listings. Plan at most ten actual provider calls for one metro and execute at concurrency no greater than eight. |
| `full` | Preserve the existing comprehensive non-interactive acquisition behavior for offline, benchmark, backfill, and explicitly requested enrichment runs. |

Backlinks, Lighthouse, Google review-velocity acquisition, and generated M8 copy are optional enrichment for `interactive` and cannot block the first readable report.

## Minimum Degraded Report

A bounded provider attempt may fail or time out without failing the product contract. The durable degraded report must still contain:

- the normalized seed keyword;
- the resolved city/state or canonical target;
- the complete existing report schema;
- deterministic fallback signals and scores;
- explicit low confidence; and
- structured provider failure records without secret-bearing text.

The degraded run remains subject to the same latency, memory, immediate-read, report-ID, and no-`persist_warning` requirements.

## Remediation Constraints

| Control | Required value or behavior |
| --- | --- |
| FastAPI internal target | 55 seconds |
| Customer BFF abort | 58,000 ms with exactly-once quota refund |
| End-to-end POST/read maximum | 60.0 seconds under one shared deadline |
| Cgroup peak | `<= 500000000` bytes |
| Quiescence sample | Five seconds after every validated GET |
| Retained growth | Run-three `memory.current` and RSS each no more than `50000000` bytes above run one |
| M4 budget | 8 seconds, no per-keyword LLM classification fanout |
| M5 budget | 32 seconds |
| Interactive organic SERPs | At most six, selected deterministically from eligible M4 order |
| Interactive provider calls | At most ten for one metro |
| Provider concurrency | At most eight |
| Live / queued task bounds | 12 seconds / 20 seconds, surfaced as structured failures |
| L1 response cache | At most 128 entries; values above 2,000,000 serialized bytes are not admitted |
| Locations catalog | Never loaded, cached, hashed, or iterated by interactive autocomplete |
| Wire contracts | Preserve snake_case and the existing report schema |
| Secrets | Use staging Supabase mappings through a mode-0600 temporary env file; never print or persist values |
| Infrastructure | Do not change `render.yaml` until live Render configuration is reconciled |

## Core-First Persistence

The `interactive` response-critical section contains only the durable report and its critical score rows. Cost logging, KB entity/snapshot/evidence writes, feedback logging, and generated guidance do not run synchronously and cannot be placed in an untracked in-process task. The exact collection cost context is drained so records do not accumulate across reports. The `full` profile retains its existing optional-persistence behavior.

## Acceptance Scenarios

### Scenario 1 — Cold readable report

- **Given** a fresh production-image container with staging credentials and the canonical Tampa/Plumbing `interactive` payload
- **When** the benchmark posts the score request and immediately reads the returned report
- **Then** both responses, body validation, latency, cgroup peak, and OOM checks satisfy the hard acceptance contract.

### Scenario 2 — Immediate-read integrity

- **Given** POST returns a non-null `report_id` without `persist_warning`
- **When** the benchmark immediately reads that ID
- **Then** GET returns the same ID and all required report paths before the shared deadline expires.

### Scenario 3 — Partial upstream failure

- **Given** one or more bounded provider attempts fail or time out
- **When** deterministic fallback processing completes
- **Then** the system persists and immediately reads the minimum degraded report with low confidence and structured failures under the unchanged hard limits.

### Scenario 4 — Repeated state remains bounded

- **Given** one production-image container
- **When** it completes three sequential reports and waits five seconds after each read
- **Then** every run passes, all absolute memory limits hold, run-three `memory.current` and RSS growth from run one are each `<= 50000000` bytes, and caches and cost contexts remain capped.

### Scenario 5 — Autocomplete avoids the bulk catalog

- **Given** Mapbox returns a usable city and a 226,000-row DataForSEO locations sentinel is available
- **When** the interactive places endpoint serves the suggestion
- **Then** it returns `enrichment_status=mapbox_only` with a null DFS code, never calls or iterates the sentinel, and scoring resolves through state/MetroDB fallback.

### Scenario 6 — Customer-path timeout

- **Given** quota was consumed and the Render request has not completed at 58 seconds
- **When** the BFF deadline fires
- **Then** it aborts upstream work, returns the existing unavailable response, and refunds quota exactly once before 60 seconds.

### Scenario 7 — Optional collaborators do not block

- **Given** an `interactive` report has durable core rows
- **When** cost, KB, feedback, or generated-guidance collaborators are slow, unavailable, or omitted
- **Then** none is called synchronously, none creates `persist_warning`, and no untracked background task is created.

### Scenario 8 — Full acquisition remains available

- **Given** a non-interactive caller requests `full`
- **When** it builds and executes its collection plan
- **Then** existing comprehensive collection and optional-persistence behavior remains unchanged.

## Method A, Method B, and Stop Rule

**Method A — bounded interactive pipeline:** remove bulk location hydration from autocomplete; bound M4 at eight seconds without serial per-keyword LLM work; plan at most ten M5 calls; cap concurrency at eight; enforce task deadlines; and bound caches, response hashing, provider clients, and cost contexts.

**Method B — mandatory core-first persistence:** for `interactive`, synchronously write only the durable report and critical score rows, drain the exact collection context, and omit optional cost/KB/feedback/generated-guidance work from the response path without creating an untracked task. Method B is required even if Method A alone meets the latency target.

After both methods, the authoritative gate runs two cold reports plus three sequential reports. If measured memory still fails, one targeted retention-copy reduction is permitted only after profiling identifies the retained copy. If the full gate still fails either hard limit, implementation stops. The artifact must record each method, exact elapsed times, cgroup peak/current, process RSS, failing stage, and why a materially different product or architecture contract would be required. Neither limit may be raised.

## Out of Scope

- Treating a larger Render instance as acceptance evidence.
- Changing `render.yaml` before live configuration reconciliation.
- Changing the public report schema or wire casing.
- Weakening the `full` profile to make the interactive gate pass.
- Introducing a durable queue, worker, or asynchronous user contract in this remediation. Those require a separate product/architecture decision only if the stop rule proves the synchronous contract infeasible.
- Persisting optional work through an untracked in-process background task.

## Verification

The final authoritative command is maintained in `docs-canonical/TEST-SPEC.md`. It must produce a redacted JSON artifact under ignored `artifacts/performance/`, and acceptance remains unverified until all five report/read pairs and retained-state checks pass. Supporting focused tests cover autocomplete, M4, M5 planning/execution, provider state, persistence, FastAPI contracts, the benchmark validator, and the consumer BFF abort/refund path.

## References

- `docs-canonical/REQUIREMENTS.md` — FR-042 and NFR-001/NFR-012/NFR-013
- `docs-canonical/ARCHITECTURE.md` — execution profiles, autocomplete boundary, and synchronous budget
- `docs-canonical/TEST-SPEC.md` — authoritative and supporting test obligations
- `docs/first-report-execution-system-review.md` — production incident evidence and measured baselines
- `docs/superpowers/plans/2026-07-11-first-report-performance.md` — dependency-ordered implementation plan
