# Quickstart: Claude-Native Research Agent

**Date**: 2026-04-04
**Branch**: `009-claude-native-agent`

## Prerequisites

- Python 3.11+
- `ANTHROPIC_API_KEY` environment variable (required for agent reasoning and full-mode experiments)
- `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` (required for full-mode experiments only; fast-mode works without)

## Install

```bash
cd main/
pip install -e ".[dev]"
```

After dependency cleanup, the install no longer requires `deepagents`, `langgraph`, `langchain-core`, or `langchain-anthropic`.

## Run a Research Session (CLI)

```bash
# Fast-mode only (no API keys needed beyond ANTHROPIC_API_KEY)
python -m src.research_agent.run_research_agent --max-iterations 3

# Full-mode with real data
python -m src.research_agent.run_research_agent \
    --scoring-input path/to/scores.json \
    --max-iterations 5 \
    --budget 10.0 \
    --graph-path research_graph.json \
    --output report.md
```

## Run via API (Docker)

```bash
npm run dev:api          # Docker with hot-reload
# OR
npm run dev:api:local    # Local uvicorn
```

Then start a session:

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"max_iterations": 3, "budget_limit_usd": 10.0}'
```

## Run Tests

```bash
# All research agent tests (no API keys needed)
pytest tests/unit/test_plugin_registry.py -v
pytest tests/unit/test_claude_agent.py -v
pytest tests/unit/test_scoring_plugin.py -v
pytest tests/unit/test_experiment_runner.py -v

# Full suite
pytest tests/unit/ -v
```

## Development: Adding a New Plugin

1. Create `src/research_agent/plugins/my_plugin.py`
2. Subclass `ToolPlugin`:

```python
from src.research_agent.plugins.base import ToolPlugin

class MyPlugin(ToolPlugin):
    @property
    def name(self) -> str:
        return "my_plugin"

    def tool_definitions(self) -> list[dict]:
        return [{
            "name": "my_tool",
            "description": "Does something useful",
            "input_schema": {
                "type": "object",
                "properties": {
                    "param": {"type": "string", "description": "Input parameter"}
                },
                "required": ["param"]
            }
        }]

    def execute(self, tool_name: str, arguments: dict) -> dict:
        if tool_name == "my_tool":
            result = do_something(arguments["param"])
            return {"data": result, "cost_usd": 0.0}
        raise ValueError(f"Unknown tool: {tool_name}")
```

3. Register in the session setup (or add to default plugin list in `deep_agent.py`)

## Key File Locations

| File | Purpose |
|------|---------|
| `src/research_agent/plugins/base.py` | `ToolPlugin` ABC + `PluginRegistry` |
| `src/research_agent/plugins/*.py` | Built-in plugins (DataForSEO, Metro, LLM, Scoring) |
| `src/research_agent/agent/claude_agent.py` | Claude tool-use agent loop |
| `src/research_agent/agent/prompts.py` | System prompt |
| `src/research_agent/deep_agent.py` | Session orchestrator (wires agent into Ralph loop) |
| `specs/009-claude-native-agent/contracts/experiment-runner.md` | Experiment runner I/O contract |
