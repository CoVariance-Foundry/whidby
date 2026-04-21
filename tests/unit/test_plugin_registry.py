"""Tests for ToolPlugin ABC and PluginRegistry."""

from __future__ import annotations

import pytest

from src.research_agent.plugins.base import PluginRegistry, ToolPlugin


class _StubPlugin(ToolPlugin):
    """Minimal concrete plugin for testing."""

    def __init__(self, name: str = "stub", tools: list[dict] | None = None) -> None:
        self._name = name
        self._tools = tools or [
            {
                "name": "stub_tool",
                "description": "A stub tool",
                "input_schema": {
                    "type": "object",
                    "properties": {"x": {"type": "string"}},
                    "required": ["x"],
                },
            }
        ]

    @property
    def name(self) -> str:
        return self._name

    def tool_definitions(self) -> list[dict]:
        return self._tools

    def execute(self, tool_name: str, arguments: dict) -> dict:
        if tool_name == "stub_tool":
            return {"result": f"executed with {arguments}", "cost_usd": 0.0}
        raise KeyError(f"Unknown tool: {tool_name}")


class _SecondPlugin(ToolPlugin):
    @property
    def name(self) -> str:
        return "second"

    def tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "second_tool",
                "description": "Another tool",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

    def execute(self, tool_name: str, arguments: dict) -> dict:
        return {"result": "second", "cost_usd": 0.0}


class TestPluginRegistry:
    def test_register_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = _StubPlugin()
        registry.register(plugin)
        assert "stub" in registry.list_plugins()

    def test_tool_name_collision_raises(self) -> None:
        registry = PluginRegistry()
        registry.register(_StubPlugin(name="a"))
        with pytest.raises(ValueError, match="stub_tool"):
            registry.register(_StubPlugin(name="b"))

    def test_duplicate_plugin_name_raises(self) -> None:
        registry = PluginRegistry()
        registry.register(_StubPlugin(name="dup"))
        with pytest.raises(ValueError, match="dup"):
            registry.register(_StubPlugin(name="dup"))

    def test_execute_routes_to_correct_plugin(self) -> None:
        registry = PluginRegistry()
        registry.register(_StubPlugin())
        result = registry.execute("stub_tool", {"x": "hello"})
        assert result["result"] == "executed with {'x': 'hello'}"

    def test_get_tool_definitions_merges_all(self) -> None:
        registry = PluginRegistry()
        registry.register(_StubPlugin())
        registry.register(_SecondPlugin())
        defs = registry.get_tool_definitions()
        names = {d["name"] for d in defs}
        assert names == {"stub_tool", "second_tool"}

    def test_list_plugins(self) -> None:
        registry = PluginRegistry()
        registry.register(_StubPlugin())
        registry.register(_SecondPlugin())
        assert sorted(registry.list_plugins()) == ["second", "stub"]

    def test_execute_unknown_tool_raises(self) -> None:
        registry = PluginRegistry()
        registry.register(_StubPlugin())
        with pytest.raises(KeyError, match="nonexistent"):
            registry.execute("nonexistent", {})

    def test_register_safe_logs_failure(self) -> None:
        registry = PluginRegistry()
        registry.register(_StubPlugin(name="first"))
        success = registry.register_safe(_StubPlugin(name="second"))
        assert success is False  # tool name collision with stub_tool

    def test_register_safe_succeeds(self) -> None:
        registry = PluginRegistry()
        success = registry.register_safe(_StubPlugin())
        assert success is True


class TestDataForSEOPlugin:
    def test_tool_definitions_returns_expected_tools(self) -> None:
        from src.research_agent.plugins.dataforseo_plugin import DataForSEOPlugin

        plugin = DataForSEOPlugin()
        defs = plugin.tool_definitions()
        names = {d["name"] for d in defs}
        expected = {
            "fetch_serp_organic",
            "fetch_serp_maps",
            "fetch_keyword_volume",
            "fetch_keyword_suggestions",
            "fetch_business_listings",
            "fetch_google_reviews",
            "fetch_backlinks_summary",
            "fetch_lighthouse",
            "explore_serp_snapshot",
        }
        assert names == expected
        for d in defs:
            assert "input_schema" in d
            assert d["input_schema"]["type"] == "object"

    def test_name(self) -> None:
        from src.research_agent.plugins.dataforseo_plugin import DataForSEOPlugin

        assert DataForSEOPlugin().name == "dataforseo"


class TestMetroDBPlugin:
    def test_tool_definitions_returns_one_tool(self) -> None:
        from src.research_agent.plugins.metro_plugin import MetroDBPlugin

        plugin = MetroDBPlugin()
        defs = plugin.tool_definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "expand_geo_scope"

    def test_name(self) -> None:
        from src.research_agent.plugins.metro_plugin import MetroDBPlugin

        assert MetroDBPlugin().name == "metro"


class TestLLMPlugin:
    def test_tool_definitions_returns_three_tools(self) -> None:
        from src.research_agent.plugins.llm_plugin import LLMPlugin

        plugin = LLMPlugin()
        defs = plugin.tool_definitions()
        assert len(defs) == 3
        names = {d["name"] for d in defs}
        assert names == {"expand_keywords", "classify_search_intent", "llm_generate"}

    def test_name(self) -> None:
        from src.research_agent.plugins.llm_plugin import LLMPlugin

        assert LLMPlugin().name == "llm"


class TestPluginIsolation:
    def test_failed_plugin_does_not_block_others(self) -> None:
        registry = PluginRegistry()
        registry.register_safe(_StubPlugin())

        class _BadPlugin(ToolPlugin):
            @property
            def name(self) -> str:
                raise RuntimeError("init explosion")

            def tool_definitions(self) -> list[dict]:
                return []

            def execute(self, tool_name: str, arguments: dict) -> dict:
                return {}

        success = registry.register_safe(_BadPlugin())
        assert success is False
        assert "stub" in registry.list_plugins()
