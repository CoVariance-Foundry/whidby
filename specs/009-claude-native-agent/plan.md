# Implementation Plan: Claude-Native Research Agent

**Branch**: `009-claude-native-agent` | **Date**: 2026-04-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-claude-native-agent/spec.md`

## Summary

Replace the dead LangChain/DeepAgents orchestration with a Claude-native tool-use agent. Build a plugin registry for modular tool loading, and implement a real experiment runner that calls the existing M5/M6/M7 pipeline to produce actual candidate scores with accurate cost tracking. Remove unused framework dependencies.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `anthropic` (existing), `networkx` (existing), `httpx` (existing), `pydantic>=2` (existing)
**Storage**: Filesystem (per-run artifacts in `research_runs/`), JSON graph (`research_graph.json`)
**Testing**: `pytest` with `pytest-asyncio`, `pytest-mock`
**Target Platform**: Linux server (Docker), macOS local dev
**Project Type**: Backend pipeline module within existing monorepo
**Performance Goals**: Fast-mode experiments < 5 seconds; tool-use loop < 30s per iteration
**Constraints**: Budget-aware ($50 USD default per session); unit tests must run without API keys
**Scale/Scope**: 3-5 metros per experiment, 10 iterations per session max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-Driven, TDD | PASS | Spec artifact created; tests written first per lifecycle |
| II. Module-First Architecture | PASS | Plugin registry extends module boundaries; existing M5/M6/M7 untouched |
| III. No Framework | PASS | Constitution v1.1.0 updated: Research Agent now uses same Anthropic SDK as pipeline, no framework exception |
| IV. Code Quality | PASS | All code will follow ruff, type hints, Google docstrings |
| V. Documentation as Code | PASS | Plan, research, data-model, contracts artifacts generated |
| VI. Simplicity and Determinism | PASS | Agent is a utility within the loop, not the orchestrator; Ralph loop remains deterministic |

## Project Structure

### Documentation (this feature)

```text
specs/009-claude-native-agent/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── experiment-runner.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/research_agent/
├── __init__.py
├── deep_agent.py              # MODIFY: remove LangChain, wire new runner
├── run_research_agent.py      # unchanged
├── api.py                     # unchanged
├── plugins/                   # NEW: plugin system
│   ├── __init__.py
│   ├── base.py                # ToolPlugin ABC + PluginRegistry
│   ├── dataforseo_plugin.py   # wraps DataForSEOClient
│   ├── metro_plugin.py        # wraps MetroDB
│   ├── llm_plugin.py          # wraps LLMClient
│   └── scoring_plugin.py      # wraps M5/M6/M7 pipeline
├── agent/                     # NEW: Claude tool-use agent
│   ├── __init__.py
│   ├── claude_agent.py        # tool-use loop
│   └── prompts.py             # system prompt (moved from deep_agent.py)
├── tools/
│   └── api_tools.py           # MODIFY: remove @tool decorators, keep plain functions
├── hypothesis/                # unchanged
├── evaluation/                # unchanged
├── recommendations/           # unchanged
├── loop/                      # unchanged
└── memory/                    # unchanged

tests/
├── unit/
│   ├── test_plugin_registry.py    # NEW
│   ├── test_claude_agent.py       # NEW
│   ├── test_scoring_plugin.py     # NEW
│   ├── test_experiment_runner.py  # NEW
│   └── ... (existing tests unchanged)
└── fixtures/
    └── agent_fixtures.py          # NEW: mock tool responses
```

**Structure Decision**: Extends existing `src/research_agent/` with two new subpackages (`plugins/`, `agent/`). No new top-level directories. Test files follow existing `tests/unit/test_{module}.py` convention.

## Design Decisions

### D1: Plugin Interface

Each plugin is a class inheriting from `ToolPlugin` ABC with three responsibilities:

1. **`name`** property: unique plugin identifier string
2. **`tool_definitions()`**: returns list of Anthropic-format tool schema dicts (`{"name": ..., "description": ..., "input_schema": {...}}`)
3. **`execute(tool_name, args)`**: dispatches a tool call and returns a result dict

The `PluginRegistry` holds loaded plugins, merges tool definitions for the agent, and routes `execute` calls by tool name. Tool name uniqueness is enforced at registration time.

### D2: Claude Agent Tool-Use Loop

The agent uses `anthropic.Anthropic.messages.create()` with `tools=` parameter. The loop:

1. Send user message (hypothesis context + baseline data) with all tool definitions
2. If response has `stop_reason="tool_use"`: extract tool calls, execute each via registry, append `tool_result` content blocks
3. Repeat until `stop_reason="end_turn"` or budget exceeded or max iterations
4. Parse final response for structured experiment result

Temperature: 0 for deterministic tool selection. Model: `claude-sonnet-4-20250514` (from constants).

### D3: Experiment Runner Modes

The `claude_experiment_runner` callable matches the existing `ExperimentRunner = Callable[[dict, FilesystemStore], dict]` signature. Internally:

**Fast mode** (parameter-only):
- Loads baseline signals from `FilesystemStore` snapshot
- Applies hypothesis modifications to signal dict copies
- Calls `compute_batch_scores()` directly
- Returns `cost_usd: 0.0` with real scores

**Full mode** (data refresh):
- Agent calls DataForSEO tools via plugins to gather fresh data
- Calls `extract_signals()` on raw data
- Calls `compute_batch_scores()` on extracted signals
- Tracks cumulative `cost_usd` from tool responses

The agent decides which mode by reasoning about the hypothesis type. Parameter-only hypotheses (modify ceilings/floors/weights) use fast mode. Data-dependent hypotheses (expand keywords, add metros) use full mode.

### D4: Output Contract Bridge

M7 `compute_scores()` returns:
```python
{"demand": float, "organic_competition": float, "local_competition": float,
 "monetization": float, "ai_resilience": float, "opportunity": float,
 "confidence": dict, "resolved_weights": dict}
```

The evaluator expects:
```python
{"candidate_scores": {"metros": [{"scores": {"opportunity": float, ...}}, ...]}}
```

The experiment runner bridges this by wrapping M7 output:
```python
{
    "cost_usd": total_cost,
    "candidate_scores": {
        "metros": [
            {"scores": compute_scores_result, "cbsa_code": metro_id}
            for metro_id, compute_scores_result in scored_metros
        ]
    },
    "modifications": plan["modifications"],
    "experiment_id": plan["experiment_id"],
    "tool_calls": [...],  # audit log
}
```

### D5: Dependency Removal

Remove from `pyproject.toml`:
- `deepagents`
- `langgraph`
- `langchain-core`
- `langchain-anthropic`

Remove all `from langchain_core.tools import tool` imports. Convert `@tool`-decorated functions to plain functions. The `anthropic` package is already a dependency and remains.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
