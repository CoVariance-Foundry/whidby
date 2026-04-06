# Tasks: Claude-Native Research Agent

**Input**: Design documents from `/specs/009-claude-native-agent/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per constitution (TDD lifecycle required).

**Organization**: Tasks grouped by user story. The PluginRegistry is foundational infrastructure that all stories depend on.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure, shared fixtures, and refactor existing code to remove LangChain decorators.

- [x] T001 Create plugin package structure: `src/research_agent/plugins/__init__.py`
- [x] T002 [P] Create agent package structure: `src/research_agent/agent/__init__.py`
- [x] T003 [P] Create shared test fixtures in `tests/fixtures/agent_fixtures.py` with mock hypothesis, baseline snapshot, and tool response data
- [x] T004 Remove `@tool` decorators and `from langchain_core.tools import tool` from `src/research_agent/tools/api_tools.py`; keep all plain functions and `ALL_TOOLS` list as plain function references

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ToolPlugin ABC and PluginRegistry — core infrastructure that MUST be complete before ANY user story can be implemented.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundation

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 Write tests for ToolPlugin ABC and PluginRegistry in `tests/unit/test_plugin_registry.py`: test register plugin, test tool name collision raises ValueError, test execute routes to correct plugin, test get_tool_definitions merges all plugins, test list_plugins, test execute unknown tool raises KeyError, test duplicate plugin name raises ValueError

### Implementation for Foundation

- [x] T006 Implement `ToolPlugin` abstract base class in `src/research_agent/plugins/base.py`: abstract property `name` (str), abstract method `tool_definitions()` returning `list[dict]`, abstract method `execute(tool_name: str, arguments: dict)` returning `dict`
- [x] T007 Implement `PluginRegistry` in `src/research_agent/plugins/base.py`: `register(plugin)` with tool name uniqueness enforcement, `get_tool_definitions()` merging all plugin tools, `execute(tool_name, arguments)` routing to correct plugin, `list_plugins()` returning registered names
- [x] T008 Verify T005 tests pass

**Checkpoint**: Foundation ready — plugin system can accept plugins and route tool calls.

---

## Phase 3: User Story 1 — Run a Real Scoring Experiment (Priority: P1) MVP

**Goal**: Replace the stub experiment runner with one that produces real candidate scores using M7's `compute_batch_scores()`. Parameter-only hypotheses re-score baseline signals with modifications and return non-zero deltas.

**Independent Test**: Run a research session with demo data and verify experiments produce non-zero composite score changes, cost_usd tracking, and per-proxy breakdown.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Write tests for ScoringPlugin in `tests/unit/test_scoring_plugin.py`: test `rescore_with_modifications` tool produces real scores from fixture signals, test output shape matches evaluator contract (`candidate_scores.metros[].scores.opportunity`), test cost_usd is 0.0 for parameter-only mode, test tool_definitions returns valid Anthropic-format schemas
- [x] T010 [P] [US1] Write tests for experiment runner in `tests/unit/test_experiment_runner.py`: test runner returns non-zero candidate scores given a parameter-modification hypothesis, test runner output satisfies ExperimentRunner type signature `Callable[[dict, FilesystemStore], dict]`, test runner loads baseline from FilesystemStore, test runner returns experiment_id and modifications, test full loop iteration with evaluator produces non-zero delta

### Implementation for User Story 1

- [x] T011 [US1] Implement ScoringPlugin in `src/research_agent/plugins/scoring_plugin.py`: `rescore_with_modifications` tool that takes baseline_signals + modifications + strategy_profile, applies signal overrides to copies, calls `compute_batch_scores()` from `src/scoring/engine.py`, wraps output into `candidate_scores.metros[].scores` shape per contracts/experiment-runner.md
- [x] T012 [US1] Implement `claude_experiment_runner` function in `src/research_agent/agent/__init__.py`: match `ExperimentRunner` signature `(hypothesis, fs) -> dict`, call `plan_experiment()` for modifications, load baseline from `fs.load_snapshot("baseline")`, create `PluginRegistry` with `ScoringPlugin`, call `rescore_with_modifications` tool, return result with `experiment_id`, `cost_usd`, `candidate_scores`, `modifications`, `tool_calls` audit log
- [x] T013 [US1] Wire `claude_experiment_runner` into `run_research_session()` in `src/research_agent/deep_agent.py`: replace `default_experiment_runner` with `claude_experiment_runner` import, remove `create_research_agent()` factory function, remove `from deepagents import create_deep_agent` import, keep `RESEARCH_SYSTEM_PROMPT` (will be moved in US3)
- [x] T014 [US1] Verify T009 and T010 tests pass; run existing tests `pytest tests/unit/test_research_agent_loop.py tests/unit/test_recommendation_engine.py -v` to confirm no regressions

**Checkpoint**: Research sessions now produce experiments with real non-zero score deltas. Fast-mode experiments complete in < 5 seconds with cost_usd: 0.0. Existing loop, evaluator, and recommender work unchanged.

---

## Phase 4: User Story 2 — Modular Tool Registration (Priority: P2)

**Goal**: Build DataForSEO, MetroDB, and LLM plugins so each data source is a self-contained module that registers tools independently. Demonstrate plugin isolation (one failure doesn't break others).

**Independent Test**: Create a minimal test plugin, register it, verify tool discovery and execution. Verify built-in plugins load and their tools are discoverable.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T015 [P] [US2] Write tests for DataForSEOPlugin in `tests/unit/test_plugin_registry.py` (append to existing): test tool_definitions returns 8 tools with correct Anthropic schemas, test execute dispatches to correct function, test execute returns cost_usd from API response
- [x] T016 [P] [US2] Write tests for MetroDBPlugin in `tests/unit/test_plugin_registry.py`: test tool_definitions returns 1 tool, test execute returns metro list with cost_usd: 0.0
- [x] T017 [P] [US2] Write tests for LLMPlugin in `tests/unit/test_plugin_registry.py`: test tool_definitions returns 3 tools, test execute returns cost_usd from LLMResult
- [x] T018 [P] [US2] Write plugin isolation test in `tests/unit/test_plugin_registry.py`: test that registering a plugin that raises during __init__ does not prevent other plugins from loading when using a safe registration helper

### Implementation for User Story 2

- [x] T019 [P] [US2] Implement DataForSEOPlugin in `src/research_agent/plugins/dataforseo_plugin.py`: wrap 8 tools (fetch_serp_organic, fetch_serp_maps, fetch_keyword_volume, fetch_keyword_suggestions, fetch_business_listings, fetch_google_reviews, fetch_backlinks_summary, fetch_lighthouse) using functions from `src/research_agent/tools/api_tools.py`, return structured dicts with cost_usd
- [x] T020 [P] [US2] Implement MetroDBPlugin in `src/research_agent/plugins/metro_plugin.py`: wrap `expand_geo_scope` using `_get_metro_db()` from api_tools.py, return metro list with cost_usd: 0.0
- [x] T021 [P] [US2] Implement LLMPlugin in `src/research_agent/plugins/llm_plugin.py`: wrap `expand_keywords`, `classify_search_intent`, `llm_generate` using `_get_llm_client()` from api_tools.py, return structured dicts with cost_usd from LLMResult
- [x] T022 [US2] Add `register_safe()` method to PluginRegistry in `src/research_agent/plugins/base.py`: wraps `register()` in try/except, logs error with `exc_info=True` on failure, returns bool success
- [x] T023 [US2] Update `claude_experiment_runner` in `src/research_agent/agent/__init__.py` to register all four plugins (DataForSEO, Metro, LLM, Scoring) using `register_safe()` so failures are isolated
- [x] T024 [US2] Verify T015-T018 tests pass; run full unit suite to confirm no regressions

**Checkpoint**: Four plugins registered independently. A test plugin can be added without modifying agent core. Plugin load failures are isolated and logged.

---

## Phase 5: User Story 3 — AI-Powered Experiment Reasoning (Priority: P3)

**Goal**: Build the Claude tool-use agent that reasons about which tools to call based on the hypothesis, tracks budget, handles tool failures, and returns structured experiment results.

**Independent Test**: Provide the agent with a hypothesis and mock tool registry; verify it selects appropriate tools, respects budget, and produces a valid experiment result.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T025 [P] [US3] Write tests for ClaudeAgent in `tests/unit/test_claude_agent.py`: test run_experiment with mocked Anthropic client returns valid experiment result, test tool-use loop executes tool calls via registry, test budget tracking stops agent when budget exceeded, test agent handles tool execution failure gracefully, test agent returns tool_calls audit log, test system prompt includes hypothesis context
- [x] T026 [P] [US3] Write tests for system prompt in `tests/unit/test_claude_agent.py`: test prompt includes scoring proxy dimensions, test prompt instructs fast-mode preference for parameter hypotheses

### Implementation for User Story 3

- [x] T027 [US3] Move `RESEARCH_SYSTEM_PROMPT` from `src/research_agent/deep_agent.py` to `src/research_agent/agent/prompts.py`; add instructions for tool selection reasoning (prefer `rescore_with_modifications` for parameter-only hypotheses, use `collect_extract_and_score` when fresh data needed), budget awareness, and structured output format
- [x] T028 [US3] Implement `ClaudeAgent` in `src/research_agent/agent/claude_agent.py`: constructor takes `PluginRegistry`, `api_key` (optional, from env), `model` (from constants), `max_tool_rounds` (default 10); `run_experiment(hypothesis, baseline, budget_remaining)` method implements tool-use loop: call `messages.create(tools=registry.get_tool_definitions())`, loop on `stop_reason=="tool_use"`, execute via registry, append `tool_result`, track cost, stop on `end_turn` or budget exceeded or max rounds
- [x] T029 [US3] Update `claude_experiment_runner` in `src/research_agent/agent/__init__.py` to use `ClaudeAgent.run_experiment()` instead of directly calling scoring plugin; pass budget_remaining from loop config
- [x] T030 [US3] Update `run_research_session` in `src/research_agent/deep_agent.py` to import from `src/research_agent/agent` and pass budget info to experiment runner; update `deep_agent.py` imports to reference `agent.prompts` for system prompt
- [x] T031 [US3] Verify T025-T026 tests pass; run full unit suite including existing loop and recommendation tests

**Checkpoint**: Agent reasons about tool selection, tracks costs, handles errors, and produces real experiment results. System works end-to-end: CLI -> session -> loop -> agent -> plugins -> M7 -> evaluator -> recommendations.

---

## Phase 6: User Story 4 — Dependency Cleanup (Priority: P4)

**Goal**: Remove dead LangChain/DeepAgents dependencies from pyproject.toml. Verify no import errors.

**Independent Test**: Remove dependencies, run full test suite, build Docker image.

- [x] T032 [US4] Remove `deepagents`, `langgraph`, `langchain-core`, `langchain-anthropic` from `pyproject.toml` dependencies list
- [x] T033 [US4] Remove remaining `langchain_core` imports from `src/research_agent/tools/api_tools.py` (verify T004 was complete), remove `RESEARCH_TOOLS` list and `ALL_TOOLS` re-export from `src/research_agent/deep_agent.py` if no longer needed
- [x] T034 [US4] Run `pip install -e ".[dev]"` to verify clean install without removed packages
- [x] T035 [US4] Run full test suite `pytest tests/unit/ -v` to verify no import errors or test failures
- [x] T036 [US4] Build Docker image `docker build -f Dockerfile.api -t widby-api-test .` and verify it starts: `docker run --rm -e PORT=8000 widby-api-test`

**Checkpoint**: All unused framework dependencies removed. Install is cleaner, Docker builds successfully, all tests pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and validation

- [x] T037 [P] Update `docs/research_agent_design.md` to reflect new architecture: replace LangChain/DeepAgents references with Claude-native tool-use + plugin registry; update architecture diagram, tool contracts section, and deployment notes
- [x] T038 [P] Update `docs/deep_agent_deployment_audit.md` to reflect resolved gaps: real experiment runner, dependency cleanup, active tool execution
- [x] T039 Run quickstart.md validation: execute each command from `specs/009-claude-native-agent/quickstart.md` and verify outputs
- [x] T040 Run `ruff check src/research_agent/ tests/unit/test_plugin_registry.py tests/unit/test_claude_agent.py tests/unit/test_scoring_plugin.py tests/unit/test_experiment_runner.py` to verify code quality

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — can start after PluginRegistry is implemented
- **US2 (Phase 4)**: Depends on Phase 2 — can run in parallel with US1 (different files)
- **US3 (Phase 5)**: Depends on Phase 3 (US1) and Phase 4 (US2) — needs all plugins and experiment runner
- **US4 (Phase 6)**: Depends on Phase 5 (US3) — cleanup after all LangChain references removed
- **Polish (Phase 7)**: Depends on Phase 6 — final validation

### User Story Dependencies

- **US1 (P1)**: Needs PluginRegistry + ScoringPlugin only. No dependency on other stories.
- **US2 (P2)**: Needs PluginRegistry only. Can run in parallel with US1.
- **US3 (P3)**: Needs US1 (experiment runner) + US2 (all plugins). Must follow both.
- **US4 (P4)**: Can run after US3 (all LangChain imports removed by then).

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Plugin implementations before agent integration
- Core implementation before wiring into deep_agent.py
- Story complete before moving to next priority

### Parallel Opportunities

- T001, T002, T003 (Phase 1 setup) — all parallel
- T009, T010 (US1 tests) — parallel
- T015, T016, T017, T018 (US2 tests) — all parallel
- T019, T020, T021 (US2 plugin implementations) — all parallel
- T025, T026 (US3 tests) — parallel
- T037, T038 (Polish docs) — parallel
- US1 and US2 can proceed in parallel after Phase 2

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Write tests for ScoringPlugin in tests/unit/test_scoring_plugin.py"
Task: "Write tests for experiment runner in tests/unit/test_experiment_runner.py"

# After tests written, implement ScoringPlugin:
Task: "Implement ScoringPlugin in src/research_agent/plugins/scoring_plugin.py"
```

## Parallel Example: User Story 2

```bash
# Launch all US2 tests together:
Task: "Write tests for DataForSEOPlugin"
Task: "Write tests for MetroDBPlugin"
Task: "Write tests for LLMPlugin"
Task: "Write plugin isolation test"

# Launch all US2 implementations together:
Task: "Implement DataForSEOPlugin in src/research_agent/plugins/dataforseo_plugin.py"
Task: "Implement MetroDBPlugin in src/research_agent/plugins/metro_plugin.py"
Task: "Implement LLMPlugin in src/research_agent/plugins/llm_plugin.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (PluginRegistry)
3. Complete Phase 3: User Story 1 (ScoringPlugin + experiment runner)
4. **STOP and VALIDATE**: Run research session, verify non-zero deltas
5. Deploy/demo if ready — the agent now produces real experiment results

### Incremental Delivery

1. Setup + Foundational → Plugin system ready
2. Add US1 → Real experiments with fast-mode scoring (MVP!)
3. Add US2 → All data sources as modular plugins
4. Add US3 → AI-powered tool selection and reasoning
5. Add US4 → Clean dependency footprint
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
