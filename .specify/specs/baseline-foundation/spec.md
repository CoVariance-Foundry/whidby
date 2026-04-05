# Baseline: Foundation Modules (M0-M3)

**Status:** Complete (pre-spec-kit baseline)
**Modules:** M0 (DataForSEO Client), M1 (Metro Database), M2 (Supabase Schema), M3 (LLM Client)

## Summary

These modules were implemented before spec-kit adoption. They form the shared infrastructure that all subsequent modules depend on.

## Module Inventory

### M0: DataForSEO Client
- **Spec reference:** Algo Spec V1.1, section 14 (API Reference)
- **Location:** `src/clients/dataforseo/`
- **Tests:** `tests/integration/test_dataforseo_integration.py`
- **Status:** Implemented and tested

### M1: Metro Database
- **Spec reference:** Algo Spec V1.1, sections 3.2-3.3
- **Location:** `src/data/`
- **Tests:** Unit tests present
- **Status:** Implemented

### M2: Supabase Schema
- **Spec reference:** Algo Spec V1.1 (all phases), Experiment Framework section 10
- **Location:** `supabase/migrations/`
- **Tests:** `tests/unit/test_supabase_schema.py`
- **Status:** Migrations created and tested

### M3: LLM Client
- **Spec reference:** Algo Spec V1.1 section 4.2, Experiment Framework sections 6.4, 8.3
- **Location:** `src/clients/llm/`
- **Tests:** `tests/integration/test_llm_integration.py`
- **Status:** Implemented and tested

## Traceability

These modules' I/O contracts are defined in:
- `docs/product_breakdown.md` — Module specifications, file structure, eval criteria
- `docs/module_dependency.md` — Dependency matrix
- `docs/data_flow.md` — Data flow between modules

## Governance Note

Changes to foundation modules after this baseline require:
1. An update to this baseline spec documenting what changed and why
2. Verification that downstream module contracts are not broken
3. Updated tests for any modified contracts
