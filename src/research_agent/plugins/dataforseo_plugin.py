"""DataForSEO plugin wrapping the existing DataForSEOClient via api_tools functions."""

from __future__ import annotations

import json
from typing import Any

from src.research_agent.plugins.base import ToolPlugin
from src.research_agent.tools.api_tools import (
    fetch_backlinks_summary,
    fetch_business_listings,
    fetch_google_reviews,
    fetch_keyword_suggestions,
    fetch_keyword_volume,
    fetch_lighthouse,
    fetch_serp_maps,
    fetch_serp_organic,
)


class DataForSEOPlugin(ToolPlugin):
    """Plugin exposing DataForSEO API endpoints as agent-callable tools."""

    @property
    def name(self) -> str:
        return "dataforseo"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "fetch_serp_organic",
                "description": "Fetch organic SERP results for a keyword at a location.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Search query"},
                        "location_code": {"type": "integer", "description": "DataForSEO location code"},
                        "depth": {"type": "integer", "description": "Number of results (default 10)"},
                    },
                    "required": ["keyword", "location_code"],
                },
            },
            {
                "name": "fetch_serp_maps",
                "description": "Fetch Google Maps SERP results for a keyword at a location.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "location_code": {"type": "integer"},
                        "depth": {"type": "integer"},
                    },
                    "required": ["keyword", "location_code"],
                },
            },
            {
                "name": "fetch_keyword_volume",
                "description": "Fetch search volume metrics for a list of keywords.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "location_code": {"type": "integer"},
                    },
                    "required": ["keywords", "location_code"],
                },
            },
            {
                "name": "fetch_keyword_suggestions",
                "description": "Fetch keyword suggestions related to a seed keyword.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "location_name": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["keyword"],
                },
            },
            {
                "name": "fetch_business_listings",
                "description": "Fetch business listings for a category in a location.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "location_code": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["category", "location_code"],
                },
            },
            {
                "name": "fetch_google_reviews",
                "description": "Fetch Google review data for a keyword/location.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "location_code": {"type": "integer"},
                        "depth": {"type": "integer"},
                    },
                    "required": ["keyword", "location_code"],
                },
            },
            {
                "name": "fetch_backlinks_summary",
                "description": "Fetch backlink summary for a target domain.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Domain or URL"},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "fetch_lighthouse",
                "description": "Run a Lighthouse performance audit on a URL.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "explore_serp_snapshot",
                "description": (
                    "Fetch a concise organic SERP snapshot for exploration follow-up."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "location_code": {"type": "integer"},
                        "depth": {"type": "integer"},
                    },
                    "required": ["keyword", "location_code"],
                },
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        dispatch = {
            "fetch_serp_organic": lambda a: fetch_serp_organic(
                a["keyword"], a["location_code"], a.get("depth", 10)
            ),
            "fetch_serp_maps": lambda a: fetch_serp_maps(
                a["keyword"], a["location_code"], a.get("depth", 10)
            ),
            "fetch_keyword_volume": lambda a: fetch_keyword_volume(
                a["keywords"], a["location_code"]
            ),
            "fetch_keyword_suggestions": lambda a: fetch_keyword_suggestions(
                a["keyword"], a.get("location_name", "United States"), a.get("limit", 50)
            ),
            "fetch_business_listings": lambda a: fetch_business_listings(
                a["category"], a["location_code"], a.get("limit", 100)
            ),
            "fetch_google_reviews": lambda a: fetch_google_reviews(
                a["keyword"], a["location_code"], a.get("depth", 20)
            ),
            "fetch_backlinks_summary": lambda a: fetch_backlinks_summary(a["target"]),
            "fetch_lighthouse": lambda a: fetch_lighthouse(a["url"]),
            "explore_serp_snapshot": lambda a: fetch_serp_organic(
                a["keyword"], a["location_code"], a.get("depth", 5)
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
