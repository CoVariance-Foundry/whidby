# Research: Claude-Native Research Agent

**Date**: 2026-04-04
**Branch**: `009-claude-native-agent`

## Research Questions

### RQ1: How does Anthropic SDK tool-use work?

**Decision**: Use `anthropic.Anthropic.messages.create()` with `tools=` parameter and manual tool-use loop. Do not use `client.beta.messages.tool_runner()` (beta API, adds dependency on unstable interface).

**Rationale**: The stable tool-use API is straightforward:
1. Define tools as list of `ToolParam` dicts with `name`, `description`, `input_schema`
2. Call `messages.create()` with `tools=` and `messages=`
3. Check `message.stop_reason == "tool_use"`
4. Extract `tool_use` blocks from `message.content`, execute them
5. Append assistant response + `tool_result` user messages
6. Repeat until `stop_reason == "end_turn"`

The `tool_runner` beta automates this loop but ties us to an unstable API. Our loop is simple enough (budget-aware, logged) that a manual implementation gives us more control.

**Alternatives considered**:
- `client.beta.messages.tool_runner()`: Auto-runs tool loop with `@beta_tool` decorators. Rejected: beta stability concern, less control over budget/logging, adds decorator coupling.
- LangChain tool-use agent: Already proven to be dead code. Rejected: violates constitution III (no frameworks).

### RQ2: How should plugins define tool schemas?

**Decision**: Each plugin returns a list of Anthropic `ToolParam`-compatible dicts from its `tool_definitions()` method. The schema follows the standard JSON Schema format that Anthropic expects.

**Rationale**: Anthropic's tool format is:
```python
{
    "name": "tool_name",
    "description": "What the tool does",
    "input_schema": {
        "type": "object",
        "properties": { ... },
        "required": [...]
    }
}
```

This is a plain dict -- no special types needed. Plugins produce these dicts, the registry collects them, and the agent passes them to `messages.create(tools=...)`.

**Alternatives considered**:
- Pydantic models for tool schemas: Adds complexity without benefit since Anthropic API takes raw dicts. Rejected: YAGNI per constitution VI.
- Separate schema files (JSON/YAML): Adds indirection. Schemas are small and best co-located with the plugin code. Rejected.

### RQ3: How should the experiment runner bridge M7 output to evaluator input?

**Decision**: The experiment runner wraps `compute_batch_scores()` output into the `candidate_scores.metros[].scores` shape that `evaluator.py` expects.

**Rationale**: The evaluator's `_extract_composites()` reads:
```python
snapshot.get("metros", snapshot.get("candidate_scores", {}).get("metros", []))
```
And per-proxy comparison reads `scores.demand`, `scores.organic_competition`, etc.

M7's `compute_scores()` output already has these exact keys (`demand`, `organic_competition`, `local_competition`, `monetization`, `ai_resilience`, `opportunity`). The bridge is a simple list comprehension wrapping each metro's M7 output into `{"scores": m7_result, "cbsa_code": metro_id}`.

**Alternatives considered**:
- Modify the evaluator to accept M7 output directly: Would break existing tests and API contract (FR-012). Rejected.
- Create an adapter layer between M7 and evaluator: Over-engineering for a one-line transform. Rejected.

### RQ4: How should fast-mode vs full-mode be determined?

**Decision**: The Claude agent decides based on hypothesis context. Hypotheses with `approach` values like `keyword_expansion_tuning`, `da_ceiling_adjustment`, `review_barrier_recalibration`, `cpc_floor_adjustment`, `aio_rate_threshold_tuning` are parameter-only (fast mode). Hypotheses with `approach` values implying data changes trigger full mode.

**Rationale**: The hypothesis generator in `generator.py` already classifies approaches. Most current approaches (10 out of 10 defined in `experiment_planner.py`) modify scoring parameters, not data inputs. The agent's system prompt instructs it to prefer fast mode when the hypothesis only changes scoring parameters.

As a fallback, the scoring plugin provides both a `rescore_with_modifications` tool (fast) and a `collect_and_score` tool (full). The agent picks the right one based on its reasoning.

**Alternatives considered**:
- Hardcoded mode selection based on `approach` string: Brittle, breaks when new approaches are added. Rejected.
- Always run full mode: Wastes API budget on parameter-only hypotheses. Rejected.

### RQ5: How should tool call costs be tracked?

**Decision**: Each plugin's `execute()` method returns a result dict that includes `cost_usd`. The agent accumulates costs across tool calls. DataForSEO tools report cost from the `APIResponse.cost` field. Scoring-only tools report 0. The total is included in the experiment result.

**Rationale**: The existing `DataForSEOClient` already tracks cost per call via `CostTracker`. The `APIResponse` dataclass has a `cost` field. Plugins surface this in their return value. The agent sums costs and the experiment runner includes the total.

**Alternatives considered**:
- Centralized cost tracker in the registry: Adds shared state. Each plugin already knows its own cost. Rejected: unnecessary coupling.

### RQ6: What happens to the existing `api_tools.py` functions?

**Decision**: Remove the `@tool` decorator and `langchain_core.tools` import. Keep the plain functions (e.g. `fetch_serp_organic`, `expand_geo_scope`, `expand_keywords`) as internal implementation that plugins call. The functions themselves are correct and tested -- only the LangChain wrapper layer is removed.

**Rationale**: The functions in `api_tools.py` are thin wrappers around existing clients. They handle async-to-sync bridging (`_run_async`) and JSON serialization. Plugins call these same functions but return structured dicts instead of JSON strings.

**Alternatives considered**:
- Inline the functions into each plugin: Would duplicate the async bridging logic. Rejected.
- Delete `api_tools.py` entirely: Would lose the convenient client factory functions (`_get_dfs_client`, etc.). Rejected.
