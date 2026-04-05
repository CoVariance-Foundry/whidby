"""Demand signal extraction."""

from __future__ import annotations

from src.pipeline.effective_volume import compute_effective_volume


def _normalize_keyword_rows(keyword_volume_rows: list[dict]) -> dict[str, dict]:
    by_keyword: dict[str, dict] = {}
    for row in keyword_volume_rows:
        keyword = str(row.get("keyword", "")).strip().lower()
        if not keyword:
            continue
        by_keyword[keyword] = row
    return by_keyword


def extract_demand_signals(
    keyword_expansion: list[dict],
    keyword_volume_rows: list[dict],
    aio_detected_by_keyword: dict[str, bool] | None = None,
) -> dict[str, float]:
    """Build demand signal block from keyword metadata and volume rows."""
    rows_by_keyword = _normalize_keyword_rows(keyword_volume_rows)
    aio_by_keyword = aio_detected_by_keyword or {}

    total_volume = 0.0
    effective_volume = 0.0
    head_term_volume = 0.0
    non_zero_keywords = 0
    weighted_cpc_sum = 0.0
    transactional_volume = 0.0
    max_cpc_tier12 = 0.0

    for item in keyword_expansion:
        keyword = str(item.get("keyword", "")).strip().lower()
        if not keyword:
            continue
        intent = str(item.get("intent", "")).strip().lower()
        tier = int(item.get("tier", 0))

        row = rows_by_keyword.get(keyword, {})
        volume = float(row.get("search_volume", row.get("monthly_volume", row.get("volume", 0.0))) or 0.0)
        cpc = float(row.get("cpc", 0.0) or 0.0)
        has_aio = bool(aio_by_keyword.get(keyword, False))

        total_volume += volume
        effective_volume += compute_effective_volume(volume, intent, has_aio)
        weighted_cpc_sum += cpc * volume
        if volume > 0:
            non_zero_keywords += 1
        if tier == 1:
            head_term_volume += volume
        if tier in {1, 2}:
            max_cpc_tier12 = max(max_cpc_tier12, cpc)
        if intent == "transactional":
            transactional_volume += volume

    keyword_count = max(len([item for item in keyword_expansion if item.get("keyword")]), 1)
    avg_cpc = weighted_cpc_sum / total_volume if total_volume > 0 else 0.0
    volume_breadth = non_zero_keywords / keyword_count
    transactional_ratio = transactional_volume / total_volume if total_volume > 0 else 0.0

    return {
        "total_search_volume": round(total_volume, 4),
        "effective_search_volume": round(effective_volume, 4),
        "head_term_volume": round(head_term_volume, 4),
        "volume_breadth": round(volume_breadth, 4),
        "avg_cpc": round(avg_cpc, 4),
        "max_cpc": round(max_cpc_tier12, 4),
        "cpc_volume_product": round(effective_volume * avg_cpc, 4),
        "transactional_ratio": round(transactional_ratio, 4),
    }
