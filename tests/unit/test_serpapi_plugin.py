"""Unit tests for SerpAPIPlugin (Task 2 of 012-recipe-reports)."""

from __future__ import annotations

import json

import pytest

from src.research_agent.plugins.serpapi_plugin import SerpAPIPlugin


class TestSerpAPIPlugin:
    def test_name_is_serpapi(self):
        assert SerpAPIPlugin().name == "serpapi"

    def test_tool_definitions_returns_two_schemas(self):
        defs = SerpAPIPlugin().tool_definitions()
        assert len(defs) == 2
        names = {d["name"] for d in defs}
        assert names == {"fetch_serpapi_google", "fetch_serpapi_maps"}

    def test_tool_definitions_have_required_anthropic_fields(self):
        for d in SerpAPIPlugin().tool_definitions():
            assert "name" in d
            assert "description" in d
            assert "input_schema" in d
            assert d["input_schema"]["type"] == "object"
            assert "properties" in d["input_schema"]
            assert "required" in d["input_schema"]

    def test_google_tool_required_fields(self):
        defs = SerpAPIPlugin().tool_definitions()
        google = next(d for d in defs if d["name"] == "fetch_serpapi_google")
        required = google["input_schema"]["required"]
        assert "keyword" in required
        assert "location" in required

    def test_maps_tool_required_fields(self):
        defs = SerpAPIPlugin().tool_definitions()
        maps = next(d for d in defs if d["name"] == "fetch_serpapi_maps")
        required = maps["input_schema"]["required"]
        assert "keyword" in required
        assert "ll" in required

    def test_execute_google_dispatches(self, mocker):
        fake = mocker.patch(
            "src.research_agent.plugins.serpapi_plugin.fetch_serpapi_google",
            return_value=json.dumps(
                {"status": "ok", "data": {"organic_results": []}, "cost": 0.01}
            ),
        )
        plugin = SerpAPIPlugin()
        result = plugin.execute(
            "fetch_serpapi_google",
            {"keyword": "plumber", "location": "Austin, Texas, United States"},
        )
        fake.assert_called_once_with("plumber", "Austin, Texas, United States", "us", "en")
        assert result == {
            "data": {"organic_results": []},
            "cost_usd": 0.01,
            "status": "ok",
        }

    def test_execute_google_with_custom_gl_hl(self, mocker):
        fake = mocker.patch(
            "src.research_agent.plugins.serpapi_plugin.fetch_serpapi_google",
            return_value=json.dumps({"status": "ok", "data": {}, "cost": 0.01}),
        )
        SerpAPIPlugin().execute(
            "fetch_serpapi_google",
            {"keyword": "cafe", "location": "Paris, France", "gl": "fr", "hl": "fr"},
        )
        fake.assert_called_once_with("cafe", "Paris, France", "fr", "fr")

    def test_execute_maps_dispatches(self, mocker):
        fake = mocker.patch(
            "src.research_agent.plugins.serpapi_plugin.fetch_serpapi_maps",
            return_value=json.dumps(
                {"status": "ok", "data": {"local_results": []}, "cost": 0.01}
            ),
        )
        plugin = SerpAPIPlugin()
        result = plugin.execute(
            "fetch_serpapi_maps",
            {"keyword": "plumber", "ll": "@40.7128,-74.0060,14z"},
        )
        fake.assert_called_once_with("plumber", "@40.7128,-74.0060,14z")
        assert result == {
            "data": {"local_results": []},
            "cost_usd": 0.01,
            "status": "ok",
        }

    def test_unknown_tool_raises_keyerror(self):
        with pytest.raises(KeyError, match="bogus"):
            SerpAPIPlugin().execute("bogus", {})
