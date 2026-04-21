"""Market-opportunity recipe playbook.

Phase 1 Task 4 of 012-recipe-reports: the first concrete :class:`Recipe`
instance. Wires together

- Task 1's :func:`opportunity_score` composite formula,
- Task 2's DataForSEO + SerpAPI plugins (for tool names referenced in the
  system prompt), and
- Task 3's ``market_opportunity.html`` Jinja template,

into a single declarative playbook that a future ``RecipeRunner`` (Task 5)
can execute.

The module exposes one public value --- :data:`RECIPE` --- plus
:func:`compute_market_opportunity_context`, the pure scoring function the
recipe points at, and the :func:`_summarize` helper the tests exercise
directly.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Any

from src.research_agent.recipes.base import Recipe
from src.research_agent.recipes.scoring import OPPORTUNITY_WEIGHTS, opportunity_score

_RECIPE_ID = "market_opportunity"
_TEMPLATE_NAME = "market_opportunity.html"
_EMPTY_TOP_MARKET = "\u2014"  # em dash, mirrors the template's empty-state glyph


_INPUTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "service": {
            "type": "string",
            "description": "Local service category, e.g. 'plumber' or 'concrete paver'.",
        },
        "cities": {
            "type": "array",
            "description": (
                "List of target cities to score. Each entry is an object with "
                "name and DataForSEO location_code."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Human-readable city, e.g. 'Austin, TX'",
                    },
                    "location_code": {
                        "type": "integer",
                        "description": "DataForSEO location code",
                    },
                    "latlng": {
                        "type": "string",
                        "description": (
                            "Optional SerpAPI lat/lng string for the Maps "
                            "engine, e.g. '@30.2672,-97.7431,14z'"
                        ),
                    },
                },
                "required": ["name", "location_code"],
            },
            "minItems": 1,
        },
    },
    "required": ["service", "cities"],
}


_SYSTEM_PROMPT = """\
You are a market-opportunity analyst scoring local SEO markets for rank-and-rent investors.

Goal: for each city in the input, gather the five composite signals used by
the deterministic opportunity score --- search_volume, avg_competitor_da,
avg_backlink_strength, gmb_saturation, and cpc_value --- using the plugins
available in this session. Do not score the markets yourself; a deterministic
Python scorer runs after you finish.

Recommended tool-call plan per city (parallelize across cities where possible):

1. Search volume + CPC: call `fetch_keyword_volume` (DataForSEO) with the
   service keyword and the city's location_code. DataForSEO returns both the
   monthly search volume and the keyword CPC in a single call --- use the
   volume for `search_volume` and the CPC for `cpc_value`.
2. Top organic competitors: call `fetch_serp_organic` (DataForSEO) with the
   service keyword and the city's location_code. Extract the top-5 organic
   result domains. Record these in `top_competitors` for downstream display.
3. Competitor authority + backlink strength: for each of the top-5 domains,
   call `fetch_backlinks_summary` (DataForSEO). Parallelize the five calls
   per city where the runner allows it. Average the DA-equivalent across the
   five domains for `avg_competitor_da`, and average the backlink metric for
   `avg_backlink_strength`.
4. GMB saturation: call `fetch_serpapi_maps` (SerpAPI) using the city's
   `latlng` when provided (fall back to the city name otherwise). Count how
   many Maps local-pack businesses have 50+ reviews and divide by the total
   results returned; use that ratio as `gmb_saturation` (0.0-1.0).

Output contract: when every city has been processed, return a single JSON
object (no prose around it) matching exactly:

{
  "service": str,
  "markets": [
    {
      "city": str,
      "search_volume": int | null,
      "avg_competitor_da": float | null,
      "avg_backlink_strength": float | null,
      "gmb_saturation": float | null,
      "cpc_value": float | null,
      "top_competitors": [ ... ]
    },
    ...
  ],
  "total_cost_usd": float,
  "notes": [ "optional free-form strings" ]
}

Error handling: if a signal cannot be obtained for a city (API failure,
rate limit, empty SERP), set that field to null on the market and add a
short human-readable entry to `notes` describing which signal failed for
which city. Never fabricate numeric signals.
"""


def _summarize(markets: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the summary card values from a list of scored markets.

    *markets* must already carry a ``score`` key (populated by
    :func:`compute_market_opportunity_context`). Returns a dict with
    ``total_markets``, ``top_market``, and ``median_score``.

    Empty input yields a zeroed summary with the em-dash sentinel so the
    template never renders ``None``.
    """
    if not markets:
        return {
            "total_markets": 0,
            "top_market": _EMPTY_TOP_MARKET,
            "median_score": 0.0,
        }

    scores = [float(m["score"]) for m in markets]
    # Deterministic tie-break: sort by (score desc, city asc) and take the
    # first. Two markets with identical scores always pick the same "top"
    # regardless of input order.
    top = sorted(markets, key=lambda m: (-m["score"], m["city"]))[0]
    return {
        "total_markets": len(markets),
        "top_market": top["city"],
        "median_score": statistics.median(scores),
    }


def compute_market_opportunity_context(collected: dict[str, Any]) -> dict[str, Any]:
    """Turn collected tool outputs into the template render context.

    Pure function --- no I/O, no env reads. See the module docstring for the
    expected ``collected`` shape; it matches the output contract described
    in the recipe's system prompt.
    """
    raw_markets: list[dict[str, Any]] = list(collected.get("markets", []))

    scored_markets: list[dict[str, Any]] = []
    for market in raw_markets:
        # raw_markets is truthy here by virtue of being iterable non-empty;
        # opportunity_score handles the single-element case (0.5 neutral).
        result = opportunity_score(market, batch=raw_markets)
        scored = {
            **market,
            "score": float(result["score"]),
            "components": dict(result["components"]),
        }
        scored_markets.append(scored)

    summary = _summarize(scored_markets)
    summary["total_cost_usd"] = float(collected.get("total_cost_usd", 0.0))

    context: dict[str, Any] = {
        "service": collected.get("service", ""),
        "markets": scored_markets,
        "weights": dict(OPPORTUNITY_WEIGHTS),
        "summary": summary,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recipe_id": _RECIPE_ID,
    }

    notes = collected.get("notes")
    if notes:
        context["notes"] = list(notes)

    return context


RECIPE: Recipe = Recipe(
    recipe_id=_RECIPE_ID,
    audience="rank_and_rent",
    required_plugins=("dataforseo", "serpapi"),
    optional_plugins=(),
    inputs_schema=_INPUTS_SCHEMA,
    system_prompt=_SYSTEM_PROMPT,
    template_name=_TEMPLATE_NAME,
    scoring_fn=compute_market_opportunity_context,
)
