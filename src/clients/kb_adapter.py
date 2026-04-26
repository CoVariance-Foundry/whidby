"""Adapter wrapping KBPersistence to implement KnowledgeStore protocol."""
from __future__ import annotations

from typing import Any

from src.clients.kb_persistence import KBPersistence


class KBKnowledgeStore:
    """Implements KnowledgeStore using existing KBPersistence."""

    def __init__(self, kb: KBPersistence) -> None:
        self._kb = kb

    def upsert_entity(self, key: Any) -> str:
        return self._kb.upsert_entity(key)

    def create_snapshot(self, entity_id: str, **kwargs: Any) -> str:
        return self._kb.create_snapshot(entity_id=entity_id, **kwargs)

    def store_evidence(
        self, snapshot_id: str, artifact_type: str, payload: Any
    ) -> None:
        self._kb.store_evidence(
            snapshot_id=snapshot_id, artifact_type=artifact_type, payload=payload
        )

    def link_report(
        self, *, report_id: str, entity_id: str, snapshot_id: str
    ) -> None:
        self._kb.link_report(
            report_id=report_id, entity_id=entity_id, snapshot_id=snapshot_id
        )

    def insert_feedback(self, row: dict[str, Any]) -> str:
        return self._kb.insert_feedback(row)
