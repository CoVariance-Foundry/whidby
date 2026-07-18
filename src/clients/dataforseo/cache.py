"""In-memory response cache with configurable TTL."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

from src.config.constants import DFS_CACHE_MAX_ENTRIES, DFS_CACHE_MAX_VALUE_BYTES


class ResponseCache:
    """Simple in-memory cache keyed by (endpoint, params) hash."""

    def __init__(
        self,
        ttl: int,
        *,
        max_entries: int = DFS_CACHE_MAX_ENTRIES,
        max_value_bytes: int = DFS_CACHE_MAX_VALUE_BYTES,
    ) -> None:
        self._ttl = ttl
        self._max_entries = max_entries
        self._max_value_bytes = max_value_bytes
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def _key(self, endpoint: str, params: dict[str, Any]) -> str:
        raw = json.dumps({"endpoint": endpoint, **params}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, endpoint: str, params: dict[str, Any]) -> Any | None:
        key = self._key(endpoint, params)
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return data

    def put(self, endpoint: str, params: dict[str, Any], data: Any, **_kwargs: Any) -> None:
        if data is None:
            return
        now = time.monotonic()
        self._prune_expired(now)
        key = self._key(endpoint, params)
        if not _fits_serialized_limit(data, self._max_value_bytes):
            self._store.pop(key, None)
            return
        self._store[key] = (now, data)
        self._store.move_to_end(key)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()

    def _prune_expired(self, now: float) -> None:
        expired = [key for key, (ts, _) in self._store.items() if now - ts > self._ttl]
        for key in expired:
            del self._store[key]


def _fits_serialized_limit(value: Any, limit: int) -> bool:
    size = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), default=str)
    for chunk in encoder.iterencode(value):
        size += len(chunk.encode())
        if size > limit:
            return False
    return True
