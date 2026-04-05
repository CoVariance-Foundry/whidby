# Feature: Outreach Delivery + Sequencing (M13)

**Feature branch:** `M13-outreach-delivery`  
**Status:** Draft  
**Module ID:** M13  
**Spec references:** `docs/outreach_experiment.md` §7 (Phase E4); `docs/product_breakdown.md` (M13)

## Summary

Sends personalized outreach emails that include audit links, manages multi-step follow-up sequences, integrates with an email platform (Resend or Instantly) via a pluggable adapter, enforces suppression and daily send limits, and stops sequences on reply, bounce, or unsubscribe while meeting CAN-SPAM requirements.

## Dependencies

- **M12:** Audit generation output (personalized audit URLs and per-recipient context required for message bodies)
- **Email platform:** Resend or Instantly (exact provider selected in plan; behavior abstracted behind adapters)
- **M2 (Supabase):** Persistence for sequence state, suppression lists, and send logs (as defined in plan/schema)

## User Scenarios & Acceptance Scenarios

### US-1 — Operator sends first-touch outreach with a real audit link

**Acceptance**

- **AS-1.1 (rendering):** Rendered HTML and text bodies contain no unresolved template placeholders (e.g. no `{{unresolved}}`); all required merge fields resolve from M12 + recipient record or the send is rejected with a clear validation error.
- **AS-1.2 (audit link):** Each outbound message includes the correct per-business audit URL from M12 output in the primary CTA position defined by templates.

### US-2 — System runs a timed follow-up sequence

**Acceptance**

- **AS-2.1 (schedule):** Default sequence sends follow-ups at **T+0, T+3, T+7** days from enrollment (calendar-day or 24h buckets as fixed in plan; consistent across recipients in the same experiment).
- **AS-2.2 (stop on reply):** When a reply is detected (signal from M14 or adapter/webhook contract), pending sequence steps for that recipient are cancelled and no further automated sends occur.
- **AS-2.3 (stop on bounce):** Hard bounces suppress the address and cancel pending steps; soft bounces follow policy defined in plan (retry vs suppress).

### US-3 — Compliance and list hygiene

**Acceptance**

- **AS-3.1 (suppression):** Before every send, the recipient is checked against suppression (unsubscribe, bounce, manual block); suppressed recipients never receive a message.
- **AS-3.2 (CAN-SPAM):** Outbound messages include required elements (valid physical mailing address, clear identification as commercial where applicable, functioning unsubscribe mechanism per chosen provider + our compliance module).
- **AS-3.3 (unsubscribe):** Unsubscribe events update suppression and halt sequences within the latency bound defined in plan.

### US-4 — Throughput and provider abstraction

**Acceptance**

- **AS-4.1 (daily limit):** A configurable per-day send cap is enforced globally (or per experiment, as specified in plan); excess scheduled sends roll to the next eligible day without silent drops.
- **AS-4.2 (adapter interface):** `email_adapters/` exposes a single interface (send batch, parse provider ids, map errors) implemented by `resend` and `instantly` adapters; orchestration in `email_sender.py` depends only on the interface.

### US-5 — Templates cover the experiment lifecycle

**Acceptance**

- **AS-5.1 (templates):** `email_templates/` contains **five** distinct templates (names and purposes fixed in `/speckit.plan`) covering initial outreach and follow-ups without duplicate placeholder schemes.

## Requirements

### Functional

- **FR-1:** Orchestrate outreach and sequences from `src/experiment/outreach_manager.py`, including enrollment, scheduling, and cancellation rules (reply/bounce/unsubscribe).
- **FR-2:** Render and send email using `email_templates/` and `email_sender.py`; support HTML + text where the provider allows.
- **FR-3:** Implement `email_adapters/resend` and `email_adapters/instantly` behind a shared adapter contract; select provider via configuration.
- **FR-4:** Implement `compliance.py` for CAN-SPAM footer assembly, list-unsubscribe alignment with provider capabilities, and audit trail hooks for regulatory review.
- **FR-5:** Persist send state, sequence step completion, and suppression causes for correlation with M14 webhooks.

### Non-functional

- **NFR-1:** Unit tests mock adapters; no live email in default CI.
- **NFR-2:** Idempotent send requests where provider supports idempotency keys; log provider message ids for deduplication.

### Implementation mapping (from product breakdown / this spec)

- `src/experiment/outreach_manager.py` — sequence orchestration
- `src/experiment/email_sender.py` — send pipeline, validation, rate limiting
- `src/experiment/email_adapters/` — `resend`, `instantly` implementations + shared interface
- `src/experiment/compliance.py` — CAN-SPAM and compliance helpers
- `email_templates/` — five templates

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Email rendering | No stray placeholders in rendered bodies; failed validation blocks send per AS-1.1 |
| SC-2 | Audit links | Correct M12 audit URL in outbound per AS-1.2 |
| SC-3 | Suppression | Suppressed recipients receive zero sends per AS-3.1 |
| SC-4 | CAN-SPAM | Required elements present per AS-3.2 |
| SC-5 | Sequence timing | 0 / 3 / 7 day steps fire per AS-2.1 |
| SC-6 | Stop on reply | Sequence halts on reply signal per AS-2.2 |
| SC-7 | Stop on bounce | Hard bounce suppresses and cancels per AS-2.3 |
| SC-8 | Daily limit | Cap enforced with defined deferral per AS-4.1 |
| SC-9 | Adapters | Both adapters implement shared interface; sender uses interface only per AS-4.2 |
| SC-10 | Templates | Five templates present and referenced by orchestration per AS-5.1 |

## Assumptions

- M12 exposes stable identifiers and audit URLs for each outreach target; breaking changes to that contract require coordinated spec updates.
- Exact webhook/event vocabulary for “reply” and “bounce” may be finalized in M13/M14 plan tasks but must be consistent across modules.
- Provider credentials and sandbox vs production behavior are environment-specific; secrets are not committed.
- Physical address and “from” domain alignment follow organizational policy stored in configuration or Supabase, not hardcoded literals.

## Source documentation

- `docs/outreach_experiment.md` — §7 / Phase E4 (outreach delivery and sequencing)
- `docs/product_breakdown.md` — M13 I/O, eval criteria, file layout
- `docs/module_dependency.md` — ordering vs M12, M14
- `docs/data_flow.md` — audit and outreach data movement
