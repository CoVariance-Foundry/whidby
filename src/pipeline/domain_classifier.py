"""Domain classification helpers for M6 signal extraction."""

from __future__ import annotations

from urllib.parse import urlparse

from src.config.constants import KNOWN_AGGREGATORS


def normalize_domain(value: str) -> str:
    """Normalize a domain or URL into a root-lowercase domain string."""
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"https://{raw}"
    host = urlparse(raw).netloc or urlparse(raw).path
    host = host.lower().split(":")[0].strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def is_aggregator(domain: str) -> bool:
    normalized = normalize_domain(domain)
    return normalized in KNOWN_AGGREGATORS


def is_national(
    domain: str,
    cross_metro_domain_stats: dict[str, int | list[str] | set[str]] | None = None,
    total_metros: int | None = None,
) -> bool:
    """Classify domain as national via cross-metro appearance ratio."""
    if not cross_metro_domain_stats:
        return False
    normalized = normalize_domain(domain)
    if not normalized:
        return False
    if normalized not in cross_metro_domain_stats:
        return False

    value = cross_metro_domain_stats[normalized]
    if isinstance(value, int):
        count = value
    elif isinstance(value, (set, list, tuple)):
        count = len(value)
    else:
        return False

    if not total_metros or total_metros <= 0:
        # Heuristic fallback from spec examples: 5+ metros is strong national signal.
        return count >= 5

    return (count / total_metros) >= 0.30


def classify_domains(
    domains: list[str],
    cross_metro_domain_stats: dict[str, int | list[str] | set[str]] | None = None,
    total_metros: int | None = None,
) -> dict[str, int]:
    """Return aggregator/local business counts from domains list."""
    unique_domains = [normalize_domain(domain) for domain in domains if normalize_domain(domain)]
    top10 = unique_domains[:10]
    aggregator_count = 0
    local_biz_count = 0

    for domain in top10:
        if is_aggregator(domain) or is_national(
            domain,
            cross_metro_domain_stats=cross_metro_domain_stats,
            total_metros=total_metros,
        ):
            aggregator_count += 1
        else:
            local_biz_count += 1

    return {
        "aggregator_count": aggregator_count,
        "local_biz_count": local_biz_count,
    }
