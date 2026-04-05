"""Unit tests for M6 domain classifier."""

from __future__ import annotations

from src.pipeline.domain_classifier import classify_domains, is_aggregator, is_national, normalize_domain


def test_normalize_domain_handles_urls_and_www() -> None:
    assert normalize_domain("https://www.YELP.com/biz/test") == "yelp.com"
    assert normalize_domain("localplumbingco.com") == "localplumbingco.com"


def test_is_aggregator_uses_known_aggregator_set() -> None:
    assert is_aggregator("https://yelp.com/biz/x") is True
    assert is_aggregator("https://localplumbingco.com") is False


def test_is_national_uses_cross_metro_ratio() -> None:
    stats = {"example.com": 8}
    assert is_national("example.com", stats, total_metros=20) is True
    assert is_national("example.com", stats, total_metros=40) is False


def test_classify_domains_counts_aggregator_and_local() -> None:
    stats = {"example.com": 8}
    counts = classify_domains(
        ["yelp.com", "example.com", "localplumbingco.com"],
        cross_metro_domain_stats=stats,
        total_metros=20,
    )
    assert counts["aggregator_count"] == 2
    assert counts["local_biz_count"] == 1
