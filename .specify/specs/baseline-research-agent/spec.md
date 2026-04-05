# Baseline: Research Agent (RA-1 through RA-5)

**Status:** Complete (pre-spec-kit baseline)
**Modules:** RA-1 (Hypothesis Generator), RA-2 (Experiment Planner), RA-3 (Ralph Research Loop), RA-4 (Evaluator + Recommender), RA-5 (Graph Memory + Filesystem Store)

## Summary

The research agent is an autonomous system that improves Widby's niche scoring algorithm through hypothesis-driven experiments in iterative Ralph loops. It was implemented before spec-kit adoption.

## Module Inventory

### RA-1: Hypothesis Generator
- **Location:** `src/research_agent/`
- **Tests:** `tests/unit/test_hypothesis_generator.py`
- **Dependencies:** M7 scoring output

### RA-2: Experiment Planner
- **Location:** `src/research_agent/`
- **Dependencies:** RA-1

### RA-3: Ralph Research Loop
- **Location:** `src/research_agent/loop/`
- **Tests:** `tests/unit/test_research_agent_loop.py`
- **Dependencies:** RA-2, RA-4, RA-5

### RA-4: Evaluator + Recommender
- **Location:** `src/research_agent/`
- **Tests:** `tests/unit/test_recommendation_engine.py`
- **Dependencies:** RA-3

### RA-5: Graph Memory + Filesystem Store
- **Location:** `src/research_agent/`
- **Tests:** `tests/unit/test_graph_memory_store.py`
- **Dependencies:** None

## Design Reference

Full architecture, loop semantics, tool contracts, memory model, and failure modes are documented in `docs/research_agent_design.md`.

## Integration Points

- **Input:** M7 scoring output feeds hypothesis generation
- **Output:** Recommendations feed back to M7 parameter updates
- **Tools:** Wraps M0 (DataForSEO), M1 (Metro DB), M3 (LLM) via tool adapters

## Governance Note

Changes to the research agent after this baseline require:
1. An update to this baseline spec documenting what changed and why
2. Updates to `docs/research_agent_design.md`
3. Verification that tool adapter contracts match foundation module interfaces
