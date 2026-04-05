# Feature: Response Tracking + Reply Classification (M14)

**Feature branch:** `M14-response-tracking`  
**Status:** Draft  
**Module ID:** M14  
**Spec references:** `docs/outreach_experiment.md` §8 (Phase E5); `docs/product_breakdown.md` (M14)

## Summary

Ingests email lifecycle events (opens, clicks, bounces, replies) via webhooks and edge functions, classifies free-text replies with the LLM client into actionable categories, computes a normalized engagement score per recipient and experiment, and records audit-page analytics for correlation with outreach performance.

## Dependencies

- **M3:** LLM client (structured classification of reply text; deterministic settings per repo policy)
- **M13:** Outreach delivery (provider message ids, thread metadata, sequence enrollment for stop-on-reply)
- **M2 (Supabase):** Durable event log, classification results, engagement scores, RLS policies as applicable

## User Scenarios & Acceptance Scenarios

### US-1 — Marketing operator sees delivery and engagement events

**Acceptance**

- **AS-1.1 (open tracking):** Open events are ingested when the provider emits them, associated with the correct outbound message id and experiment cohort.
- **AS-1.2 (click tracking):** Click events capture target URL and timestamp; clicks on audit links are distinguishable from other tracked links when UTM or path conventions are used.

### US-2 — System classifies replies for downstream automation

**Acceptance**

- **AS-2.1 (taxonomy):** Each classified reply maps to one of: `positive`, `negative`, `already_handled` (exact enum fixed in schema; extension requires spec amendment).
- **AS-2.2 (LLM guardrails):** Classification uses M3 with schema-validated output; ambiguous or empty body yields a documented fallback label and confidence flag.

### US-3 — Engagement is comparable across experiments

**Acceptance**

- **AS-3.1 (score range):** `engagement_score` is on **0–100** inclusive, using weighted signals defined in `engagement_scorer.py` (weights documented in plan/constants).
- **AS-3.2 (idempotency):** Replayed webhooks do not duplicate primary event rows or inflate scores (dedupe key = provider event id or hash contract).

### US-4 — Audit funnel is measurable

**Acceptance**

- **AS-4.1 (audit page tracking):** Audit page views (and optional time-on-page or scroll depth if instrumented) are recorded with linkage to recipient and experiment for M15 analysis.

### US-5 — Edge Functions bridge the web to the data model

**Acceptance**

- **AS-5.1 (webhooks):** Supabase Edge Functions verify provider signatures (where available), normalize payloads, and enqueue or write events atomically per plan.

## Requirements

### Functional

- **FR-1:** Implement `src/experiment/event_tracker.py` to receive, validate, normalize, and persist webhook payloads into Supabase tables defined in plan.
- **FR-2:** Implement `src/experiment/reply_classifier.py` calling M3 to produce structured labels + rationale (optional) for operator review.
- **FR-3:** Implement `src/experiment/engagement_scorer.py` to aggregate opens, clicks, replies, and audit signals into `engagement_score` 0–100.
- **FR-4:** Deploy and document Supabase Edge Functions for inbound provider webhooks; include secret rotation and replay protection strategy in plan.
- **FR-5:** Emit signals consumable by M13 (reply detected → stop sequence) and M15 (experiment metrics).

### Non-functional

- **NFR-1:** Webhook handlers return quickly (< provider timeout); heavy work via queue or async pattern if required by load (documented in plan).
- **NFR-2:** PII in reply text is minimized in logs; retention policy aligns with product policy.

### Implementation mapping (from product breakdown / this spec)

- `src/experiment/event_tracker.py` — ingestion and persistence
- `src/experiment/reply_classifier.py` — LLM classification
- `src/experiment/engagement_scorer.py` — scoring model
- Supabase Edge Functions — HTTP ingress for webhooks

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Open tracking | Opens stored and attributable per AS-1.1 |
| SC-2 | Click tracking | Clicks stored with URL + time per AS-1.2 |
| SC-3 | Reply classification | Labels ∈ {positive, negative, already_handled} per AS-2.1 |
| SC-4 | LLM integration | M3 structured output; fallback path per AS-2.2 |
| SC-5 | Engagement score | 0–100 score per AS-3.1 |
| SC-6 | Webhook idempotency | No duplicate inflation per AS-3.2 |
| SC-7 | Audit tracking | Audit events linked to recipient/experiment per AS-4.1 |
| SC-8 | Edge Functions | Verified ingress + normalized writes per AS-5.1 |

## Assumptions

- Email providers expose sufficient webhook fields to correlate events with M13 send records (message id, recipient, campaign/experiment id).
- M3 rate limits and cost are acceptable for reply volume; batching or sampling is out of scope unless added in plan.
- Audit page instrumentation lives in the audit delivery surface (M12) or eval frontend (M16) as agreed in plan; M14 defines the event contract.

## Source documentation

- `docs/outreach_experiment.md` — §8 / Phase E5 (response tracking and classification)
- `docs/product_breakdown.md` — M14 I/O, eval criteria, file layout
- `docs/module_dependency.md` — ordering vs M13, M15
- `docs/data_flow.md` — events → scores → analysis
- `docs/research_agent_design.md` — cross-cutting observability patterns where applicable
