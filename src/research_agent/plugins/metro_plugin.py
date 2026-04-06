"""MetroDB plugin wrapping geographic scope expansion."""

from __future__ import annotations

import json
from typing import Any

from src.research_agent.plugins.base import ToolPlugin
from src.research_agent.tools.api_tools import expand_geo_scope


class MetroDBPlugin(ToolPlugin):
    """Plugin exposing MetroDB geographic scope expansion as an agent tool."""

    @property
    def name(self) -> str:
        return "metro"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "expand_geo_scope",
                "description": (
                    "Expand a geographic scope into a list of metros with CBSA codes, "
                    "populations, and DataForSEO location codes."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "scope": {
                            "type": "string",
                            "enum": ["state", "region", "custom"],
                            "description": "Scope type",
                        },
                        "target": {
                            "type": "string",
                            "description": (
                                "State code, region name, or comma-separated CBSA codes"
                            ),
                        },
                        "depth": {
                            "type": "string",
                            "enum": ["standard", "deep"],
                            "description": "standard (top 20) or deep (all >= 50k pop)",
                        },
                    },
                    "required": ["scope", "target"],
                },
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name != "expand_geo_scope":
            raise KeyError(f"Unknown tool: '{tool_name}'")

        raw_json = expand_geo_scope(
            arguments["scope"],
            arguments["target"],
            arguments.get("depth", "standard"),
        )
        return {
            "data": json.loads(raw_json),
            "cost_usd": 0.0,
        }
