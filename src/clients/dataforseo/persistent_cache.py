"""Persistent response cache backed by Supabase api_response_cache table.

Falls back to the in-memory ResponseCache when Supabase credentials are
unavailable (e.g. unit tests).  The two layers compose: in-memory is the
hot L1 with monotonic-clock TTL; Supabase is the cold L2 with wall-clock
expiration shared across processes/restarts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from .cache import ResponseCache

logger = logging.getLogger(__name__)


class PersistentResponseCache:
    """Two-tier cache: in-memory L1 + Supabase L2."""

    def __init__(self, ttl: int, *, client: Any | None = None) -> None:
        self._ttl = ttl
        self._memory = ResponseCache(ttl=ttl)
        self._client = client
        self._db_available = client is not None

        if self._client is None:
            url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if url and key:
                try:
                    from supabase import create_client
                    self._client = create_client(url, key)
                    self._db_available = True
                except Exception:
                    logger.warning("PersistentResponseCache: Supabase init failed, DB layer disabled")

    @staticmethod
    def _key(endpoint: str, params: dict[str, Any]) -> str:
        raw = json.dumps({"endpoint": endpoint, **params}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, endpoint: str, params: dict[str, Any]) -> Any | None:
        mem_hit = self._memory.get(endpoint, params)
        if mem_hit is not None:
            return mem_hit

        if not self._db_available:
            return None

        params_hash = self._key(endpoint, params)
        try:
            res = (
                self._client.table("api_response_cache")
                .select("id, response_data, expires_at, hit_count")
                .eq("endpoint", endpoint)
                .eq("params_hash", params_hash)
                .limit(1)
                .execute()
            )
            if not res.data:
                return None

            row = res.data[0]
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            if expires_at <= datetime.now(UTC):
                self._client.table("api_response_cache").delete().eq("id", row["id"]).execute()
                return None

            data = row["response_data"]
            self._memory.put(endpoint, params, data)

            self._client.table("api_response_cache").update({
                "hit_count": row.get("hit_count", 0) + 1,
                "last_hit_at": datetime.now(UTC).isoformat(),
            }).eq("id", row["id"]).execute()

            return data
        except Exception:
            logger.warning("PersistentResponseCache.get DB read failed", exc_info=True)
            return None

    def put(self, endpoint: str, params: dict[str, Any], data: Any, *, cost: float = 0.0) -> None:
        self._memory.put(endpoint, params, data)

        if not self._db_available:
            return

        params_hash = self._key(endpoint, params)
        expires_at = (datetime.now(UTC) + timedelta(seconds=self._ttl)).isoformat()
        row = {
            "endpoint": endpoint,
            "params_hash": params_hash,
            "params": params,
            "response_data": data,
            "expires_at": expires_at,
            "cost_usd": cost,
            "hit_count": 0,
        }
        try:
            self._client.table("api_response_cache").upsert(
                row, on_conflict="endpoint,params_hash"
            ).execute()
        except Exception:
            logger.warning("PersistentResponseCache.put DB write failed", exc_info=True)

    def clear(self) -> None:
        self._memory.clear()
