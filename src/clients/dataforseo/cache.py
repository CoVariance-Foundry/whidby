"""In-memory response cache with configurable TTL."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any


class ResponseCache:
    """Simple in-memory cache keyed by (endpoint, params) hash."""

    def __init__(self, ttl: int) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

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
        return data

    def put(self, endpoint: str, params: dict[str, Any], data: Any) -> None:
        key = self._key(endpoint, params)
        self._store[key] = (time.monotonic(), data)

    def clear(self) -> None:
        self._store.clear()
