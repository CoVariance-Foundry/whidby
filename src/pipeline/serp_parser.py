"""SERP parsing helpers used by M6 signal extraction."""

from __future__ import annotations

from .domain_classifier import normalize_domain


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def parse_serp_features(raw_serp_rows: list[dict]) -> dict[str, object]:
    """Parse and aggregate SERP features from M5 organic SERP rows."""
    total = len(raw_serp_rows)
    if total == 0:
        return {
            "aio_trigger_rate": 0.0,
            "featured_snippet_rate": 0.0,
            "paa_density": 0.0,
            "local_pack_present": False,
            "local_pack_position": 10,
            "lsa_present": False,
            "ads_present": False,
            "organic_domains": [],
            "organic_titles": [],
        }

    aio_count = 0
    snippet_count = 0
    paa_total = 0
    local_pack_position = 10
    local_pack_present = False
    lsa_present = False
    ads_present = False
    organic_domains: list[str] = []
    organic_titles: list[str] = []

    for row in raw_serp_rows:
        features = {str(item).lower() for item in _as_list(row.get("serp_features"))}
        aio = bool(row.get("aio_present")) or "ai_overview" in features or "aio" in features
        snippet = bool(row.get("snippet_present")) or "featured_snippet" in features
        lsa = bool(row.get("lsa_present")) or "local_services_ads" in features
        ads = bool(row.get("ads_present")) or bool(row.get("ads_top_present")) or "ads_top" in features

        people_also_ask = _as_list(row.get("people_also_ask"))
        paa_count = int(row.get("paa_count", len(people_also_ask)))

        lp_present = bool(row.get("local_pack_present")) or "local_pack" in features
        lp_position = int(row.get("local_pack_position", 10))

        aio_count += int(aio)
        snippet_count += int(snippet)
        paa_total += max(paa_count, 0)
        lsa_present = lsa_present or lsa
        ads_present = ads_present or ads

        if lp_present:
            local_pack_present = True
            local_pack_position = min(local_pack_position, lp_position if lp_position > 0 else 10)

        for result in _as_list(row.get("organic_results")):
            if not isinstance(result, dict):
                continue
            domain = normalize_domain(str(result.get("domain") or result.get("url") or ""))
            title = str(result.get("title", "")).strip()
            if domain:
                organic_domains.append(domain)
            if title:
                organic_titles.append(title)

    return {
        "aio_trigger_rate": round(aio_count / total, 4),
        "featured_snippet_rate": round(snippet_count / total, 4),
        "paa_density": round(paa_total / total, 4),
        "local_pack_present": local_pack_present,
        "local_pack_position": local_pack_position if local_pack_present else 10,
        "lsa_present": lsa_present,
        "ads_present": ads_present,
        "organic_domains": organic_domains,
        "organic_titles": organic_titles,
    }
