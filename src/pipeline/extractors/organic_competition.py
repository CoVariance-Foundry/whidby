"""Organic competition signal extraction."""

from __future__ import annotations

from src.pipeline.domain_classifier import classify_domains


def extract_organic_competition_signals(
    backlinks_rows: list[dict],
    lighthouse_rows: list[dict],
    serp_context: dict[str, object],
    keyword_expansion: list[dict],
    cross_metro_domain_stats: dict[str, int | list[str] | set[str]] | None = None,
    total_metros: int | None = None,
) -> dict[str, float]:
    """Build organic competition signal block."""
    da_values = sorted(
        [
            float(row.get("domain_authority", row.get("da", 0.0)) or 0.0)
            for row in backlinks_rows
            if row
        ],
        reverse=True,
    )
    top5_da = da_values[:5]
    avg_top5_da = sum(top5_da) / len(top5_da) if top5_da else 0.0
    min_top5_da = min(top5_da) if top5_da else 0.0
    max_top5_da = max(top5_da) if top5_da else 0.0
    da_spread = max_top5_da - min_top5_da

    domains = [str(item) for item in serp_context.get("organic_domains", [])]
    domain_counts = classify_domains(
        domains=domains,
        cross_metro_domain_stats=cross_metro_domain_stats,
        total_metros=total_metros,
    )

    perf_values = [float(row.get("performance_score", row.get("performance", 0.0)) or 0.0) for row in lighthouse_rows]
    avg_lighthouse_performance = sum(perf_values) / len(perf_values) if perf_values else 0.0

    schema_hits = 0
    for row in lighthouse_rows:
        schema_types = row.get("schema_types", [])
        has_schema = bool(row.get("has_localbusiness_schema", False)) or (
            isinstance(schema_types, list) and "LocalBusiness" in schema_types
        )
        schema_hits += int(has_schema)
    schema_adoption_rate = schema_hits / len(lighthouse_rows) if lighthouse_rows else 0.0

    keywords = [str(item.get("keyword", "")).lower() for item in keyword_expansion if item.get("keyword")]
    titles = [str(item).lower() for item in serp_context.get("organic_titles", [])]
    title_hits = 0
    for title in titles[:10]:
        if any(keyword in title for keyword in keywords):
            title_hits += 1
    title_keyword_match_rate = title_hits / min(len(titles), 10) if titles else 0.0

    return {
        "avg_top5_da": round(avg_top5_da, 4),
        "min_top5_da": round(min_top5_da, 4),
        "da_spread": round(da_spread, 4),
        "aggregator_count": domain_counts["aggregator_count"],
        "local_biz_count": domain_counts["local_biz_count"],
        "avg_lighthouse_performance": round(avg_lighthouse_performance, 4),
        "schema_adoption_rate": round(schema_adoption_rate, 4),
        "title_keyword_match_rate": round(title_keyword_match_rate, 4),
    }
