"""Top-level M6 signal extraction orchestration."""

from __future__ import annotations

from src.pipeline.dfs_normalizers import (
    normalize_business_listings_rows,
    normalize_gbp_info_rows,
    normalize_google_reviews_rows,
    normalize_serp_maps_rows,
)
from src.pipeline.extractors import (
    extract_ai_resilience_signals,
    extract_demand_signals,
    extract_local_competition_signals,
    extract_monetization_signals,
    extract_organic_competition_signals,
)
from src.pipeline.serp_parser import parse_serp_features


def _keyword_aio_lookup(raw_serp_rows: list[dict]) -> dict[str, bool]:
    lookup: dict[str, bool] = {}
    for row in raw_serp_rows:
        keyword = str(row.get("keyword", "")).strip().lower()
        if not keyword:
            continue
        has_aio = bool(row.get("aio_present"))
        features = row.get("serp_features", [])
        if isinstance(features, list):
            has_aio = has_aio or any(str(item).lower() in {"ai_overview", "aio"} for item in features)
        lookup[keyword] = has_aio
    return lookup


def extract_signals(
    raw_metro_bundle: dict[str, list[dict]],
    keyword_expansion: list[dict],
    cross_metro_domain_stats: dict[str, int | list[str] | set[str]] | None = None,
    total_metros: int | None = None,
) -> dict[str, dict]:
    """Extract M6 MetroSignals for one metro.

    Args:
        raw_metro_bundle: Raw per-category M5 payload for one metro.
        keyword_expansion: Keyword metadata from M4.
        cross_metro_domain_stats: Optional domain frequency map for national detection.
        total_metros: Optional denominator for cross-metro threshold.

    Returns:
        MetroSignals object containing five categories.

    Raises:
        ValueError: If required top-level inputs are missing.
    """
    if not isinstance(raw_metro_bundle, dict):
        raise ValueError("raw_metro_bundle is required and must be a dictionary")
    if not isinstance(keyword_expansion, list):
        raise ValueError("keyword_expansion is required and must be a list")

    raw_serp = list(raw_metro_bundle.get("serp_organic", []))
    raw_serp_maps = normalize_serp_maps_rows(list(raw_metro_bundle.get("serp_maps", [])))
    raw_keyword_volume = list(raw_metro_bundle.get("keyword_volume", []))
    raw_backlinks = list(raw_metro_bundle.get("backlinks", []))
    raw_lighthouse = list(raw_metro_bundle.get("lighthouse", []))
    raw_reviews = normalize_google_reviews_rows(list(raw_metro_bundle.get("google_reviews", [])))
    raw_gbp = normalize_gbp_info_rows(list(raw_metro_bundle.get("gbp_info", [])))
    raw_listings = normalize_business_listings_rows(
        list(raw_metro_bundle.get("business_listings", []))
    )

    serp_context = parse_serp_features(raw_serp)
    aio_by_keyword = _keyword_aio_lookup(raw_serp)

    demand = extract_demand_signals(
        keyword_expansion=keyword_expansion,
        keyword_volume_rows=raw_keyword_volume,
        aio_detected_by_keyword=aio_by_keyword,
    )
    organic_competition = extract_organic_competition_signals(
        backlinks_rows=raw_backlinks,
        lighthouse_rows=raw_lighthouse,
        serp_context=serp_context,
        keyword_expansion=keyword_expansion,
        cross_metro_domain_stats=cross_metro_domain_stats,
        total_metros=total_metros,
    )
    local_competition = extract_local_competition_signals(
        serp_context=serp_context,
        serp_maps_rows=raw_serp_maps,
        google_reviews_rows=raw_reviews,
        gbp_info_rows=raw_gbp,
        business_listings_rows=raw_listings,
    )
    ai_resilience = extract_ai_resilience_signals(
        serp_context=serp_context,
        keyword_expansion=keyword_expansion,
    )
    monetization = extract_monetization_signals(
        demand_signals=demand,
        local_competition_signals=local_competition,
        organic_competition_signals=organic_competition,
        serp_context=serp_context,
        business_listings_rows=raw_listings,
    )

    return {
        "demand": demand,
        "organic_competition": organic_competition,
        "local_competition": local_competition,
        "ai_resilience": ai_resilience,
        "monetization": monetization,
    }
