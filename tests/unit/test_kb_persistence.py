"""Unit tests for KBPersistence — entity, snapshot, evidence, feedback CRUD."""

from __future__ import annotations

from typing import Any

from src.clients.kb_persistence import KBPersistence
from src.pipeline.canonical_key import resolve_canonical_key


class _FakeTable:
    def __init__(self, sink: list[dict]) -> None:
        self.sink = sink
        self._filters: dict[str, Any] = {}
        self._select_cols = "*"
        self._limit_n: int | None = None

    def insert(self, payload: Any) -> "_FakeTable":
        if isinstance(payload, list):
            self.sink.extend(payload)
        else:
            self.sink.append(payload)
        return self

    def upsert(self, payload: Any, **_kwargs: Any) -> "_FakeTable":
        if isinstance(payload, list):
            self.sink.extend(payload)
        else:
            self.sink.append(payload)
        return self

    def update(self, payload: Any) -> "_FakeTable":
        for row in self.sink:
            for k, v in (payload if isinstance(payload, dict) else {}).items():
                row[k] = v
        return self

    def select(self, cols: str = "*") -> "_FakeTable":
        self._select_cols = cols
        return self

    def eq(self, col: str, val: Any) -> "_FakeTable":
        self._filters[col] = val
        return self

    def is_(self, col: str, val: Any) -> "_FakeTable":
        return self

    def limit(self, n: int) -> "_FakeTable":
        self._limit_n = n
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> "_FakeTable":
        return self

    def delete(self) -> "_FakeTable":
        return self

    def execute(self) -> Any:
        filtered = self.sink
        for col, val in self._filters.items():
            filtered = [r for r in filtered if r.get(col) == val]
        if self._limit_n:
            filtered = filtered[:self._limit_n]
        self._filters = {}

        class _R:
            data = filtered
        return _R()


class _FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}

    def table(self, name: str) -> _FakeTable:
        self.tables.setdefault(name, [])
        return _FakeTable(self.tables[name])


def test_upsert_entity_creates_and_returns_id() -> None:
    fake = _FakeSupabase()
    kb = KBPersistence(client=fake)
    key = resolve_canonical_key(niche="roofing", city="Phoenix", state="AZ")

    fake.tables["kb_entities"] = [{"id": "ent-1", "niche_keyword_normalized": "roofing"}]
    entity_id = kb.upsert_entity(key)
    assert entity_id == "ent-1"


def test_create_snapshot_inserts_row() -> None:
    fake = _FakeSupabase()
    kb = KBPersistence(client=fake)
    report = {
        "spec_version": "1.1",
        "keyword_expansion": {"expanded_keywords": []},
        "metros": [{
            "scores": {"opportunity": 72}, "signals": {},
            "serp_archetype": "local_first", "ai_exposure": "low",
            "difficulty_tier": "MODERATE", "guidance": {},
        }],
        "meta": {"total_api_calls": 5},
    }

    snap_id = kb.create_snapshot(
        entity_id="ent-1",
        input_hash="abc123",
        strategy_profile="balanced",
        report=report,
        report_id="rpt-1",
    )

    assert snap_id is not None
    assert len(fake.tables["kb_snapshots"]) == 1
    row = fake.tables["kb_snapshots"][0]
    assert row["entity_id"] == "ent-1"
    assert row["is_current"] is True
    assert row["input_hash"] == "abc123"


def test_store_evidence_writes_artifact_row() -> None:
    fake = _FakeSupabase()
    kb = KBPersistence(client=fake)

    artifact_id = kb.store_evidence(
        snapshot_id="snap-1",
        artifact_type="score_bundle",
        payload={"demand": 72},
    )

    assert artifact_id is not None
    assert len(fake.tables["kb_evidence_artifacts"]) == 1
    row = fake.tables["kb_evidence_artifacts"][0]
    assert row["artifact_type"] == "score_bundle"
    assert row["payload"] == {"demand": 72}


def test_insert_feedback_writes_to_feedback_events() -> None:
    fake = _FakeSupabase()
    kb = KBPersistence(client=fake)

    feedback_row = {
        "log_id": "fb-1",
        "context": {"report_id": "rpt-1", "cbsa_code": "38060"},
        "signals": {"demand": {}},
        "scores": {"opportunity": 72},
        "classification": {"serp_archetype": "local_first"},
        "recommendation_rank": 1,
        "outcome": None,
    }

    result_id = kb.insert_feedback(feedback_row)
    assert result_id == "fb-1"
    assert len(fake.tables["feedback_events"]) == 1


def test_link_report_sets_entity_and_snapshot_ids() -> None:
    fake = _FakeSupabase()
    fake.tables["reports"] = [{"id": "rpt-1", "entity_id": None, "snapshot_id": None}]
    kb = KBPersistence(client=fake)

    kb.link_report(report_id="rpt-1", entity_id="ent-1", snapshot_id="snap-1")

    row = fake.tables["reports"][0]
    assert row["entity_id"] == "ent-1"
    assert row["snapshot_id"] == "snap-1"
