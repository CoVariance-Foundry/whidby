"""LLM plugin wrapping keyword expansion, intent classification, and generation."""

from __future__ import annotations

import json
from typing import Any

from src.research_agent.plugins.base import ToolPlugin
from src.research_agent.tools.api_tools import (
    classify_search_intent,
    expand_keywords,
    llm_generate,
)


class LLMPlugin(ToolPlugin):
    """Plugin exposing LLM client capabilities as agent-callable tools."""

    @property
    def name(self) -> str:
        return "llm"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "expand_keywords",
                "description": "Use the LLM to expand a niche keyword into a classified keyword set.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "niche": {
                            "type": "string",
                            "description": "The niche keyword to expand (e.g. 'plumber').",
                        },
                    },
                    "required": ["niche"],
                },
            },
            {
                "name": "classify_search_intent",
                "description": "Classify the search intent of a query string.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to classify.",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "llm_generate",
                "description": "Free-form LLM generation for analysis, reasoning, or content.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "system_prompt": {
                            "type": "string",
                            "description": "System instructions for the model.",
                        },
                        "user_prompt": {
                            "type": "string",
                            "description": "The user-facing prompt/question.",
                        },
                    },
                    "required": ["system_prompt", "user_prompt"],
                },
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        dispatch = {
            "expand_keywords": lambda a: expand_keywords(a["niche"]),
            "classify_search_intent": lambda a: classify_search_intent(a["query"]),
            "llm_generate": lambda a: llm_generate(a["system_prompt"], a["user_prompt"]),
        }
        if tool_name not in dispatch:
            raise KeyError(f"Unknown tool: '{tool_name}'")

        raw_json = dispatch[tool_name](arguments)
        parsed = json.loads(raw_json)
        return {
            "data": parsed.get("data", parsed),
            "cost_usd": parsed.get("cost_usd", 0.0),
        }
