# Feature Specification: Data Persistence Layer

**Feature Branch**: `010-data-persistence-layer`
**Created**: 2026-04-06
**Status**: Draft
**Input**: User description: "Data Persistence Layer: Observation store, canonical reference store, and anchor search system for temporal analysis, cache reuse, and absolute scoring baselines"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Repeated Niche Queries Use Cached Data (Priority: P1)

A practitioner requests a niche+metro scoring report for "plumber in Phoenix." One hour later, a second practitioner (or the same one) requests the same niche and metro. The system recognizes that fresh data already exists, skips paid API calls, and returns results using the previously collected observations — delivering the report faster and at zero incremental data cost.

**Why this priority**: Cost reduction is the highest-impact, lowest-risk win. Every duplicate API call is wasted money. Caching directly reduces operating costs and improves response time for the most common use case.

**Independent Test**: Run two identical scoring pipeline executions within an hour. Verify the second run makes zero paid API calls, completes faster, and produces equivalent scoring output.

**Acceptance Scenarios**:

1. **Given** a completed pipeline run for "plumber in Phoenix" that finished 30 minutes ago, **When** a new pipeline run is triggered for the same niche and metro, **Then** the system serves data from the observation store without calling external APIs, and the total API cost for the second run is $0.00.
2. **Given** a completed pipeline run for "plumber in Phoenix" that finished 25 hours ago, **When** a new pipeline run is triggered for the same niche and metro, **Then** the system detects that SERP data has expired (24-hour TTL) and re-fetches SERP endpoints while still reusing unexpired keyword volume data (30-day TTL).
3. **Given** a practitioner who needs the absolute latest data, **When** they trigger a pipeline run with force-refresh enabled, **Then** all data is re-fetched from the API regardless of cache state, the new observations are stored alongside (not replacing) the old ones, and the report uses only the freshly collected data.

---

### User Story 2 - Scoring Anchored Against Industry Baselines (Priority: P2)

A practitioner receives a scoring report for "electrician in Tucson." Instead of scores that only reflect how Tucson compares to other metros *in the same report*, the scores also reflect how Tucson compares to national and metro-tier benchmarks — e.g., "CPC is 35% below the national median for electricians" or "review counts are typical for mid-size metro electrician markets."

**Why this priority**: Absolute baselines make scores meaningful beyond a single report. Without them, a report with only 3 metros produces misleading relative rankings. Benchmarks are the foundation for score calibration and user trust.

**Independent Test**: Generate a report for a niche+metro that has existing benchmark data. Verify the opportunity scores incorporate both relative (within-report) and absolute (vs. benchmark) components, and that the report output includes benchmark context.

**Acceptance Scenarios**:

1. **Given** computed benchmarks exist for "plumber" at the national level and for "mid-size metro" tier, **When** a scoring report is generated for "plumber in Tucson" (a mid-size metro), **Then** the demand and monetization scores blend relative ranking with absolute benchmark comparison.
2. **Given** no benchmarks exist for a newly discovered niche, **When** a scoring report is generated for that niche, **Then** the system falls back to relative-only scoring (same as current behavior) without errors.
3. **Given** both external-seeded and internally-computed benchmarks exist for the same metric, **When** the scoring engine requests a benchmark, **Then** fresh computed benchmarks take priority over external seeds.

---

### User Story 3 - Temporal Trend Analysis for Key Markets (Priority: P3)

An analyst wants to understand how competition for "pest control in Atlanta" has changed over the last 90 days. The system provides a time series of key signals — average DA of top-5 organic results, local pack review velocity, search volume trends, and AIO presence — collected automatically on a daily cadence without any user-triggered report runs.

**Why this priority**: Temporal analysis is the highest-value differentiator but requires accumulated data over time. It depends on the observation store (P1) and benefits from benchmarks (P2). It is less urgent than immediate cost savings and scoring accuracy.

**Independent Test**: After 7+ days of automated anchor data collection for a configured niche+metro pair, query the signal snapshot history and verify a complete daily time series with no gaps.

**Acceptance Scenarios**:

1. **Given** an anchor configuration for "pest control in Atlanta" that has been running daily for 14 days, **When** the analyst queries signal snapshots for the last 14 days, **Then** the system returns 14 daily snapshot records, each containing SERP DA averages, review counts, search volume, and AIO presence indicators.
2. **Given** a daily anchor run encounters a transient API failure for one data type, **When** the run completes, **Then** the successfully collected data types are still stored and the failure is logged without blocking subsequent anchor runs.
3. **Given** an anchor's daily cost would exceed its configured budget, **When** the anchor runner evaluates the anchor, **Then** the run is skipped with a "budget_exceeded" status and the system continues processing other anchors.

---

### User Story 4 - Cold Start Bootstraps Benchmarks from Day One (Priority: P2)

On initial deployment, the system runs a batch of simulated pipeline executions across a diverse set of niches and metros to populate the observation store and compute initial industry benchmarks. This ensures the first real user reports benefit from absolute scoring baselines rather than operating benchmark-blind for months.

**Why this priority**: Without cold start, the benchmark system has no data to compute from, making P2 (benchmark-anchored scoring) useless until enough organic reports accumulate. The cold start is a prerequisite for P2's value delivery.

**Independent Test**: Execute the cold start protocol for a subset of the niche/metro matrix. Verify benchmarks are computed and available for scoring within 48 hours.

**Acceptance Scenarios**:

1. **Given** the observation store and canonical tables are deployed but empty, **When** the cold start protocol executes 100 simulated pipeline runs across 20 niches and 25 metros, **Then** at least 40,000 observations are stored and at least 500 benchmark values are computed.
2. **Given** externally-seeded benchmarks are loaded before the simulation, **When** computed benchmarks are produced from simulation data, **Then** any computed benchmark that diverges more than 50% from the external seed is flagged for manual review.
3. **Given** the cold start has completed, **When** a real user requests a report for a niche+metro combination covered by the simulation, **Then** the system serves cached observations (if within TTL) at zero API cost and uses computed benchmarks for absolute scoring.

---

### Edge Cases

- What happens when the observation storage bucket is temporarily unavailable? The system must fall through to live API calls and not fail the pipeline.
- What happens when a DataForSEO API response is malformed or returns an error? The observation is stored with `status = 'error'` and is never served as a cache hit.
- What happens when two concurrent pipeline runs request the same uncached data simultaneously? Both should proceed with API calls; the first write wins in the observation store and the second becomes a redundant (but harmless) append.
- What happens when observation storage approaches capacity limits? The retention cleanup purges storage payloads older than 24 months while preserving index rows for long-term trend metadata.
- What happens when a benchmark's sample size is too small to be statistically meaningful? The system requires a minimum sample size (5+ observations) before producing a computed benchmark, falling back to external seeds or no benchmark.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist every external data API response as an immutable, timestamped observation with the query parameters that produced it.
- **FR-002**: System MUST check for fresh cached observations before making paid API calls, using data-type-specific freshness windows (ranging from 24 hours for search results to 90 days for reference data).
- **FR-003**: System MUST allow callers to bypass the cache and force a fresh API call while still storing the new observation (append-only — old observations are never deleted or overwritten).
- **FR-004**: System MUST store lightweight observation metadata in the database for fast lookups, with full API response payloads stored separately in object storage.
- **FR-005**: System MUST maintain canonical reference data for metro demographics (with population-based size tiers), industry benchmarks (computed from accumulated observations), and niche taxonomies (category mappings and default parameters).
- **FR-006**: System MUST compute industry benchmarks weekly from observations accumulated over the prior 90 days, requiring a minimum sample size before producing a benchmark value.
- **FR-007**: System MUST support a benchmark priority chain: fresh computed values take precedence over externally-seeded values, which take precedence over stale computed values, which take precedence over no benchmark.
- **FR-008**: System MUST support automated, scheduled data collection for configured niche+metro pairs at configurable frequencies (daily, weekly, monthly) with per-anchor cost budgets.
- **FR-009**: System MUST produce daily signal snapshots from anchor data collection, storing denormalized key metrics for efficient time-series queries.
- **FR-010**: System MUST support a cold start protocol that batch-executes pipeline runs across a diverse niche/metro matrix to bootstrap the observation store and enable benchmark computation from day one.
- **FR-011**: System MUST purge storage payloads older than 24 months while retaining observation index rows indefinitely for long-term trend metadata.
- **FR-012**: System MUST preserve backward compatibility with the existing scoring pipeline — the addition of persistence must not change the shape of data returned to callers or alter scoring output (until benchmarks are explicitly integrated).
- **FR-013**: System MUST track cumulative API cost per observation source (pipeline, anchor, manual) for cost attribution and budget monitoring.

### Key Entities

- **Observation**: An immutable record of a single external API response, including what was queried (endpoint + parameters), when it was observed, how much it cost, where the full payload is stored, and when it expires for caching purposes.
- **Canonical Metro**: An enriched metro record with population, growth, region, size tier classification, and DataForSEO location code mappings. Refreshed annually from census data.
- **Canonical Benchmark**: A computed or externally-seeded industry metric (e.g., median CPC, average review count) scoped by niche and optionally by metro size tier. Refreshed weekly from accumulated observations.
- **Canonical Niche**: A niche taxonomy entry with category mappings, vertical classification, typical AIO exposure, and known keyword modifier patterns. Maintained manually with LLM-assisted discovery.
- **Anchor Configuration**: A subscription-like record defining which niche+metro pair to monitor, what data types to collect, at what frequency, with what keywords, and under what cost budget.
- **Anchor Run**: A log entry for each execution of an anchor's data collection cycle, recording timing, cost, observation count, and completion status.
- **Signal Snapshot**: A denormalized daily summary of key competition and demand signals for one anchor, derived from that day's observations, optimized for time-series queries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A second scoring request for the same niche+metro within the freshness window completes with zero paid external data calls and at least 50% faster than the first request.
- **SC-002**: After the cold start protocol completes, computed benchmarks are available for at least 80% of the target niche × metro-tier combinations (20 niches × 3 tiers).
- **SC-003**: Monthly external data costs decrease by at least 30% compared to the pre-cache baseline for equivalent report volume.
- **SC-004**: Automated anchor data collection runs complete with a 95%+ success rate over any 7-day window.
- **SC-005**: Signal snapshot time-series queries for a specific niche+metro return results within 2 seconds for up to 365 days of daily data.
- **SC-006**: The scoring pipeline produces identical output before and after the persistence layer is added (until benchmark-blended scoring is explicitly enabled).
- **SC-007**: At V1 scale (200 anchors), automated data collection costs remain under $500/month.
- **SC-008**: Observation storage payloads older than 24 months are automatically purged, with index rows retained for historical queries.

## Assumptions

- The existing scoring pipeline (M0 through M9) is stable and its test suite passes. The persistence layer is additive — it does not require rewriting pipeline logic.
- External data API pricing remains stable enough that the cost model projections (e.g., ~$0.07/anchor/day) are accurate within 2x.
- Object storage is available and reliable for payload persistence. Temporary unavailability should cause graceful fallback to live API calls, not pipeline failure.
- The cold start cost (~$250 for 100 simulated reports) is an approved one-time investment.
- Benchmark-blended scoring (absolute + relative) is a separate, opt-in change to the scoring engine that ships after the persistence layer is stable. The persistence layer does not alter scoring output by default.
- Supabase Edge Functions and pg_cron are available and suitable for scheduled anchor execution at the required scale.
- All cached observations are shared infrastructure — no user-level data isolation is required for API response caching. User-scoped data (reports, feedback logs) remains isolated.
- Data retention of 24 months for storage payloads provides sufficient depth for temporal analysis while keeping storage costs manageable.
