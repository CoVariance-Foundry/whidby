"""SerpAPI plugin wrapping the SerpAPIClient via api_tools facades."""

from __future__ import annotations

import json
from typing import Any

from src.research_agent.plugins.base import ToolPlugin
from src.research_agent.tools.api_tools import (
    fetch_serpapi_google,
    fetch_serpapi_maps,
)


class SerpAPIPlugin(ToolPlugin):
    """Plugin exposing SerpAPI Google + Google Maps engines as agent tools."""

    @property
    def name(self) -> str:
        return "serpapi"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "fetch_serpapi_google",
                "description": (
                    "Fetch SerpAPI Google results (organic, ads, local_pack, "
                    "ai_overview) for a keyword at a location."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Search query"},
                        "location": {
                            "type": "string",
                            "description": (
                                "SerpAPI location string "
                                "(e.g. 'Austin, Texas, United States')"
                            ),
                        },
                        "gl": {
                            "type": "string",
                            "description": "Country code (default 'us')",
                        },
                        "hl": {
                            "type": "string",
                            "description": "UI language (default 'en')",
                        },
                    },
                    "required": ["keyword", "location"],
                },
            },
            {
                "name": "fetch_serpapi_maps",
                "description": (
                    "Fetch Google Maps results via SerpAPI for a keyword at "
                    "a lat/lng location."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Search query"},
                        "ll": {
                            "type": "string",
                            "description": (
                                "Lat/lng/zoom string "
                                "(e.g. '@40.7128,-74.0060,14z')"
                            ),
                        },
                    },
                    "required": ["keyword", "ll"],
                },
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        dispatch = {
            "fetch_serpapi_google": lambda a: fetch_serpapi_google(
                a["keyword"],
                a["location"],
                a.get("gl", "us"),
                a.get("hl", "en"),
            ),
            "fetch_serpapi_maps": lambda a: fetch_serpapi_maps(
                a["keyword"], a["ll"]
            ),
        }
        if tool_name not in dispatch:
            raise KeyError(f"Unknown tool: '{tool_name}'")

        raw_json = dispatch[tool_name](arguments)
        parsed = json.loads(raw_json)
        return {
            "data": parsed.get("data"),
            "cost_usd": parsed.get("cost", 0.0),
            "status": parsed.get("status", "ok"),
        }
