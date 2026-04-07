"""Supabase-backed observation persistence and TTL-aware cache.

Stores every DataForSEO API response as an immutable observation with
metadata in Postgres and the full payload in Supabase Storage as gzipped JSON.
"""

from __future__ import annotations

import gzip
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config.constants import TTL_DURATIONS

logger = logging.getLogger(__name__)


def _endpoint_group(endpoint: str) -> str:
    """Derive a storage-path-friendly group name from an endpoint path."""
    return endpoint.split("/")[0].replace("_", "-") if "/" in endpoint else endpoint


def _build_storage_path(
    ttl_category: str,
    query_hash: str,
    observation_id: str,
    observed_at: datetime,
) -> str:
    return (
        f"observations/{ttl_category}/"
        f"{observed_at.year}/{observed_at.month:02d}/{observed_at.day:02d}/"
        f"{query_hash}_{observation_id}.json.gz"
    )


class ObservationStore:
    """Persistent observation store backed by Supabase Postgres + Storage.

    Args:
        supabase_client: Initialised Supabase client instance.
        bucket_name: Supabase Storage bucket for payloads (default ``observations``).
    """

    def __init__(self, supabase_client: Any, bucket_name: str = "observations") -> None:
        self._sb = supabase_client
        self._bucket = bucket_name

    def check_cache(self, query_hash: str) -> dict[str, Any] | None:
        """Look up a fresh, healthy observation by *query_hash*.

        Returns a dict with ``hit=True`` and the deserialized payload on a
        cache hit, or ``None`` on miss / error / partial / expired.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            resp = (
                self._sb.table("observations")
                .select("*")
                .eq("query_hash", query_hash)
                .eq("status", "ok")
                .gt("expires_at", now_iso)
                .order("observed_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning("Observation cache lookup failed for hash=%s", query_hash, exc_info=True)
            return None

        rows = resp.data if resp.data else []
        if not rows:
            return None

        row = rows[0]
        if row.get("payload_purged"):
            return None

        storage_path = row.get("storage_path")
        if not storage_path:
            return None

        payload = self.download_payload(storage_path)
        if payload is None:
            return None

        return {
            "hit": True,
            "query_hash": query_hash,
            "observation_id": row["id"],
            "payload": payload,
            "observed_at": row["observed_at"],
            "expires_at": row["expires_at"],
        }

    def store(
        self,
        endpoint: str,
        params: dict[str, Any],
        query_hash: str,
        ttl_category: str,
        data: Any,
        cost_usd: float,
        source: str = "pipeline",
        run_id: str | None = None,
        queue_mode: str | None = None,
    ) -> dict[str, Any] | None:
        """Persist an observation: upload payload to Storage, insert index row.

        On Storage failure the index row is written with ``status='partial'``
        so the caller can fall through to the in-memory cache.
        """
        obs_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ttl_seconds = TTL_DURATIONS.get(ttl_category, TTL_DURATIONS["serp"])
        expires_at = now + timedelta(seconds=ttl_seconds)

        compressed = gzip.compress(json.dumps(data, default=str).encode())
        storage_path = _build_storage_path(ttl_category, query_hash, obs_id, now)

        upload_ok = True
        try:
            self._sb.storage.from_(self._bucket).upload(
                storage_path,
                compressed,
                file_options={"content-type": "application/gzip"},
            )
        except Exception:
            logger.warning(
                "Storage upload failed for %s; writing partial observation",
                storage_path,
                exc_info=True,
            )
            upload_ok = False
            storage_path = None

        row = {
            "id": obs_id,
            "endpoint": endpoint,
            "query_params": params,
            "query_hash": query_hash,
            "observed_at": now.isoformat(),
            "source": source,
            "run_id": run_id,
            "cost_usd": cost_usd,
            "api_queue_mode": queue_mode,
            "storage_path": storage_path,
            "payload_size_bytes": len(compressed) if upload_ok else None,
            "ttl_category": ttl_category,
            "expires_at": expires_at.isoformat(),
            "status": "ok" if upload_ok else "partial",
            "error_message": "Storage upload failed" if not upload_ok else None,
        }

        try:
            self._sb.table("observations").insert(row).execute()
        except Exception:
            logger.error("Failed to insert observation index row", exc_info=True)
            return None

        return row

    def download_payload(self, storage_path: str) -> Any | None:
        """Download and decompress a gzipped JSON payload from Storage."""
        try:
            raw = self._sb.storage.from_(self._bucket).download(storage_path)
            return json.loads(gzip.decompress(raw))
        except Exception:
            logger.warning("Payload download failed: %s", storage_path, exc_info=True)
            return None
