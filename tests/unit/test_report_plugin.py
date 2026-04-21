"""Unit tests for ReportPlugin (Task 3 of 012-recipe-reports)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import TemplateNotFound

from src.research_agent.plugins.report_plugin import ReportPlugin


@pytest.fixture
def minimal_context() -> dict:
    """A minimal but valid market_opportunity.html context."""
    return {
        "service": "roofer",
        "markets": [
            {
                "city": "Austin, TX",
                "score": 0.87,
                "components": {
                    "search_volume_norm": 0.9,
                    "inverse_avg_competitor_da": 0.8,
                    "inverse_avg_backlink_strength": 0.75,
                    "inverse_gmb_saturation": 0.7,
                    "cpc_value_norm": 0.6,
                },
                "search_volume": 12000,
                "avg_competitor_da": 24.0,
                "avg_backlink_strength": 12.5,
                "gmb_saturation": 0.42,
                "cpc_value": 18.3,
            },
        ],
        "weights": {
            "search_volume": 0.30,
            "avg_competitor_da": 0.25,
            "avg_backlink_strength": 0.20,
            "gmb_saturation": 0.15,
            "cpc_value": 0.10,
        },
        "summary": {
            "total_markets": 1,
            "top_market": "Austin, TX",
            "median_score": 0.87,
            "total_cost_usd": 0.12,
        },
        "generated_at": "2026-04-20T12:00:00Z",
        "recipe_id": "market_opportunity",
    }


class TestReportPluginMetadata:
    def test_name_is_report(self):
        assert ReportPlugin().name == "report"

    def test_tool_definitions_returns_one_schema(self):
        defs = ReportPlugin().tool_definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "compose_report"

    def test_tool_definitions_have_required_anthropic_fields(self):
        defs = ReportPlugin().tool_definitions()
        schema = defs[0]
        assert "description" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "properties" in schema["input_schema"]
        required = set(schema["input_schema"]["required"])
        assert required == {"recipe_id", "template_name", "context", "output_dir"}


class TestReportPluginExecute:
    def test_writes_file_to_disk(self, tmp_path: Path, minimal_context: dict):
        plugin = ReportPlugin()
        result = plugin.execute(
            "compose_report",
            {
                "recipe_id": "market_opportunity",
                "template_name": "market_opportunity.html",
                "context": minimal_context,
                "output_dir": str(tmp_path),
            },
        )
        assert result["status"] == "ok"
        assert result["cost_usd"] == 0.0
        assert "report_path" in result
        assert "bytes" in result
        assert result["bytes"] > 0

        report_path = Path(result["report_path"])
        assert report_path.is_absolute()
        assert report_path.exists()
        assert report_path.stat().st_size == result["bytes"]

    def test_filename_pattern(self, tmp_path: Path, minimal_context: dict):
        plugin = ReportPlugin()
        result = plugin.execute(
            "compose_report",
            {
                "recipe_id": "market_opportunity",
                "template_name": "market_opportunity.html",
                "context": minimal_context,
                "output_dir": str(tmp_path),
            },
        )
        filename = Path(result["report_path"]).name
        # <recipe_id>_<YYYYMMDDTHHMMSSZ>.html
        assert re.match(
            r"^market_opportunity_\d{8}T\d{6}Z\.html$",
            filename,
        ), f"Filename '{filename}' doesn't match expected pattern"

    def test_missing_template_raises_template_not_found(
        self, tmp_path: Path, minimal_context: dict
    ):
        plugin = ReportPlugin()
        with pytest.raises(TemplateNotFound):
            plugin.execute(
                "compose_report",
                {
                    "recipe_id": "market_opportunity",
                    "template_name": "does_not_exist.html",
                    "context": minimal_context,
                    "output_dir": str(tmp_path),
                },
            )

    def test_output_dir_created_if_missing(
        self, tmp_path: Path, minimal_context: dict
    ):
        nested = tmp_path / "reports" / "2026" / "04"
        assert not nested.exists()

        plugin = ReportPlugin()
        result = plugin.execute(
            "compose_report",
            {
                "recipe_id": "market_opportunity",
                "template_name": "market_opportunity.html",
                "context": minimal_context,
                "output_dir": str(nested),
            },
        )
        assert nested.exists()
        assert Path(result["report_path"]).parent == nested

    def test_autoescape_protects_against_injection(
        self, tmp_path: Path, minimal_context: dict
    ):
        # Inject a malicious service name.
        minimal_context["service"] = "<script>alert(1)</script>"
        plugin = ReportPlugin()
        result = plugin.execute(
            "compose_report",
            {
                "recipe_id": "market_opportunity",
                "template_name": "market_opportunity.html",
                "context": minimal_context,
                "output_dir": str(tmp_path),
            },
        )
        html = Path(result["report_path"]).read_text(encoding="utf-8")
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    def test_unknown_tool_raises_keyerror(self):
        with pytest.raises(KeyError, match="bogus"):
            ReportPlugin().execute("bogus", {})
