"""Knowledge base persistence layer for entities, snapshots, and evidence.

Operates alongside the existing SupabasePersistence (which handles the
presentation-layer reports table).  This module manages the durable KB
tables defined in 007_kb_schema.sql.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from src.pipeline.canonical_key import CanonicalKey

logger = logging.getLogger(__name__)


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any: ...


class KBPersistence:
    """Manages kb_entities, kb_snapshots, kb_evidence_artifacts, and feedback_events."""

    def __init__(self, *, client: _SupabaseLike | None = None) -> None:
        if client is None:
            from supabase import create_client

            url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                missing = [
                    v
                    for v in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
                    if not os.environ.get(v)
                ]
                raise RuntimeError(
                    f"Cannot persist KB data — missing env var(s): {', '.join(missing)}"
                )
            client = create_client(url, key)
        self._client = client

    # ------------------------------------------------------------------
    # Entity operations
    # ------------------------------------------------------------------

    def upsert_entity(self, key: CanonicalKey) -> str:
        """Insert or return existing entity for the canonical key.

        Returns the entity UUID.
        """
        t0 = time.monotonic()
        row = {
            "niche_keyword_normalized": key.niche_normalized,
            "geo_target_normalized": key.geo_normalized,
            "geo_scope": key.geo_scope,
            "place_id": key.place_id,
            "dataforseo_location_code": key.dataforseo_location_code,
            "country_iso_code": "US",
        }
        res = (
            self._client.table("kb_entities")
            .upsert(row, on_conflict="niche_keyword_normalized,geo_target_normalized,geo_scope")
            .execute()
        )
        entity_id = res.data[0]["id"]
        ms = int((time.monotonic() - t0) * 1000)
        logger.info("upsert_entity entity_id=%s duration_ms=%d", entity_id, ms)
        return entity_id

    def find_entity(self, key: CanonicalKey) -> str | None:
        """Look up an existing entity by canonical key.  Returns UUID or None."""
        res = (
            self._client.table("kb_entities")
            .select("id")
            .eq("niche_keyword_normalized", key.niche_normalized)
            .eq("geo_target_normalized", key.geo_normalized)
            .eq("geo_scope", key.geo_scope)
            .limit(1)
            .execute()
        )
        return res.data[0]["id"] if res.data else None

    # ------------------------------------------------------------------
    # Snapshot operations
    # ------------------------------------------------------------------

    def get_current_snapshot(self, entity_id: str) -> dict[str, Any] | None:
        """Return the current snapshot for an entity, or None."""
        res = (
            self._client.table("kb_snapshots")
            .select("*")
            .eq("entity_id", entity_id)
            .eq("is_current", True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def create_snapshot(
        self,
        *,
        entity_id: str,
        input_hash: str,
        strategy_profile: str,
        report: dict[str, Any],
        report_id: str | None = None,
    ) -> str:
        """Create a new current snapshot and supersede any prior one.

        Returns the new snapshot UUID.
        """
        t0 = time.monotonic()
        now = datetime.now(UTC).isoformat()

        previous = self.get_current_snapshot(entity_id)
        next_version = (previous["version"] + 1) if previous else 1

        snapshot_id = str(uuid4())

        metro = report["metros"][0] if report.get("metros") else {}
        row = {
            "id": snapshot_id,
            "entity_id": entity_id,
            "version": next_version,
            "valid_from": now,
            "is_current": True,
            "input_hash": input_hash,
            "strategy_profile": strategy_profile,
            "spec_version": report.get("spec_version", "1.1"),
            "keyword_expansion": report.get("keyword_expansion"),
            "signals": metro.get("signals"),
            "scores": metro.get("scores"),
            "classification": {
                "serp_archetype": metro.get("serp_archetype"),
                "ai_exposure": metro.get("ai_exposure"),
                "difficulty_tier": metro.get("difficulty_tier"),
            } if metro else None,
            "guidance": metro.get("guidance"),
            "meta": report.get("meta"),
            "report_id": report_id,
        }

        if previous:
            prev_id = previous["id"]
            self._client.table("kb_snapshots").update({
                "is_current": False,
                "valid_to": now,
                "superseded_by": snapshot_id,
            }).eq("id", prev_id).execute()

        self._client.table("kb_snapshots").insert(row).execute()

        ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "create_snapshot entity_id=%s snapshot_id=%s version=%d superseded=%s duration_ms=%d",
            entity_id, snapshot_id, next_version, previous["id"] if previous else None, ms,
        )
        return snapshot_id

    # ------------------------------------------------------------------
    # Evidence artifacts
    # ------------------------------------------------------------------

    def store_evidence(
        self,
        *,
        snapshot_id: str,
        artifact_type: str,
        payload: Any,
    ) -> str:
        """Store a raw evidence artifact linked to a snapshot.

        Returns the artifact UUID.
        """
        t0 = time.monotonic()
        serialized = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(serialized.encode()).hexdigest()
        now = datetime.now(UTC).isoformat()

        artifact_id = str(uuid4())
        row = {
            "id": artifact_id,
            "snapshot_id": snapshot_id,
            "artifact_type": artifact_type,
            "payload": payload,
            "payload_hash": payload_hash,
            "source_window_start": now,
            "source_window_end": now,
            "byte_size": len(serialized.encode()),
        }

        self._client.table("kb_evidence_artifacts").insert(row).execute()
        ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "store_evidence snapshot_id=%s type=%s bytes=%d duration_ms=%d",
            snapshot_id, artifact_type, row["byte_size"], ms,
        )
        return artifact_id

    # ------------------------------------------------------------------
    # Feedback events
    # ------------------------------------------------------------------

    def insert_feedback(self, row: dict[str, Any]) -> str:
        """Insert a feedback event row.  Returns the row UUID."""
        feedback_id = row.get("log_id") or str(uuid4())
        db_row = {
            "id": feedback_id,
            "report_id": row.get("context", {}).get("report_id"),
            "context": row.get("context", {}),
            "signals": row.get("signals", {}),
            "scores": row.get("scores", {}),
            "classification": row.get("classification", {}),
            "recommendation_rank": row.get("recommendation_rank"),
            "outcome": row.get("outcome"),
        }
        self._client.table("feedback_events").insert(db_row).execute()
        return feedback_id

    # ------------------------------------------------------------------
    # Link reports to KB lineage
    # ------------------------------------------------------------------

    def link_report(
        self, *, report_id: str, entity_id: str, snapshot_id: str
    ) -> None:
        """Set entity_id and snapshot_id on an existing reports row."""
        self._client.table("reports").update({
            "entity_id": entity_id,
            "snapshot_id": snapshot_id,
        }).eq("id", report_id).execute()
