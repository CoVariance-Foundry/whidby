# Data Model: Claude-Native Research Agent

**Date**: 2026-04-04
**Branch**: `009-claude-native-agent`

## Entity Definitions

### ToolPlugin (ABC)

The base class for all tool plugins. Each plugin encapsulates a set of related tools.

| Field | Type | Description |
|-------|------|-------------|
| name | str (property) | Unique plugin identifier (e.g. "dataforseo", "scoring") |

| Method | Signature | Description |
|--------|-----------|-------------|
| tool_definitions | () -> list[dict] | Returns Anthropic-format tool schema dicts |
| execute | (tool_name: str, arguments: dict) -> dict | Dispatches a tool call, returns result with optional cost_usd |

### PluginRegistry

Central catalog of loaded plugins. Resolves tool names to plugins.

| Field | Type | Description |
|-------|------|-------------|
| _plugins | dict[str, ToolPlugin] | Map of plugin name -> plugin instance |
| _tool_map | dict[str, str] | Map of tool name -> plugin name (for dispatch) |

| Method | Signature | Description |
|--------|-----------|-------------|
| register | (plugin: ToolPlugin) -> None | Add a plugin; raises on tool name collision |
| get_tool_definitions | () -> list[dict] | Merged tool definitions from all plugins |
| execute | (tool_name: str, arguments: dict) -> dict | Route to correct plugin, raises if tool unknown |
| list_plugins | () -> list[str] | Plugin names |

**Validation rules:**
- Tool names must be unique across all registered plugins (enforced at `register()` time)
- Plugin names must be unique (enforced at `register()` time)

### ClaudeAgent

The AI reasoning component using Anthropic SDK tool-use.

| Field | Type | Description |
|-------|------|-------------|
| _client | anthropic.Anthropic | SDK client instance |
| _registry | PluginRegistry | Tool plugin registry |
| _model | str | Model name (from constants) |
| _system_prompt | str | Research agent system prompt |
| _max_tool_rounds | int | Max tool-use loop iterations (default 10) |

| Method | Signature | Description |
|--------|-----------|-------------|
| run_experiment | (hypothesis: dict, baseline: dict, budget_remaining: float) -> dict | Execute a full experiment via tool-use reasoning |

### ToolCallRecord

Audit log entry for a single tool invocation.

| Field | Type | Description |
|-------|------|-------------|
| tool_name | str | Name of the tool called |
| arguments | dict | Input arguments |
| result | dict | Output result |
| cost_usd | float | Cost incurred (0.0 for free tools) |
| latency_ms | int | Execution time in milliseconds |
| timestamp | str | ISO 8601 UTC timestamp |

### ExperimentResult

Output from the experiment runner. Must satisfy the `ExperimentRunner` return type.

| Field | Type | Description |
|-------|------|-------------|
| experiment_id | str | Unique experiment identifier |
| cost_usd | float | Total cost across all tool calls |
| modifications | list[dict] | Parameter modifications applied |
| candidate_scores | dict | Nested `{"metros": [{"scores": {...}, "cbsa_code": str}]}` |
| tool_calls | list[ToolCallRecord] | Audit trail of all tool invocations |
| plan | dict | Experiment plan from experiment_planner |

## Data Flow

```
hypothesis (dict)
    │
    ▼
ClaudeAgent.run_experiment()
    │
    ├── messages.create(tools=registry.get_tool_definitions())
    │       │
    │       ▼ (tool_use stop_reason)
    │   PluginRegistry.execute(tool_name, args)
    │       │
    │       ├── DataForSEOPlugin → DataForSEOClient → raw API data
    │       ├── MetroDBPlugin → MetroDB → metro records
    │       ├── LLMPlugin → LLMClient → keyword/intent data
    │       └── ScoringPlugin → extract_signals() + compute_batch_scores() → scores
    │       │
    │       ▼ (tool_result appended to messages)
    │   [loop until end_turn or budget exceeded]
    │
    ▼
ExperimentResult (dict)
    │
    ▼
RalphResearchLoop (existing)
    ├── evaluator compares baseline vs candidate_scores
    ├── records to FilesystemStore
    └── promotes to ResearchGraphStore
```

## Plugin Tool Inventories

### DataForSEOPlugin

| Tool Name | Wraps | Input | Output |
|-----------|-------|-------|--------|
| fetch_serp_organic | DataForSEOClient.serp_organic | keyword, location_code, depth | SERP results + cost_usd |
| fetch_serp_maps | DataForSEOClient.serp_maps | keyword, location_code, depth | Maps results + cost_usd |
| fetch_keyword_volume | DataForSEOClient.keyword_volume | keywords, location_code | Volume data + cost_usd |
| fetch_keyword_suggestions | DataForSEOClient.keyword_suggestions | keyword, location_name, limit | Suggestions + cost_usd |
| fetch_business_listings | DataForSEOClient.business_listings | category, location_code, limit | Listings + cost_usd |
| fetch_google_reviews | DataForSEOClient.google_reviews | keyword, location_code, depth | Reviews + cost_usd |
| fetch_backlinks_summary | DataForSEOClient.backlinks_summary | target | Backlinks + cost_usd |
| fetch_lighthouse | DataForSEOClient.lighthouse | url | Audit + cost_usd |

### MetroDBPlugin

| Tool Name | Wraps | Input | Output |
|-----------|-------|-------|--------|
| expand_geo_scope | MetroDB.expand_scope | scope, target, depth | Metro list (cost_usd: 0) |

### LLMPlugin

| Tool Name | Wraps | Input | Output |
|-----------|-------|-------|--------|
| expand_keywords | LLMClient.keyword_expansion | niche | Keyword set + cost_usd |
| classify_search_intent | LLMClient.classify_intent | query | Intent label + cost_usd |
| llm_generate | LLMClient.generate | system_prompt, user_prompt | Text + cost_usd |

### ScoringPlugin

| Tool Name | Wraps | Input | Output |
|-----------|-------|-------|--------|
| rescore_with_modifications | compute_batch_scores | baseline_signals, modifications, strategy_profile | Candidate scores (cost_usd: 0) |
| collect_extract_and_score | collect_data + extract_signals + compute_batch_scores | keywords, metros, strategy_profile | Candidate scores + cost_usd |

## Existing Entities (Unchanged)

These entities are consumed but not modified by this feature:

- **LoopConfig**: Max iterations, budget, run ID, paths
- **IterationResult**: Per-iteration outcome with delta, validated flag
- **LoopOutcome**: Final session outcome with stop reason
- **FilesystemStore**: Per-run artifact persistence
- **ResearchGraphStore**: NetworkX knowledge graph
- **GraphNode / GraphEdge**: Typed graph entities
