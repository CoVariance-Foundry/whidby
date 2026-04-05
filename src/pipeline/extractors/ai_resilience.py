"""AI resilience signal extraction."""

from __future__ import annotations


def extract_ai_resilience_signals(
    serp_context: dict[str, object],
    keyword_expansion: list[dict],
) -> dict[str, float | int]:
    """Build AI resilience signal block."""
    total_keywords = len([item for item in keyword_expansion if item.get("keyword")]) or 1
    transactional_count = len(
        [item for item in keyword_expansion if str(item.get("intent", "")).lower() == "transactional"]
    )

    local_fulfillment_required = 1
    for item in keyword_expansion:
        if "local_fulfillment_required" in item:
            local_fulfillment_required = int(bool(item["local_fulfillment_required"]))
            break

    return {
        "aio_trigger_rate": round(float(serp_context.get("aio_trigger_rate", 0.0) or 0.0), 4),
        "featured_snippet_rate": round(float(serp_context.get("featured_snippet_rate", 0.0) or 0.0), 4),
        "transactional_keyword_ratio": round(transactional_count / total_keywords, 4),
        "local_fulfillment_required": local_fulfillment_required,
        "paa_density": round(float(serp_context.get("paa_density", 0.0) or 0.0), 4),
    }
