"""Unit tests for PersistentResponseCache — two-tier cache behavior."""

from __future__ import annotations

from typing import Any

from src.clients.dataforseo.persistent_cache import PersistentResponseCache


class _FakeTable:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: dict[str, Any] = {}
        self._selected_cols: list[str] | None = None
        self._pending_update: dict[str, Any] | None = None

    def select(self, cols: str = "*") -> "_FakeTable":
        if cols.strip() == "*":
            self._selected_cols = None
        else:
            self._selected_cols = [col.strip() for col in cols.split(",")]
        return self

    def eq(self, col: str, val: Any) -> "_FakeTable":
        self._filters[col] = val
        return self

    def limit(self, n: int) -> "_FakeTable":
        return self

    def insert(self, payload: Any) -> "_FakeTable":
        if isinstance(payload, list):
            self._rows.extend(payload)
        else:
            self._rows.append(payload)
        return self

    def upsert(self, payload: Any, **_kwargs: Any) -> "_FakeTable":
        self._rows.append(payload)
        return self

    def update(self, payload: Any) -> "_FakeTable":
        self._pending_update = payload if isinstance(payload, dict) else {}
        return self

    def delete(self) -> "_FakeTable":
        return self

    def execute(self) -> Any:
        filtered = self._rows
        for col, val in self._filters.items():
            filtered = [r for r in filtered if r.get(col) == val]

        if self._pending_update is not None:
            for row in filtered:
                row.update(self._pending_update)
            self._pending_update = None

        selected = filtered
        if self._selected_cols is not None:
            selected = [{col: row.get(col) for col in self._selected_cols} for row in filtered]

        self._filters = {}
        self._selected_cols = None

        class _R:
            data = selected
        return _R()


class _FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}

    def table(self, name: str) -> _FakeTable:
        self.tables.setdefault(name, [])
        return _FakeTable(self.tables[name])


def test_memory_layer_works_without_db() -> None:
    cache = PersistentResponseCache(ttl=3600, client=None)
    cache._db_available = False

    assert cache.get("serp", {"keyword": "test"}) is None
    cache.put("serp", {"keyword": "test"}, {"results": [1, 2, 3]})
    assert cache.get("serp", {"keyword": "test"}) == {"results": [1, 2, 3]}


def test_clear_resets_memory_layer() -> None:
    cache = PersistentResponseCache(ttl=3600, client=None)
    cache._db_available = False

    cache.put("serp", {"keyword": "test"}, {"data": True})
    cache.clear()
    assert cache.get("serp", {"keyword": "test"}) is None


def test_put_writes_to_db_when_available() -> None:
    fake = _FakeSupabase()
    cache = PersistentResponseCache(ttl=3600, client=fake)

    cache.put("serp/organic", {"keyword": "roofing"}, {"items": []}, cost=0.001)
    assert len(fake.tables["api_response_cache"]) == 1
    row = fake.tables["api_response_cache"][0]
    assert row["endpoint"] == "serp/organic"
    assert row["cost_usd"] == 0.001


def test_key_is_deterministic() -> None:
    k1 = PersistentResponseCache._key("serp", {"a": 1, "b": 2})
    k2 = PersistentResponseCache._key("serp", {"b": 2, "a": 1})
    assert k1 == k2


def test_db_hit_increments_hit_count() -> None:
    fake = _FakeSupabase()
    cache = PersistentResponseCache(ttl=3600, client=fake)
    params = {"keyword": "roofing"}
    params_hash = cache._key("serp/organic", params)

    fake.tables["api_response_cache"] = [{
        "id": "row-1",
        "endpoint": "serp/organic",
        "params_hash": params_hash,
        "response_data": {"items": [1]},
        "expires_at": "2099-01-01T00:00:00+00:00",
        "hit_count": 2,
    }]

    assert cache.get("serp/organic", params) == {"items": [1]}
    assert fake.tables["api_response_cache"][0]["hit_count"] == 3
