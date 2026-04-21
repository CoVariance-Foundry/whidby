"""Unit tests for the market_opportunity.html Jinja template.

Renders the template directly via Jinja so we test the template output
independently of :class:`ReportPlugin`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "research_agent"
    / "templates"
)


@pytest.fixture
def env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


@pytest.fixture
def three_market_context() -> dict:
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
            {
                "city": "Denver, CO",
                "score": 0.64,
                "components": {
                    "search_volume_norm": 0.6,
                    "inverse_avg_competitor_da": 0.5,
                    "inverse_avg_backlink_strength": 0.55,
                    "inverse_gmb_saturation": 0.6,
                    "cpc_value_norm": 0.5,
                },
                "search_volume": 8000,
                "avg_competitor_da": 32.0,
                "avg_backlink_strength": 20.2,
                "gmb_saturation": 0.55,
                "cpc_value": 14.0,
            },
            {
                "city": "Boise, ID",
                "score": 0.41,
                "components": {
                    "search_volume_norm": 0.3,
                    "inverse_avg_competitor_da": 0.4,
                    "inverse_avg_backlink_strength": 0.45,
                    "inverse_gmb_saturation": 0.5,
                    "cpc_value_norm": 0.35,
                },
                "search_volume": 2400,
                "avg_competitor_da": 38.0,
                "avg_backlink_strength": 26.0,
                "gmb_saturation": 0.60,
                "cpc_value": 9.1,
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
            "total_markets": 3,
            "top_market": "Austin, TX",
            "median_score": 0.64,
            "total_cost_usd": 1.47,
        },
        "generated_at": "2026-04-20T12:00:00Z",
        "recipe_id": "market_opportunity",
    }


class TestMarketOpportunityTemplate:
    def test_title_contains_service(self, env, three_market_context):
        tmpl = env.get_template("market_opportunity.html")
        html = tmpl.render(**three_market_context)
        assert "Market Opportunity" in html
        assert "roofer" in html.lower()

    def test_every_city_appears(self, env, three_market_context):
        tmpl = env.get_template("market_opportunity.html")
        html = tmpl.render(**three_market_context)
        for market in three_market_context["markets"]:
            assert market["city"] in html, f"Missing city: {market['city']}"

    def test_top_market_listed_first(self, env, three_market_context):
        tmpl = env.get_template("market_opportunity.html")
        html = tmpl.render(**three_market_context)

        # Only inspect the first <tbody> to avoid matching cities that appear
        # again inside the per-market <details> breakdown section.
        tbody_open = html.find("<tbody>")
        tbody_close = html.find("</tbody>", tbody_open)
        assert tbody_open != -1 and tbody_close != -1
        tbody = html[tbody_open:tbody_close]

        idx_austin = tbody.find("Austin, TX")
        idx_denver = tbody.find("Denver, CO")
        idx_boise = tbody.find("Boise, ID")
        assert idx_austin != -1
        assert idx_denver != -1
        assert idx_boise != -1
        # Table is sorted by score descending: Austin > Denver > Boise.
        assert idx_austin < idx_denver < idx_boise

    def test_weights_disclosed(self, env, three_market_context):
        tmpl = env.get_template("market_opportunity.html")
        html = tmpl.render(**three_market_context)
        # Check the weights surface somehow (either as decimals or percents)
        # 0.30 and 30% are both acceptable forms.
        has_search_volume_weight = "0.30" in html or "30%" in html or "0.3" in html
        has_da_weight = "0.25" in html or "25%" in html
        assert has_search_volume_weight, "search_volume weight 0.30 not visible"
        assert has_da_weight, "avg_competitor_da weight 0.25 not visible"

    def test_valid_html5(self, env, three_market_context):
        tmpl = env.get_template("market_opportunity.html")
        html = tmpl.render(**three_market_context)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html

    def test_zero_markets_renders(self, env):
        context = {
            "service": "roofer",
            "markets": [],
            "weights": {
                "search_volume": 0.30,
                "avg_competitor_da": 0.25,
                "avg_backlink_strength": 0.20,
                "gmb_saturation": 0.15,
                "cpc_value": 0.10,
            },
            "summary": {
                "total_markets": 0,
                "top_market": None,
                "median_score": 0.0,
                "total_cost_usd": 0.0,
            },
            "generated_at": "2026-04-20T12:00:00Z",
            "recipe_id": "market_opportunity",
        }
        tmpl = env.get_template("market_opportunity.html")
        html = tmpl.render(**context)
        # Should render without raising and indicate emptiness
        assert "No markets" in html or "no markets" in html
