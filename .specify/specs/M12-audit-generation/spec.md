# Feature: Audit Generation (M12)

**Feature branch:** `M12-audit-generation`  
**Status:** Draft  
**Module ID:** M12  
**Spec references:** `docs/outreach_experiment.md` §6 (Phase E3)

## Summary

The module generates **personalized HTML audit pages** for each qualified business, at **unique hosted URLs**, using three **depth tiers**: **minimal**, **standard**, and **visual_mockup**. Audits embed **tracking pixels** (opens and key interactions as defined in plan) and use the **LLM (M3)** for narrative copy grounded in **M11 scan facts** so issues are not hallucinated.

## Dependencies

- **M3:** LLM client (structured prompts, JSON or templated sections, temperature policy for factual tone)
- **M11:** Site scanning output (weakness score, issues list, schema flags, quality bucket, content features)

## User Scenarios & Acceptance Scenarios

### US-1 — Recipient opens a minimal audit

**Acceptance**

- **AS-1.1 (length):** **Minimal** tier HTML body text totals **< 200 words** (excluding boilerplate, nav, and tracking snippet).
- **AS-1.2 (issues):** Minimal audit surfaces **3–5** prioritized issues derived only from M11 signals (no invented problems).
- **AS-1.3 (personalization):** Page includes business name, metro/niche context, and at least one **site-specific** reference tied to scan data.

### US-2 — Practitioner reviews a standard audit

**Acceptance**

- **AS-2.1 (scored sections):** **Standard** tier includes **scored sections** (e.g. technical, on-page, content, schema) with numeric or letter grades per plan template.
- **AS-2.2 (traceability):** Each section’s top findings map to **machine-readable issue IDs** from M11 for QA and regression tests.

### US-3 — Prospect sees a visual mockup tier

**Acceptance**

- **AS-3.1 (before/after):** **Visual_mockup** tier includes **before/after** imagery (screenshots or composited mocks) produced via screenshot capture pipeline.
- **AS-3.2 (honesty):** “After” visuals are labeled per legal/UX policy (e.g. **conceptual preview**) if not live site changes.

### US-4 — Operations hosts audits at unique URLs

**Acceptance**

- **AS-4.1 (unique URL):** Each generated audit is reachable at a **unique, non-guessable** URL path (tokenized slug or UUID per plan).
- **AS-4.2 (availability):** Hosting layer returns **200** for published audits and **404** for unknown tokens; invalidation/expiry behavior documented.

### US-5 — Marketing measures engagement

**Acceptance**

- **AS-5.1 (tracking pixel):** Each audit HTML includes a **tracking pixel** (or equivalent beacon) firing on load with audit ID and tier metadata.
- **AS-5.2 (privacy):** Pixel endpoints and parameters comply with experiment privacy notes (no unnecessary PII).

### US-6 — LLM copy stays factual

**Acceptance**

- **AS-6.1 (no hallucinated issues):** Generated copy MUST NOT assert issues absent from M11 output; automated tests flag unknown issue references.
- **AS-6.2 (fallback):** If LLM output drifts, pipeline **rejects or repairs** via schema validation / second pass per plan.

## Requirements

### Functional

- **FR-1:** Expose generation API accepting **business identity**, **M11 scan payload**, **tier** ∈ {`minimal`, `standard`, `visual_mockup`}, and returning **HTML string** + **public URL** + **audit record ID**.
- **FR-2:** Maintain **three HTML templates** under `src/experiment/audit_templates/` (one per tier baseline); `audit_generator.py` fills slots from data + LLM sections.
- **FR-3:** Implement **audit_hosting.py**: upload/serve static HTML (or SSR shim) to unique paths; configure base URL from environment.
- **FR-4:** Implement **screenshot_capture.py** for **visual_mockup** tier (before = live or cached capture; after = template-based or annotated composite per plan).
- **FR-5:** **LLM integration** uses M3 with a **strict allowlist** of facts (issue IDs, metrics, bucket); narrative text MUST cite only those facts.
- **FR-6:** Embed **tracking pixel** HTML snippet configurable by endpoint URL constant.

### Non-functional

- **NFR-1:** Unit tests validate HTML structure, word counts, issue counts, and **forbidden hallucination** patterns using fixed M11 fixtures (no live LLM in default CI unless snapshot tests are approved).
- **NFR-2:** Generated pages are **safe static HTML** (escaped user-derived strings, no script injection from business names/URLs).

### Implementation mapping

- `src/experiment/audit_generator.py` — tier selection, LLM orchestration, template merge
- `src/experiment/audit_templates/` — **three** baseline HTML files (minimal, standard, visual_mockup)
- `src/experiment/audit_hosting.py` — publish + unique URL policy
- `src/experiment/screenshot_capture.py` — captures for visual tier

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Minimal length | Body **< 200 words** per AS-1.1 |
| SC-2 | Minimal issues | **3–5** issues from M11 only per AS-1.2 |
| SC-3 | Standard sections | Scored sections present per AS-2.1 |
| SC-4 | Visual mockup | Before/after visuals per AS-3.1 |
| SC-5 | Personalization | Business/site-specific content per AS-1.3 |
| SC-6 | Unique URL | Unique hosted path per AS-4.1 |
| SC-7 | Tracking | Pixel present and wired to audit ID per AS-5.1 |
| SC-8 | LLM fidelity | No hallucinated issues in tests per AS-6.1–AS-6.2 |

## Assumptions

- Hosting target (Supabase storage, S3+CDN, or app route) is fixed in `/speckit.plan`; this spec requires only **stable public HTTPS URLs**.
- Screenshot capture may depend on headless Chrome in CI for a narrow golden-path test or use static image fixtures for default unit tests.
- LLM model and temperature follow M3 defaults unless experiment doc mandates stricter **temp = 0** for audit prose.

## Source documentation

- `docs/outreach_experiment.md` — §6 (Phase E3)
- `docs/product_breakdown.md` — M12 I/O contract, eval criteria, file layout (if present)
- `docs/module_dependency.md` — ordering vs M3 and M11
- `docs/data_flow.md` — audits consumed by outreach / tracking modules
