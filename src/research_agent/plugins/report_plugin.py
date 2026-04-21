"""Report plugin: renders a recipe's collected data to a branded HTML file.

Mirrors the shape of the other plugins in this package: single plugin name,
Anthropic-schema tool definitions, and an ``execute`` dispatcher that raises
``KeyError`` for unknown tool names.

Pure filesystem writer -- no network, no DB, single-threaded. The plugin
resolves templates from :mod:`src.research_agent.templates` using a Jinja
``FileSystemLoader`` with autoescape enabled for ``.html`` files.

Trust model: ``template_name`` is restricted to :data:`ALLOWED_TEMPLATES` so
agent-generated arguments cannot load arbitrary files from the templates
directory. ``output_dir`` is trusted to be a safe path chosen by the caller;
the FastAPI endpoint that invokes this plugin is responsible for constraining
it under the per-run reports root (``research_runs/{run_id}/reports/``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.research_agent.plugins.base import ToolPlugin

TEMPLATE_DIR: Path = Path(__file__).resolve().parent.parent / "templates"

ALLOWED_TEMPLATES: frozenset[str] = frozenset({"market_opportunity.html"})

# UTC timestamp format used in report filenames. Shared between the plugin
# (which writes) and the FastAPI layer (which parses for display).
REPORT_TIMESTAMP_FORMAT: str = "%Y%m%dT%H%M%SZ"


class ReportPlugin(ToolPlugin):
    """Plugin exposing the ``compose_report`` tool for recipe report rendering."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
            keep_trailing_newline=True,
        )

    @property
    def name(self) -> str:
        return "report"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "compose_report",
                "description": (
                    "Render a recipe's collected data into a branded HTML "
                    "report and persist it to the filesystem. Returns the "
                    "absolute path of the written file and the byte size."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "recipe_id": {
                            "type": "string",
                            "description": "Recipe id (maps to template name)",
                        },
                        "template_name": {
                            "type": "string",
                            "description": (
                                "Jinja template filename, e.g. "
                                "'market_opportunity.html'"
                            ),
                        },
                        "context": {
                            "type": "object",
                            "description": (
                                "Template render context (keyword->value map)."
                            ),
                        },
                        "output_dir": {
                            "type": "string",
                            "description": (
                                "Absolute directory path the report will be "
                                "written to. Will be created if missing."
                            ),
                        },
                    },
                    "required": [
                        "recipe_id",
                        "template_name",
                        "context",
                        "output_dir",
                    ],
                },
            }
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name != "compose_report":
            raise KeyError(f"Unknown tool: '{tool_name}'")

        recipe_id: str = arguments["recipe_id"]
        template_name: str = arguments["template_name"]
        context: dict[str, Any] = arguments["context"]
        output_dir = Path(arguments["output_dir"])

        if template_name not in ALLOWED_TEMPLATES:
            raise ValueError(
                f"template '{template_name}' is not in the allow-list "
                f"(allowed: {sorted(ALLOWED_TEMPLATES)})"
            )

        template = self._env.get_template(template_name)
        rendered = template.render(**context)

        timestamp = datetime.now(timezone.utc).strftime(REPORT_TIMESTAMP_FORMAT)
        filename = f"{recipe_id}_{timestamp}.html"

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = (output_dir / filename).resolve()
        output_path.write_text(rendered, encoding="utf-8")

        byte_size = output_path.stat().st_size

        return {
            "report_path": str(output_path),
            "bytes": byte_size,
            "cost_usd": 0.0,
            "status": "ok",
        }
