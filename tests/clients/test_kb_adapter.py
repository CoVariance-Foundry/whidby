"""Tests for KBKnowledgeStore adapter."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.clients.kb_adapter import KBKnowledgeStore


@pytest.fixture
def fake_kb() -> MagicMock:
    kb = MagicMock()
    kb.upsert_entity.return_value = "entity-1"
    kb.create_snapshot.return_value = "snap-1"
    kb.store_evidence.return_value = "artifact-1"
    kb.link_report.return_value = None
    kb.insert_feedback.return_value = "fb-1"
    return kb


@pytest.fixture
def store(fake_kb: MagicMock) -> KBKnowledgeStore:
    return KBKnowledgeStore(fake_kb)


def test_upsert_entity_delegates(store: KBKnowledgeStore, fake_kb: MagicMock) -> None:
    key = MagicMock()
    result = store.upsert_entity(key)
    assert result == "entity-1"
    fake_kb.upsert_entity.assert_called_once_with(key)


def test_create_snapshot_delegates(store: KBKnowledgeStore, fake_kb: MagicMock) -> None:
    result = store.create_snapshot(
        entity_id="e1",
        input_hash="abc",
        strategy_profile="balanced",
        report={"metros": []},
        report_id="r1",
    )
    assert result == "snap-1"
    fake_kb.create_snapshot.assert_called_once_with(
        entity_id="e1",
        input_hash="abc",
        strategy_profile="balanced",
        report={"metros": []},
        report_id="r1",
    )


def test_store_evidence_delegates(store: KBKnowledgeStore, fake_kb: MagicMock) -> None:
    store.store_evidence(
        snapshot_id="s1", artifact_type="score_bundle", payload=[{"scores": {}}]
    )
    fake_kb.store_evidence.assert_called_once_with(
        snapshot_id="s1", artifact_type="score_bundle", payload=[{"scores": {}}]
    )


def test_link_report_delegates(store: KBKnowledgeStore, fake_kb: MagicMock) -> None:
    store.link_report(report_id="r1", entity_id="e1", snapshot_id="s1")
    fake_kb.link_report.assert_called_once_with(
        report_id="r1", entity_id="e1", snapshot_id="s1"
    )


def test_insert_feedback_delegates(store: KBKnowledgeStore, fake_kb: MagicMock) -> None:
    row = {"log_id": "x", "context": {}}
    result = store.insert_feedback(row)
    assert result == "fb-1"
    fake_kb.insert_feedback.assert_called_once_with(row)
