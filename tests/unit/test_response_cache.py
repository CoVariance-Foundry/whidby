"""Bounded-memory tests for the DataForSEO L1 response cache."""

from __future__ import annotations

from src.clients.dataforseo.cache import ResponseCache


def test_cache_evicts_lru_entries_above_limit() -> None:
    cache = ResponseCache(ttl=3600, max_entries=128)

    for index in range(1_000):
        cache.put("serp", {"keyword": f"keyword-{index}"}, {"rank": index})

    assert len(cache._store) <= 128
    assert cache.get("serp", {"keyword": "keyword-999"}) == {"rank": 999}
    assert cache.get("serp", {"keyword": "keyword-0"}) is None


def test_put_prunes_expired_entries_without_exact_key_read(monkeypatch) -> None:
    now = 100.0
    monkeypatch.setattr("src.clients.dataforseo.cache.time.monotonic", lambda: now)
    cache = ResponseCache(ttl=10, max_entries=128)
    cache.put("serp", {"keyword": "old"}, {"rank": 1})

    now = 111.0
    cache.put("serp", {"keyword": "new"}, {"rank": 2})

    assert len(cache._store) == 1
    assert cache.get("serp", {"keyword": "new"}) == {"rank": 2}


def test_oversized_value_is_not_admitted_to_l1() -> None:
    cache = ResponseCache(ttl=3600, max_value_bytes=2_000_000)
    value = {"payload": "x" * 2_000_001}

    cache.put("serp", {"keyword": "large"}, value)

    assert cache.get("serp", {"keyword": "large"}) is None


def test_none_is_not_admitted_to_l1() -> None:
    cache = ResponseCache(ttl=3600)

    cache.put("serp", {"keyword": "none"}, None)

    assert len(cache._store) == 0
