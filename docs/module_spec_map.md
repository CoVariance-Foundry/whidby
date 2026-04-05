# Module-to-Spec-Kit Feature Map

**Purpose:** Maps every Widby module milestone to its spec-kit feature artifact directory and tracks delivery status through the mandatory lifecycle.

## Baseline (Pre-Spec-Kit)

| Module | Feature Directory | Status | Notes |
|--------|------------------|--------|-------|
| M0: DataForSEO Client | `.specify/specs/baseline-foundation/` | Complete | Pre-spec-kit |
| M1: Metro Database | `.specify/specs/baseline-foundation/` | Complete | Pre-spec-kit |
| M2: Supabase Schema | `.specify/specs/baseline-foundation/` | Complete | Pre-spec-kit |
| M3: LLM Client | `.specify/specs/baseline-foundation/` | Complete | Pre-spec-kit |
| RA-1 to RA-5 | `.specify/specs/baseline-research-agent/` | Complete | Pre-spec-kit |

## Remaining Modules (Spec-Kit Governed)

| Module | Feature Directory | Specify | Clarify | Plan | Tasks | Implement | Merged |
|--------|------------------|---------|---------|------|-------|-----------|--------|
| M4: Keyword Expansion | `.specify/specs/M04-keyword-expansion/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M5: Data Collection | `.specify/specs/M05-data-collection/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M6: Signal Extraction | `.specify/specs/M06-signal-extraction/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M7: Scoring Engine | `.specify/specs/M07-scoring-engine/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M8: Classification | `.specify/specs/M08-classification-guidance/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M9: Report Generation | `.specify/specs/M09-report-generation/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M10: Business Discovery | `.specify/specs/M10-business-discovery/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M11: Site Scanning | `.specify/specs/M11-site-scanning/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M12: Audit Generation | `.specify/specs/M12-audit-generation/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M13: Outreach Delivery | `.specify/specs/M13-outreach-delivery/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M14: Response Tracking | `.specify/specs/M14-response-tracking/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M15: Experiment Analysis | `.specify/specs/M15-experiment-analysis/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |
| M16: Eval Frontend | `.specify/specs/M16-eval-frontend/` | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |

## Gate Checklist Per Module

Before a module PR can merge, verify:

- [ ] Spec artifact exists at `.specify/specs/{feature}/spec.md`
- [ ] Plan artifact exists at `.specify/specs/{feature}/plan.md`
- [ ] Tasks artifact exists at `.specify/specs/{feature}/tasks.md`
- [ ] All unit tests pass: `pytest tests/unit/ -v`
- [ ] Ruff passes: `ruff check src/ tests/`
- [ ] Web lint passes (if applicable): `npm run lint`
- [ ] Architecture docs updated if contracts changed
- [ ] Constitution compliance verified

## Source Spec References Per Module

| Module | Algo Spec Section | Product Breakdown Section | Experiment Spec Section |
|--------|------------------|--------------------------|------------------------|
| M4 | section 4 (Phase 1) | M4: Keyword Expansion | -- |
| M5 | section 5 (Phase 2) | M5: Data Collection | -- |
| M6 | section 6 (Phase 3) | M6: Signal Extraction | -- |
| M7 | section 7 (Phase 4) | M7: Scoring Engine | -- |
| M8 | section 8 (Phase 5) | M8: Classification | -- |
| M9 | sections 9-10 | M9: Report Generation | -- |
| M10 | -- | M10: Business Discovery | section 4 (Phase E1) |
| M11 | -- | M11: Site Scanning | section 5 (Phase E2) |
| M12 | -- | M12: Audit Generation | section 6 (Phase E3) |
| M13 | -- | M13: Outreach Delivery | section 7 (Phase E4) |
| M14 | -- | M14: Response Tracking | section 8 (Phase E5) |
| M15 | -- | M15: Experiment Analysis | section 9 (Phase E6) |
| M16 | All | M16: Eval Frontend | All |
