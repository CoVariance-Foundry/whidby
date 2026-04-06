"""Tool adapter functions wrapping existing project clients.

Thin facades that expose DataForSEO, MetroDB, and LLM client methods
as callable functions for the research agent plugins.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.llm.client import LLMClient
from src.data.metro_db import MetroDB


def _get_dfs_client() -> DataForSEOClient:
    return DataForSEOClient(
        login=os.environ.get("DATAFORSEO_LOGIN", ""),
        password=os.environ.get("DATAFORSEO_PASSWORD", ""),
    )


def _get_llm_client() -> LLMClient:
    return LLMClient()


def _get_metro_db() -> MetroDB:
    return MetroDB.from_seed()


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from sync context, reusing a running loop if possible."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# DataForSEO tools
# ---------------------------------------------------------------------------


def fetch_serp_organic(keyword: str, location_code: int, depth: int = 10) -> str:
    """Fetch organic SERP results for a keyword at a specific DataForSEO location.

    Args:
        keyword: Search query to analyze.
        location_code: DataForSEO location code for geo targeting.
        depth: Number of results to return (default 10).

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(client.serp_organic(keyword, location_code, depth))
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


def fetch_serp_maps(keyword: str, location_code: int, depth: int = 10) -> str:
    """Fetch Google Maps SERP results for a keyword at a specific location.

    Args:
        keyword: Search query to analyze.
        location_code: DataForSEO location code for geo targeting.
        depth: Number of results to return (default 10).

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(client.serp_maps(keyword, location_code, depth))
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


def fetch_keyword_volume(keywords: list[str], location_code: int) -> str:
    """Fetch search volume and metrics for a list of keywords.

    Args:
        keywords: List of keywords to look up.
        location_code: DataForSEO location code for geo targeting.

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(client.keyword_volume(keywords, location_code))
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


def fetch_keyword_suggestions(
    keyword: str, location_name: str = "United States", limit: int = 50
) -> str:
    """Fetch keyword suggestions related to a seed keyword.

    Args:
        keyword: Seed keyword.
        location_name: Location name (e.g. "United States").
        limit: Max suggestions to return (default 50).

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(
        client.keyword_suggestions(keyword, location_name=location_name, limit=limit)
    )
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


def fetch_business_listings(
    category: str, location_code: int, limit: int = 100
) -> str:
    """Fetch business listings for a category in a location.

    Args:
        category: Business category (e.g. "plumber").
        location_code: DataForSEO location code.
        limit: Max listings to return (default 100).

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(client.business_listings(category, location_code, limit))
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


def fetch_google_reviews(
    keyword: str, location_code: int, depth: int = 20
) -> str:
    """Fetch Google review data for a keyword/location combination.

    Args:
        keyword: Business search term.
        location_code: DataForSEO location code.
        depth: Number of review results (default 20).

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(client.google_reviews(keyword, location_code, depth))
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


def fetch_backlinks_summary(target: str) -> str:
    """Fetch backlink summary for a target domain.

    Args:
        target: Domain or URL to analyze.

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(client.backlinks_summary(target))
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


def fetch_lighthouse(url: str) -> str:
    """Run a Lighthouse performance audit on a URL.

    Args:
        url: The URL to audit.

    Returns:
        JSON string of the API response.
    """
    client = _get_dfs_client()
    resp = _run_async(client.lighthouse(url))
    return json.dumps({"status": resp.status, "data": resp.data, "cost": resp.cost})


# ---------------------------------------------------------------------------
# Metro DB tools
# ---------------------------------------------------------------------------


def expand_geo_scope(scope: str, target: str, depth: str = "standard") -> str:
    """Expand a geographic scope into a list of metros.

    Args:
        scope: "state", "region", or "custom".
        target: State code (e.g. "AZ"), region name (e.g. "Southwest"),
                or comma-separated CBSA codes for "custom".
        depth: "standard" (top 20 by pop) or "deep" (all >= 50k pop).

    Returns:
        JSON array of metro objects with cbsa_code, name, state, population,
        principal_cities, and dataforseo_location_codes.
    """
    db = _get_metro_db()
    target_val: str | list[str] = target
    if scope == "custom":
        target_val = [c.strip() for c in target.split(",")]
    metros = db.expand_scope(scope=scope, target=target_val, depth=depth)
    return json.dumps(
        [
            {
                "cbsa_code": m.cbsa_code,
                "cbsa_name": m.cbsa_name,
                "state": m.state,
                "population": m.population,
                "principal_cities": m.principal_cities,
                "dataforseo_location_codes": m.dataforseo_location_codes,
            }
            for m in metros
        ]
    )


# ---------------------------------------------------------------------------
# LLM tools
# ---------------------------------------------------------------------------


def expand_keywords(niche: str) -> str:
    """Use the LLM to expand a niche keyword into classified keyword set.

    Args:
        niche: The niche keyword to expand (e.g. "plumber").

    Returns:
        JSON string with the keyword expansion result.
    """
    client = _get_llm_client()
    result = _run_async(client.keyword_expansion(niche))
    return json.dumps(
        {"success": result.success, "data": result.data, "cost_usd": result.cost_usd}
    )


def classify_search_intent(query: str) -> str:
    """Classify the search intent of a query string.

    Args:
        query: The search query to classify.

    Returns:
        JSON string with the intent label.
    """
    client = _get_llm_client()
    intent = _run_async(client.classify_intent(query))
    return json.dumps({"intent": intent})


def llm_generate(system_prompt: str, user_prompt: str) -> str:
    """Free-form LLM generation for analysis, reasoning, or content.

    Args:
        system_prompt: System instructions for the model.
        user_prompt: The user-facing prompt/question.

    Returns:
        JSON string with the generated text.
    """
    client = _get_llm_client()
    result = _run_async(client.generate(system=system_prompt, prompt=user_prompt))
    return json.dumps(
        {"success": result.success, "data": result.data, "cost_usd": result.cost_usd}
    )


# ---------------------------------------------------------------------------
# Tool registry (plain function list for backward compatibility)
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    fetch_serp_organic,
    fetch_serp_maps,
    fetch_keyword_volume,
    fetch_keyword_suggestions,
    fetch_business_listings,
    fetch_google_reviews,
    fetch_backlinks_summary,
    fetch_lighthouse,
    expand_geo_scope,
    expand_keywords,
    classify_search_intent,
    llm_generate,
]
