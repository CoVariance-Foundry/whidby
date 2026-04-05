"""Monetization signal extraction."""

from __future__ import annotations


def extract_monetization_signals(
    demand_signals: dict[str, float],
    local_competition_signals: dict[str, float | bool],
    organic_competition_signals: dict[str, float],
    serp_context: dict[str, object],
    business_listings_rows: list[dict],
) -> dict[str, float | bool]:
    """Build monetization signal block."""
    return {
        "avg_cpc": round(float(demand_signals.get("avg_cpc", 0.0) or 0.0), 4),
        "business_density": float(len(business_listings_rows)),
        "gbp_completeness_avg": round(
            float(local_competition_signals.get("gbp_completeness_avg", 0.0) or 0.0),
            4,
        ),
        "lsa_present": bool(serp_context.get("lsa_present", False)),
        "aggregator_presence": float(organic_competition_signals.get("aggregator_count", 0.0) or 0.0),
        "ads_present": bool(serp_context.get("ads_present", False)),
    }
