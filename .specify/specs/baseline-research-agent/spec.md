# Baseline: Research Agent (RA-1 through RA-5 + RA-6 through RA-8)

**Status:** Complete (updated 2026-04-06 via 009-claude-native-agent)
**Modules:** RA-1 (Hypothesis Generator), RA-2 (Experiment Planner), RA-3 (Ralph Research Loop), RA-4 (Evaluator + Recommender), RA-5 (Graph Memory + Filesystem Store), RA-6 (Plugin Registry), RA-7 (Claude Agent), RA-8 (Tool Plugins)

## Summary

The research agent is an autonomous system that improves Widby's niche scoring algorithm through hypothesis-driven experiments in iterative Ralph loops. It uses Claude-native tool-use (Anthropic SDK) with a modular plugin registry for AI-powered experiment reasoning.

## Module Inventory

### RA-1: Hypothesis Generator
- **Location:** `src/research_agent/hypothesis/generator.py`
- **Tests:** `tests/unit/test_hypothesis_generator.py`
- **Dependencies:** M7 scoring output

### RA-2: Experiment Planner
- **Location:** `src/research_agent/hypothesis/experiment_planner.py`
- **Dependencies:** RA-1

### RA-3: Ralph Research Loop
- **Location:** `src/research_agent/loop/ralph_loop.py`
- **Tests:** `tests/unit/test_research_agent_loop.py`
- **Dependencies:** RA-2, RA-4, RA-5, RA-7

### RA-4: Evaluator + Recommender
- **Location:** `src/research_agent/evaluation/`, `src/research_agent/recommendations/`
- **Tests:** `tests/unit/test_recommendation_engine.py`
- **Dependencies:** RA-3

### RA-5: Graph Memory + Filesystem Store
- **Location:** `src/research_agent/memory/`
- **Tests:** `tests/unit/test_graph_memory_store.py`
- **Dependencies:** None

### RA-6: Plugin Registry (NEW — 009-claude-native-agent)
- **Location:** `src/research_agent/plugins/base.py`
- **Tests:** `tests/unit/test_plugin_registry.py`
- **Dependencies:** None
- **What changed:** Replaced LangChain `@tool` decorators with `ToolPlugin` ABC + `PluginRegistry`. Modular tool loading with failure isolation (`register_safe`).

### RA-7: Claude Agent (NEW — 009-claude-native-agent)
- **Location:** `src/research_agent/agent/claude_agent.py`, `src/research_agent/agent/prompts.py`
- **Tests:** `tests/unit/test_claude_agent.py`, `tests/unit/test_experiment_runner.py`
- **Dependencies:** RA-6, Anthropic SDK
- **What changed:** Replaced dead `create_research_agent()` (LangChain/DeepAgents) with `ClaudeAgent` using `anthropic.Anthropic.messages.create(tools=...)`. The agent reasons about which tools to call per hypothesis, tracks budget, and produces real experiment results.

### RA-8: Tool Plugins (NEW — 009-claude-native-agent)
- **Location:** `src/research_agent/plugins/scoring_plugin.py`, `dataforseo_plugin.py`, `metro_plugin.py`, `llm_plugin.py`
- **Tests:** `tests/unit/test_plugin_registry.py`, `tests/unit/test_scoring_plugin.py`
- **Dependencies:** M0 (DataForSEO), M1 (Metro DB), M3 (LLM), M7 (Scoring)
- **What changed:** Existing tool functions in `api_tools.py` refactored from `@tool`-decorated LangChain wrappers to plain functions. Four plugins wrap them with Anthropic-compatible schemas. ScoringPlugin calls M7 `compute_batch_scores()` for real experiments.

## Design Reference

Full architecture, loop semantics, plugin system, tool contracts, memory model, and failure modes are documented in `docs/research_agent_design.md`.

## Integration Points

- **Input:** M7 scoring output feeds hypothesis generation
- **Output:** Recommendations feed back to M7 parameter updates
- **Tools:** Plugin system wraps M0 (DataForSEO), M1 (Metro DB), M3 (LLM), M7 (Scoring) via plugin adapters
- **Agent:** ClaudeAgent uses Anthropic SDK tool-use for experiment reasoning

## Dependency Changes (009-claude-native-agent)

**Removed from `pyproject.toml`:**
- `deepagents`
- `langgraph`
- `langchain-core`
- `langchain-anthropic`

**Rationale:** These were entirely dead code. The `create_research_agent()` factory and `RESEARCH_TOOLS` list were never called by any live entrypoint. Replaced by Claude-native tool-use via the same `anthropic` SDK already used by the pipeline.

## Governance Note

Changes to the research agent after this baseline require:
1. An update to this baseline spec documenting what changed and why
2. Updates to `docs/research_agent_design.md`
3. Verification that plugin tool schemas match foundation module interfaces
