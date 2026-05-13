# Phase 3: Create MarketService — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract all business logic from the `niches_score` API handler in `src/research_agent/api.py` into `MarketService`, making the handler a thin HTTP wrapper. Create infrastructure adapters implementing domain ports.

**Architecture:** MarketService coordinates the full scoring flow: canonical key resolution → pipeline execution (via injected `score_niche_for_metro`) → report persistence → KB entity/snapshot/evidence updates → cost flush → feedback logging → response shaping. Infrastructure is injected at construction. The handler becomes ~15 lines: parse request → call service → return response. The orchestrator (`src/pipeline/orchestrator.py`) is NOT modified — it continues to handle geo resolution and M4–M9 internally.

**Key Design Decisions:**

1. **Pipeline injected, utilities imported pragmatically.** MarketService receives `score_niche_for_metro` as a callable `pipeline_fn` param — the pipeline is the heavyweight dependency and injection makes testing trivial (no patches). However, `resolve_canonical_key` and `log_feedback` are imported directly from `src.pipeline` as lightweight utilities. Moving `CanonicalKey` and feedback logic into `src/domain/` is deferred to Phase 4.
2. **No SERPDataProvider/KeywordExpander adapters.** The orchestrator accepts `Any`-typed `dataforseo_client`/`llm_client` and uses them directly. Creating domain port adapters for these would be unused code. Deferred to Phase 4 when orchestrator internals get refactored.
3. **No double geo resolution.** The orchestrator resolves geo internally via `GeoResolver`. MarketService only calls `resolve_canonical_key` (KB identity normalization, separate from geo resolution).
4. **SupabaseMarketStore and KBKnowledgeStore adapters ARE created** — thin wrappers implementing the domain ports for persistence operations MarketService actually performs.
5. **Response contract preserved exactly.** `ScoreResult.to_api_response()` produces the exact same JSON shape the handler currently returns, including conditional `persist_warning`, `entity_id`, `snapshot_id`.

**Intentional behavior change — dry_run persistence:**
The existing handler persists reports and updates KB even on `dry_run=True` requests (the `_persist_report` call is unconditional). MarketService corrects this: `dry_run=True` skips persistence, KB updates, cost flush, and feedback logging. This matches the Phase 3 spec's intent and the `dry_run` contract. The test in `test_api_niches.py` is updated accordingly (`report_id` becomes `None` for dry_run).

**Tech Stack:** Python 3.11, pytest, dataclasses, Protocol typing, FastAPI

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/clients/supabase_adapter.py` | SupabaseMarketStore — wraps SupabasePersistence, implements MarketStore port |
| Create | `src/clients/kb_adapter.py` | KBKnowledgeStore — wraps KBPersistence, implements KnowledgeStore port |
| Create | `src/domain/services/market_service.py` | MarketService, ScoreRequest, ScoreResult |
| Create | `tests/domain/services/fakes.py` | Shared test fakes for MarketService dependencies |
| Create | `tests/domain/services/test_market_service.py` | Unit tests for MarketService with fakes |
| Create | `tests/clients/test_supabase_adapter.py` | Unit tests for SupabaseMarketStore |
| Create | `tests/clients/test_kb_adapter.py` | Unit tests for KBKnowledgeStore |
| Modify | `src/domain/ports.py:47-53` | Add `link_report` + `insert_feedback` to KnowledgeStore |
| Modify | `src/research_agent/api.py:280-590` | Thin handler + startup wiring |
| Modify | `src/domain/services/__init__.py` | Export MarketService, ScoreRequest, ScoreResult |
| Modify | `tests/unit/test_api_niches.py` | Migrate patches to MarketService injection |
| Modify | `docs/product_breakdown.md` | Docs sync (pre-commit gate) |

---

### Task 0: Create Worktree

- [ ] **Step 1: Create an isolated worktree from dev branch**

```bash
git worktree add .worktrees/phase-3-market-service dev
cd .worktrees/phase-3-market-service
```

- [ ] **Step 2: Create feature branch**

```bash
git checkout -b phase-3-market-service
```

All subsequent tasks execute inside `.worktrees/phase-3-market-service/`.

---

### Task 1: Extend KnowledgeStore Port

**Files:**
- Modify: `src/domain/ports.py:47-53`

- [ ] **Step 1: Add `link_report` and `insert_feedback` to KnowledgeStore protocol**

In `src/domain/ports.py`, the current `KnowledgeStore` protocol is:

```python
class KnowledgeStore(Protocol):
    def upsert_entity(self, key: Any) -> str: ...
    def create_snapshot(self, entity_id: str, **kwargs: Any) -> str: ...
    def store_evidence(
        self, snapshot_id: str, artifact_type: str, payload: Any
    ) -> None: ...
```

Replace with:

```python
class KnowledgeStore(Protocol):
    def upsert_entity(self, key: Any) -> str: ...
    def create_snapshot(self, entity_id: str, **kwargs: Any) -> str: ...
    def store_evidence(
        self, snapshot_id: str, artifact_type: str, payload: Any
    ) -> None: ...
    def link_report(
        self, *, report_id: str, entity_id: str, snapshot_id: str
    ) -> None: ...
    def insert_feedback(self, row: dict[str, Any]) -> str: ...
```

- [ ] **Step 2: Run existing domain tests to verify no regressions**

Run: `python -m pytest tests/domain/ -v`
Expected: All existing tests PASS (protocol extension is additive)

- [ ] **Step 3: Commit**

```bash
git add src/domain/ports.py
git commit -m "feat(domain): extend KnowledgeStore protocol with link_report and insert_feedback"
```

---

### Task 2: Create SupabaseMarketStore Adapter (TDD)

**Files:**
- Create: `tests/clients/test_supabase_adapter.py`
- Create: `src/clients/supabase_adapter.py`

- [ ] **Step 1: Create test directory**

```bash
mkdir -p tests/clients
touch tests/clients/__init__.py
```

- [ ] **Step 2: Write the failing tests**

Create `tests/clients/test_supabase_adapter.py`:

```python
"""Tests for SupabaseMarketStore adapter."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.clients.supabase_adapter import SupabaseMarketStore


@pytest.fixture
def fake_persistence() -> MagicMock:
    p = MagicMock()
    p.persist_report.return_value = "report-123"
    p._client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "report-123", "niche_keyword": "plumbing"}]
    )
    return p


@pytest.fixture
def store(fake_persistence: MagicMock) -> SupabaseMarketStore:
    return SupabaseMarketStore(fake_persistence)


def test_persist_report_delegates_to_persistence(
    store: SupabaseMarketStore, fake_persistence: MagicMock
) -> None:
    report = {"report_id": "r1", "input": {}, "metros": [], "meta": {}}
    result = store.persist_report(report)
    assert result == "report-123"
    fake_persistence.persist_report.assert_called_once_with(report)


def test_read_report_queries_supabase(
    store: SupabaseMarketStore, fake_persistence: MagicMock
) -> None:
    result = store.read_report("report-123")
    assert result is not None
    assert result["id"] == "report-123"


def test_read_report_returns_none_when_not_found(
    fake_persistence: MagicMock,
) -> None:
    fake_persistence._client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    store = SupabaseMarketStore(fake_persistence)
    assert store.read_report("nonexistent") is None


def test_query_markets_returns_empty_list(
    store: SupabaseMarketStore,
) -> None:
    from src.domain.queries import MarketQuery
    assert store.query_markets(MarketQuery()) == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/clients/test_supabase_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.clients.supabase_adapter'`

- [ ] **Step 4: Write the implementation**

Create `src/clients/supabase_adapter.py`:

```python
"""Adapter wrapping SupabasePersistence to implement MarketStore protocol."""
from __future__ import annotations

from typing import Any

from src.clients.supabase_persistence import SupabasePersistence
from src.domain.entities import Market
from src.domain.queries import MarketQuery


class SupabaseMarketStore:
    """Implements MarketStore using existing SupabasePersistence."""

    def __init__(self, persistence: SupabasePersistence) -> None:
        self._persistence = persistence

    def persist_report(self, report: dict[str, Any]) -> str:
        return self._persistence.persist_report(report)

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        res = (
            self._persistence._client
            .table("reports")
            .select("*")
            .eq("id", report_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def query_markets(self, query: MarketQuery) -> list[Market]:
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/clients/test_supabase_adapter.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/clients/supabase_adapter.py tests/clients/test_supabase_adapter.py tests/clients/__init__.py
git commit -m "feat(clients): add SupabaseMarketStore adapter implementing MarketStore port"
```

---

### Task 3: Create KBKnowledgeStore Adapter (TDD)

**Files:**
- Create: `tests/clients/test_kb_adapter.py`
- Create: `src/clients/kb_adapter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/clients/test_kb_adapter.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/clients/test_kb_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.clients.kb_adapter'`

- [ ] **Step 3: Write the implementation**

Create `src/clients/kb_adapter.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/clients/test_kb_adapter.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/clients/kb_adapter.py tests/clients/test_kb_adapter.py
git commit -m "feat(clients): add KBKnowledgeStore adapter implementing KnowledgeStore port"
```

---

### Task 4: Create MarketService with ScoreRequest/ScoreResult (TDD)

This is the core task. MarketService transplants all business logic from the `niches_score` handler (`src/research_agent/api.py:445-590`).

**Files:**
- Create: `tests/domain/services/fakes.py`
- Create: `tests/domain/services/test_market_service.py`
- Create: `src/domain/services/market_service.py`

- [ ] **Step 1: Extract shared test fakes**

Create `tests/domain/services/fakes.py` — shared fakes used by both MarketService tests and API handler tests:

```python
"""Shared test fakes for MarketService dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FakePipelineResult:
    report: dict[str, Any]
    opportunity_score: int
    evidence: list[dict[str, Any]]


def make_fake_report(
    report_id: str = "rpt-1",
    niche: str = "plumbing",
    city: str = "Boise",
    state: str = "ID",
) -> dict[str, Any]:
    return {
        "report_id": report_id,
        "generated_at": "2026-04-25T00:00:00+00:00",
        "spec_version": "1.1",
        "input": {
            "niche_keyword": niche,
            "geo_scope": "city",
            "geo_target": f"{city}, {state}",
            "report_depth": "standard",
            "strategy_profile": "balanced",
        },
        "keyword_expansion": {
            "niche": niche,
            "expanded_keywords": [
                {"keyword": niche, "tier": 1, "intent": "transactional",
                 "source": "llm", "aio_risk": "low"},
            ],
        },
        "metros": [
            {
                "cbsa_code": "14260",
                "cbsa_name": f"{city}, {state}",
                "population": 800000,
                "scores": {
                    "demand": 70, "organic_competition": 40,
                    "local_competition": 55, "monetization": 65,
                    "ai_resilience": 80, "opportunity": 72,
                    "confidence": {"score": 82, "flags": []},
                },
                "confidence": {"score": 82, "flags": []},
                "serp_archetype": "local_first",
                "ai_exposure": "low",
                "difficulty_tier": "T2",
                "signals": {"demand": {"tier_1_volume_effective": 1000}},
                "guidance": {"summary": "Good opportunity"},
            }
        ],
        "meta": {
            "total_api_calls": 5,
            "total_cost_usd": 0.02,
            "processing_time_seconds": 2.5,
            "feedback_log_id": "fb-1",
        },
    }


async def fake_pipeline(**kwargs: Any) -> FakePipelineResult:
    return FakePipelineResult(
        report=make_fake_report(),
        opportunity_score=72,
        evidence=[
            {"category": "demand", "label": "Volume", "value": 1000,
             "source": "M6", "is_available": True},
        ],
    )


async def failing_pipeline(**kwargs: Any) -> FakePipelineResult:
    raise ValueError("no CBSA match for city='Nowhere' state=None")


class FakeMarketStore:
    def __init__(self) -> None:
        self.reports: dict[str, Any] = {}
        self.fail_persist: bool = False

    def persist_report(self, report: dict[str, Any]) -> str:
        if self.fail_persist:
            raise RuntimeError("Supabase down")
        rid = report["report_id"]
        self.reports[rid] = report
        return rid

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        return self.reports.get(report_id)

    def query_markets(self, query: Any) -> list:
        return []


class FakeKnowledgeStore:
    def __init__(self) -> None:
        self.entities: dict[str, Any] = {}
        self.snapshots: dict[str, Any] = {}
        self.evidence: list[tuple[str, str, Any]] = []
        self.links: list[tuple[str, str, str]] = []
        self.feedback_rows: list[dict[str, Any]] = []

    def upsert_entity(self, key: Any) -> str:
        eid = f"entity-{len(self.entities) + 1}"
        self.entities[eid] = key
        return eid

    def create_snapshot(self, entity_id: str, **kwargs: Any) -> str:
        sid = f"snap-{len(self.snapshots) + 1}"
        self.snapshots[sid] = {"entity_id": entity_id, **kwargs}
        return sid

    def store_evidence(
        self, snapshot_id: str, artifact_type: str, payload: Any
    ) -> None:
        self.evidence.append((snapshot_id, artifact_type, payload))

    def link_report(
        self, *, report_id: str, entity_id: str, snapshot_id: str
    ) -> None:
        self.links.append((report_id, entity_id, snapshot_id))

    def insert_feedback(self, row: dict[str, Any]) -> str:
        fid = f"fb-{len(self.feedback_rows) + 1}"
        self.feedback_rows.append(row)
        return fid


class FakeDFSClient:
    """Mimics DataForSEOClient enough for cost flush."""

    def __init__(self) -> None:
        self.cost_tracker = _FakeCostTracker()


class _FakeCostTracker:
    def __init__(self) -> None:
        self.flushed_report_ids: list[str] = []

    def flush_to_supabase(self, report_id: str) -> None:
        self.flushed_report_ids.append(report_id)
```

- [ ] **Step 2: Write the failing tests**

Create `tests/domain/services/test_market_service.py`:

```python
"""Tests for MarketService — scoring orchestration without infrastructure."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.domain.services.market_service import MarketService, ScoreRequest, ScoreResult
from tests.domain.services.fakes import (
    FakeDFSClient,
    FakeKnowledgeStore,
    FakeMarketStore,
    FakePipelineResult,
    failing_pipeline,
    fake_pipeline,
    make_fake_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> FakeMarketStore:
    return FakeMarketStore()


@pytest.fixture
def kb() -> FakeKnowledgeStore:
    return FakeKnowledgeStore()


@pytest.fixture
def dfs() -> FakeDFSClient:
    return FakeDFSClient()


@pytest.fixture
def service(
    store: FakeMarketStore,
    kb: FakeKnowledgeStore,
    dfs: FakeDFSClient,
) -> MarketService:
    return MarketService(
        pipeline_fn=fake_pipeline,
        dfs_client=dfs,
        llm_client=None,
        market_store=store,
        knowledge_store=kb,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_score_returns_score_result(service: MarketService) -> None:
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    result = asyncio.run(service.score(req))
    assert isinstance(result, ScoreResult)
    assert result.opportunity_score == 72
    assert result.niche == "plumbing"


def test_score_classification_label_high(service: MarketService) -> None:
    async def high_score_pipeline(**kwargs: Any) -> FakePipelineResult:
        r = make_fake_report()
        return FakePipelineResult(report=r, opportunity_score=80, evidence=[])

    svc = MarketService(
        pipeline_fn=high_score_pipeline,
        market_store=FakeMarketStore(),
        knowledge_store=FakeKnowledgeStore(),
    )
    result = asyncio.run(svc.score(ScoreRequest(niche="x", city="y", state="Z")))
    assert result.classification_label == "High"


def test_score_classification_label_medium(service: MarketService) -> None:
    result = asyncio.run(service.score(
        ScoreRequest(niche="plumbing", city="Boise", state="ID")
    ))
    assert result.classification_label == "Medium"


def test_score_classification_label_low() -> None:
    async def low_pipeline(**kwargs: Any) -> FakePipelineResult:
        r = make_fake_report()
        return FakePipelineResult(report=r, opportunity_score=30, evidence=[])

    svc = MarketService(
        pipeline_fn=low_pipeline,
        market_store=FakeMarketStore(),
        knowledge_store=FakeKnowledgeStore(),
    )
    result = asyncio.run(svc.score(ScoreRequest(niche="x", city="y", state="Z")))
    assert result.classification_label == "Low"


def test_score_persists_report(
    service: MarketService, store: FakeMarketStore
) -> None:
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    result = asyncio.run(service.score(req))
    assert result.report_id == "rpt-1"
    assert "rpt-1" in store.reports


def test_score_updates_kb(
    service: MarketService, kb: FakeKnowledgeStore
) -> None:
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    result = asyncio.run(service.score(req))
    assert result.entity_id is not None
    assert result.snapshot_id is not None
    assert len(kb.entities) == 1
    assert len(kb.snapshots) == 1
    assert len(kb.evidence) >= 1
    assert len(kb.links) == 1


def test_score_stores_two_evidence_artifacts(
    service: MarketService, kb: FakeKnowledgeStore
) -> None:
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    asyncio.run(service.score(req))
    types = [e[1] for e in kb.evidence]
    assert "score_bundle" in types
    assert "keyword_expansion" in types


def test_score_flushes_dfs_costs(
    service: MarketService, dfs: FakeDFSClient
) -> None:
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    asyncio.run(service.score(req))
    assert dfs.cost_tracker.flushed_report_ids == ["rpt-1"]


def test_score_logs_feedback(
    service: MarketService, kb: FakeKnowledgeStore
) -> None:
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    asyncio.run(service.score(req))
    assert len(kb.feedback_rows) >= 1


def test_dry_run_skips_persistence(
    store: FakeMarketStore, kb: FakeKnowledgeStore, dfs: FakeDFSClient
) -> None:
    svc = MarketService(
        pipeline_fn=fake_pipeline,
        dfs_client=dfs,
        llm_client=None,
        market_store=store,
        knowledge_store=kb,
    )
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID", dry_run=True)
    result = asyncio.run(svc.score(req))
    assert result.report_id is None
    assert len(store.reports) == 0
    assert len(kb.entities) == 0
    assert len(dfs.cost_tracker.flushed_report_ids) == 0


def test_persist_failure_returns_warning(
    kb: FakeKnowledgeStore, dfs: FakeDFSClient
) -> None:
    failing_store = FakeMarketStore()
    failing_store.fail_persist = True
    svc = MarketService(
        pipeline_fn=fake_pipeline,
        dfs_client=dfs,
        llm_client=None,
        market_store=failing_store,
        knowledge_store=kb,
    )
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    result = asyncio.run(svc.score(req))
    assert result.persist_warning is not None
    assert "failed to save" in result.persist_warning.lower()
    assert result.report_id == "rpt-1"


def test_persist_failure_skips_feedback(
    kb: FakeKnowledgeStore, dfs: FakeDFSClient
) -> None:
    failing_store = FakeMarketStore()
    failing_store.fail_persist = True
    svc = MarketService(
        pipeline_fn=fake_pipeline,
        dfs_client=dfs,
        llm_client=None,
        market_store=failing_store,
        knowledge_store=kb,
    )
    req = ScoreRequest(niche="plumbing", city="Boise", state="ID")
    asyncio.run(svc.score(req))
    assert len(kb.feedback_rows) == 0


def test_pipeline_valueerror_propagates() -> None:
    svc = MarketService(
        pipeline_fn=failing_pipeline,
        market_store=FakeMarketStore(),
        knowledge_store=FakeKnowledgeStore(),
    )
    req = ScoreRequest(niche="plumbing", city="Nowhere")
    with pytest.raises(ValueError, match="no CBSA match"):
        asyncio.run(svc.score(req))


def test_to_api_response_matches_wire_contract() -> None:
    result = ScoreResult(
        report_id="r-123",
        opportunity_score=72,
        classification_label="Medium",
        evidence=[{"category": "demand"}],
        report={"report_id": "r-123"},
        entity_id="e-1",
        snapshot_id="s-1",
        niche="plumbing",
    )
    resp = result.to_api_response()
    assert resp["report_id"] == "r-123"
    assert resp["opportunity_score"] == 72
    assert resp["classification_label"] == "Medium"
    assert resp["evidence"] == [{"category": "demand"}]
    assert resp["report"] == {"report_id": "r-123"}
    assert resp["entity_id"] == "e-1"
    assert resp["snapshot_id"] == "s-1"
    assert "persist_warning" not in resp


def test_to_api_response_includes_persist_warning_when_set() -> None:
    result = ScoreResult(
        report_id="r-123",
        opportunity_score=72,
        classification_label="Medium",
        evidence=[],
        report={},
        entity_id=None,
        snapshot_id=None,
        niche="plumbing",
        persist_warning="Report scored successfully but failed to save to database",
    )
    resp = result.to_api_response()
    assert resp["persist_warning"] == "Report scored successfully but failed to save to database"


def test_score_passes_dry_run_to_pipeline() -> None:
    calls: list[dict[str, Any]] = []

    async def tracking_pipeline(**kwargs: Any) -> FakePipelineResult:
        calls.append(kwargs)
        return FakePipelineResult(
            report=make_fake_report(), opportunity_score=72, evidence=[]
        )

    svc = MarketService(
        pipeline_fn=tracking_pipeline,
        dfs_client=FakeDFSClient(),
        llm_client=None,
        market_store=FakeMarketStore(),
        knowledge_store=FakeKnowledgeStore(),
    )
    asyncio.run(svc.score(
        ScoreRequest(niche="plumbing", city="Boise", state="ID", dry_run=True)
    ))
    assert calls[0]["dry_run"] is True
    assert calls[0]["llm_client"] is None
    assert calls[0]["dataforseo_client"] is None


def test_score_passes_clients_to_pipeline_when_not_dry_run() -> None:
    calls: list[dict[str, Any]] = []
    dfs = FakeDFSClient()

    async def tracking_pipeline(**kwargs: Any) -> FakePipelineResult:
        calls.append(kwargs)
        return FakePipelineResult(
            report=make_fake_report(), opportunity_score=72, evidence=[]
        )

    svc = MarketService(
        pipeline_fn=tracking_pipeline,
        dfs_client=dfs,
        llm_client="fake-llm",
        market_store=FakeMarketStore(),
        knowledge_store=FakeKnowledgeStore(),
    )
    asyncio.run(svc.score(
        ScoreRequest(niche="plumbing", city="Boise", state="ID")
    ))
    assert calls[0]["dataforseo_client"] is dfs
    assert calls[0]["llm_client"] == "fake-llm"
    assert "dry_run" not in calls[0] or calls[0].get("dry_run") is not True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/services/test_market_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.domain.services.market_service'`

- [ ] **Step 3: Write the MarketService implementation**

Create `src/domain/services/market_service.py`:

```python
"""MarketService — single-market scoring orchestration.

Extracted from the niches_score handler in api.py.
Coordinates: canonical key → pipeline execution → persistence → KB update → feedback.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import uuid4

from src.pipeline.canonical_key import resolve_canonical_key
from src.pipeline.feedback_logger import log_feedback

logger = logging.getLogger(__name__)


@dataclass
class ScoreRequest:
    """Input for scoring a single market. Maps from API request params."""

    niche: str
    city: str
    state: str | None = None
    place_id: str | None = None
    dataforseo_location_code: int | None = None
    strategy_profile: str = "balanced"
    dry_run: bool = False


@dataclass
class ScoreResult:
    """Output of scoring a single market. Handler maps this to API response."""

    report_id: str | None
    opportunity_score: int
    classification_label: str
    evidence: list[dict[str, Any]]
    report: dict[str, Any]
    entity_id: str | None
    snapshot_id: str | None
    niche: str
    persist_warning: str | None = None

    def to_api_response(self) -> dict[str, Any]:
        resp: dict[str, Any] = {
            "report_id": self.report_id,
            "opportunity_score": self.opportunity_score,
            "classification_label": self.classification_label,
            "evidence": self.evidence,
            "report": self.report,
            "entity_id": self.entity_id,
            "snapshot_id": self.snapshot_id,
        }
        if self.persist_warning:
            resp["persist_warning"] = self.persist_warning
        return resp


class MarketService:
    """Scores a single market: pipeline → persist → KB → feedback.

    All infrastructure is injected — no direct client construction.
    """

    def __init__(
        self,
        *,
        pipeline_fn: Callable[..., Awaitable[Any]],
        dfs_client: Any | None = None,
        llm_client: Any | None = None,
        market_store: Any,
        knowledge_store: Any,
    ) -> None:
        self._pipeline = pipeline_fn
        self._dfs = dfs_client
        self._llm = llm_client
        self._store = market_store
        self._kb = knowledge_store

    async def score(self, request: ScoreRequest) -> ScoreResult:
        request_id = str(uuid4())
        handler_start = time.monotonic()
        logger.info(
            "MarketService.score START request_id=%s niche=%r city=%r state=%r dry_run=%s",
            request_id,
            request.niche,
            request.city,
            request.state,
            request.dry_run,
        )

        canonical = resolve_canonical_key(
            niche=request.niche,
            city=request.city,
            state=request.state,
            place_id=request.place_id,
            dataforseo_location_code=request.dataforseo_location_code,
        )
        input_hash = canonical.input_hash(request.strategy_profile)

        # --- Run pipeline ---
        if request.dry_run:
            result = await self._pipeline(
                niche=request.niche,
                city=request.city,
                state=request.state,
                place_id=request.place_id,
                dataforseo_location_code=request.dataforseo_location_code,
                strategy_profile=request.strategy_profile,
                llm_client=None,
                dataforseo_client=None,
                dry_run=True,
                request_id=request_id,
            )
        else:
            result = await self._pipeline(
                niche=request.niche,
                city=request.city,
                state=request.state,
                place_id=request.place_id,
                dataforseo_location_code=request.dataforseo_location_code,
                strategy_profile=request.strategy_profile,
                llm_client=self._llm,
                dataforseo_client=self._dfs,
                request_id=request_id,
            )

        pipeline_ms = int((time.monotonic() - handler_start) * 1000)

        # --- Persist report ---
        report_id: str | None = None
        persist_failed = False
        if not request.dry_run:
            try:
                report_id = self._store.persist_report(result.report)
            except Exception:
                logger.exception(
                    "Report persistence failed for report_id=%s",
                    result.report.get("report_id"),
                )
                report_id = result.report.get("report_id")
                persist_failed = True

        # --- Flush DFS costs ---
        if not request.dry_run and self._dfs is not None and report_id:
            try:
                self._dfs.cost_tracker.flush_to_supabase(report_id)
            except Exception:
                logger.exception(
                    "Failed to flush DFS cost log for report_id=%s", report_id
                )

        # --- KB update ---
        entity_id: str | None = None
        snapshot_id: str | None = None
        if not request.dry_run:
            try:
                entity_id = self._kb.upsert_entity(canonical)
                snapshot_id = self._kb.create_snapshot(
                    entity_id=entity_id,
                    input_hash=input_hash,
                    strategy_profile=request.strategy_profile,
                    report=result.report,
                    report_id=report_id,
                )
                if report_id:
                    self._kb.link_report(
                        report_id=report_id,
                        entity_id=entity_id,
                        snapshot_id=snapshot_id,
                    )
                self._kb.store_evidence(
                    snapshot_id=snapshot_id,
                    artifact_type="score_bundle",
                    payload=result.report.get("metros", []),
                )
                if result.report.get("keyword_expansion"):
                    self._kb.store_evidence(
                        snapshot_id=snapshot_id,
                        artifact_type="keyword_expansion",
                        payload=result.report["keyword_expansion"],
                    )
            except Exception:
                logger.exception(
                    "KB persistence failed for report_id=%s", report_id
                )

        # --- Feedback logging ---
        if not request.dry_run and report_id and not persist_failed:
            try:
                log_feedback(result.report, self._kb)
            except Exception:
                logger.exception(
                    "Feedback logging failed for report_id=%s", report_id
                )

        total_ms = int((time.monotonic() - handler_start) * 1000)
        logger.info(
            "MarketService.score DONE request_id=%s report_id=%s entity_id=%s "
            "snapshot_id=%s opportunity=%s persist_ok=%s pipeline_ms=%d total_ms=%d",
            request_id,
            report_id,
            entity_id,
            snapshot_id,
            result.opportunity_score,
            not persist_failed,
            pipeline_ms,
            total_ms,
        )

        classification_label = (
            "High"
            if result.opportunity_score >= 75
            else "Medium"
            if result.opportunity_score >= 50
            else "Low"
        )

        return ScoreResult(
            report_id=report_id,
            opportunity_score=result.opportunity_score,
            classification_label=classification_label,
            evidence=result.evidence,
            report=result.report,
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            niche=request.niche,
            persist_warning=(
                "Report scored successfully but failed to save to database"
                if persist_failed
                else None
            ),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/domain/services/test_market_service.py -v`
Expected: All 17 tests PASS

- [ ] **Step 5: Run full domain test suite**

Run: `python -m pytest tests/domain/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/market_service.py tests/domain/services/test_market_service.py tests/domain/services/fakes.py
git commit -m "feat(domain): add MarketService extracting scoring orchestration from API handler"
```

---

### Task 5: Refactor the API Handler

**Files:**
- Modify: `src/research_agent/api.py:280-590`

The handler must become a thin wrapper. The response contract must remain identical.

- [ ] **Step 1: Capture current response shape by running the dry-run handler test**

Run: `python -m pytest tests/unit/test_api_niches.py::test_post_niches_score_dry_run_returns_report_and_opportunity -v`
Expected: PASS (baseline — this must still pass after refactoring)

- [ ] **Step 2: Add MarketService startup wiring and thin handler**

In `src/research_agent/api.py`, add imports near the top (around line 31):

```python
from src.clients.supabase_adapter import SupabaseMarketStore
from src.clients.kb_adapter import KBKnowledgeStore
from src.domain.services.market_service import MarketService, ScoreRequest
```

Replace the `_persist_report` helper (lines 280-281) and `_read_report_by_id` helper (lines 284-295) with a MarketService singleton:

```python
# ---------------------------------------------------------------------------
# MarketService singleton (replaces per-request client construction)
# ---------------------------------------------------------------------------

_MARKET_SERVICE: MarketService | None = None


def _build_market_service() -> MarketService:
    dfs = _shared_dfs_client()
    llm: Any = None
    try:
        llm = LLMClient()
    except Exception:
        logger.warning("LLMClient unavailable; only dry-run scoring will work")

    store: Any = None
    kb: Any = None
    try:
        store = SupabaseMarketStore(SupabasePersistence())
    except Exception:
        logger.warning("SupabaseMarketStore unavailable; persistence will fail")
    try:
        kb = KBKnowledgeStore(KBPersistence())
    except Exception:
        logger.warning("KBKnowledgeStore unavailable; KB operations will fail")

    return MarketService(
        pipeline_fn=score_niche_for_metro,
        dfs_client=dfs,
        llm_client=llm,
        market_store=store,
        knowledge_store=kb,
    )


def _market_service() -> MarketService:
    global _MARKET_SERVICE
    if _MARKET_SERVICE is None:
        _MARKET_SERVICE = _build_market_service()
    return _MARKET_SERVICE


def _read_report_by_id(report_id: str) -> dict[str, Any] | None:
    """Read a report by ID. Used by GET /api/niches/{report_id}."""
    svc = _market_service()
    if svc._store is not None:
        return svc._store.read_report(report_id)
    import os
    from supabase import create_client
    client = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    res = client.table("reports").select("*").eq("id", report_id).limit(1).execute()
    return res.data[0] if res.data else None
```

Replace the `niches_score` handler (lines 445-590) with:

```python
@app.post("/api/niches/score")
async def niches_score(req: NicheScoreRequest) -> dict[str, Any]:
    """Run M4-M9 pipeline for a (niche, city, state) pair and persist the report."""
    try:
        score_request = ScoreRequest(
            niche=req.niche,
            city=req.city,
            state=req.state,
            place_id=req.place_id,
            dataforseo_location_code=req.dataforseo_location_code,
            strategy_profile=req.strategy_profile,
            dry_run=req.dry_run,
        )
        result = await _market_service().score(score_request)
        return result.to_api_response()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception(
            "niches_score pipeline failed niche=%r city=%r", req.niche, req.city
        )
        raise HTTPException(
            status_code=500, detail="Scoring pipeline failed unexpectedly"
        )
```

- [ ] **Step 3: Remove unused imports**

After the refactor, these imports from `api.py` are no longer needed directly in the handler:
- `uuid` (moved to MarketService)
- `resolve_canonical_key` (moved to MarketService)
- `log_feedback` (moved to MarketService)

Check with: `ruff check src/research_agent/api.py`

Remove any unused imports flagged by ruff. Keep `score_niche_for_metro` (used by `_build_market_service`), `SupabasePersistence`, `KBPersistence`, `LLMClient`, `DataForSEOClient` (used by wiring).

- [ ] **Step 4: Run the handler tests**

Run: `python -m pytest tests/unit/test_api_niches.py -v`
Expected: Some tests may fail due to changed patching targets. Note which ones fail.

- [ ] **Step 5: Migrate test patches in test_api_niches.py**

The test `test_post_niches_score_dry_run_returns_report_and_opportunity` patches:
- `src.research_agent.api.score_niche_for_metro` → now needs to patch via MarketService injection
- `src.research_agent.api._persist_report` → no longer exists

Update `tests/unit/test_api_niches.py`:

```python
"""Unit tests for the FastAPI /api/niches routes."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

import src.research_agent.api as api_module
from src.research_agent.api import app
from src.domain.services.market_service import MarketService, ScoreRequest, ScoreResult


class _FakeScoreResult:
    def __init__(self) -> None:
        self.report = {
            "report_id": "abc",
            "generated_at": "2026-04-20T00:00:00+00:00",
            "spec_version": "1.1",
            "input": {"niche_keyword": "roofing", "geo_scope": "city",
                      "geo_target": "Phoenix, AZ", "report_depth": "standard",
                      "strategy_profile": "balanced"},
            "keyword_expansion": {"niche": "roofing", "expanded_keywords": []},
            "metros": [{"cbsa_code": "38060", "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                         "population": 5000000,
                         "scores": {"demand": 70, "organic_competition": 40,
                                    "local_competition": 55, "monetization": 65,
                                    "ai_resilience": 80, "opportunity": 72,
                                    "confidence": {"score": 82, "flags": []}},
                         "confidence": {"score": 82, "flags": []},
                         "serp_archetype": "local_first",
                         "ai_exposure": "low", "difficulty_tier": "T2",
                         "signals": {}, "guidance": {}}],
            "meta": {"total_api_calls": 0, "total_cost_usd": 0.0,
                      "processing_time_seconds": 0.1, "feedback_log_id": "fb"},
        }
        self.opportunity_score = 72
        self.evidence = [{"category": "demand", "label": "x", "value": 1.0,
                           "source": "s", "is_available": True}]


def _make_test_market_service(
    pipeline_fn: Any | None = None,
) -> MarketService:
    """Build a MarketService with fakes for handler-level tests."""
    from tests.domain.services.fakes import (
        FakeMarketStore,
        FakeKnowledgeStore,
    )

    async def _default_pipeline(**kwargs: Any) -> _FakeScoreResult:
        return _FakeScoreResult()

    return MarketService(
        pipeline_fn=pipeline_fn or _default_pipeline,
        market_store=FakeMarketStore(),
        knowledge_store=FakeKnowledgeStore(),
    )


def test_post_niches_score_dry_run_returns_report_and_opportunity(monkeypatch: Any) -> None:
    async def _fake_orchestrator(**kwargs: Any) -> _FakeScoreResult:
        assert kwargs["dry_run"] is True
        assert kwargs["place_id"] == "place.123"
        assert kwargs["dataforseo_location_code"] == 12345
        return _FakeScoreResult()

    svc = _make_test_market_service(pipeline_fn=_fake_orchestrator)
    monkeypatch.setattr(api_module, "_MARKET_SERVICE", svc)

    client = TestClient(app)
    res = client.post("/api/niches/score", json={
        "niche": "roofing",
        "city": "Phoenix",
        "state": "AZ",
        "place_id": "place.123",
        "dataforseo_location_code": 12345,
        "dry_run": True,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["report_id"] is None  # dry_run skips persistence
    assert body["opportunity_score"] == 72
    assert body["evidence"][0]["category"] == "demand"


def test_post_niches_score_validation_error_on_empty_city() -> None:
    client = TestClient(app)
    res = client.post("/api/niches/score", json={"niche": "roofing", "city": "", "state": "AZ"})
    assert res.status_code == 400


def test_post_niches_score_validation_error_on_nonpositive_dfs_location_code() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/niches/score",
        json={"niche": "roofing", "city": "Phoenix", "dataforseo_location_code": 0},
    )
    assert res.status_code == 400


def test_get_niches_report_reads_from_supabase(monkeypatch: Any) -> None:
    fake_row = {
        "id": "abc", "niche_keyword": "roofing", "geo_target": "Phoenix, AZ",
        "metros": [{"cbsa_code": "38060", "scores": {"opportunity": 72}}],
        "created_at": "2026-04-20T00:00:00+00:00", "spec_version": "1.1",
        "keyword_expansion": {"keywords": []}, "meta": {}, "report_depth": "standard",
        "strategy_profile": "balanced", "geo_scope": "city",
    }
    with patch("src.research_agent.api._read_report_by_id", return_value=fake_row):
        client = TestClient(app)
        res = client.get("/api/niches/abc")
    assert res.status_code == 200
    body = res.json()
    assert body["report_id"] == "abc"
    assert body["input"]["niche_keyword"] == "roofing"
```

- [ ] **Step 6: Run all handler tests**

Run: `python -m pytest tests/unit/test_api_niches.py -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/research_agent/api.py tests/unit/test_api_niches.py
git commit -m "refactor(api): thin niches_score handler delegates to MarketService"
```

---

### Task 6: Update Exports and Documentation

**Files:**
- Modify: `src/domain/services/__init__.py`
- Modify: `docs/product_breakdown.md`

- [ ] **Step 1: Update domain services exports**

Replace `src/domain/services/__init__.py` with:

```python
from src.domain.services.geo_resolver import GeoResolutionError, GeoResolver, ResolvedTarget
from src.domain.services.market_service import MarketService, ScoreRequest, ScoreResult

__all__ = [
    "GeoResolver",
    "GeoResolutionError",
    "ResolvedTarget",
    "MarketService",
    "ScoreRequest",
    "ScoreResult",
]
```

- [ ] **Step 2: Update product_breakdown.md**

In `docs/product_breakdown.md`, find the section describing the API handler / pipeline orchestration and add:

```markdown
### MarketService (Phase 3)

**File:** `src/domain/services/market_service.py`

**Purpose:** Extracted business logic from the `niches_score` API handler. Coordinates the full scoring flow:
1. Canonical key resolution (KB identity)
2. Pipeline execution (via injected `score_niche_for_metro`)
3. Report persistence (via `MarketStore` adapter)
4. KB entity/snapshot/evidence updates (via `KnowledgeStore` adapter)
5. DFS cost log flushing
6. Feedback logging

**Input:** `ScoreRequest(niche, city, state?, place_id?, dataforseo_location_code?, strategy_profile, dry_run)`
**Output:** `ScoreResult(report_id, opportunity_score, classification_label, evidence, report, entity_id, snapshot_id, persist_warning?)`

**Adapters:**
- `src/clients/supabase_adapter.py` — `SupabaseMarketStore` implements `MarketStore`
- `src/clients/kb_adapter.py` — `KBKnowledgeStore` implements `KnowledgeStore`
```

- [ ] **Step 3: Commit**

```bash
git add src/domain/services/__init__.py docs/product_breakdown.md
git commit -m "docs: update exports and product_breakdown for Phase 3 MarketService"
```

---

### Task 7: Full Validation

- [ ] **Step 1: Run all domain unit tests**

Run: `python -m pytest tests/domain/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run all client adapter tests**

Run: `python -m pytest tests/clients/ -v`
Expected: All tests PASS

- [ ] **Step 3: Run all API handler tests**

Run: `python -m pytest tests/unit/test_api_niches.py -v`
Expected: All 4 tests PASS

- [ ] **Step 4: Run the full unit test suite**

Run: `python -m pytest tests/unit/ -v`
Expected: All tests PASS, zero regressions

- [ ] **Step 5: Verify domain layer purity**

```bash
grep -r "from src.clients" src/domain/ && echo "FAIL: domain imports clients" || echo "PASS"
grep -r "import os" src/domain/services/ && echo "FAIL: env vars in domain" || echo "PASS"
```

Expected: Both print PASS

- [ ] **Step 6: Lint check**

Run: `ruff check src/ tests/`
Expected: Zero errors

- [ ] **Step 7: Verify handler is thin**

```bash
grep -c "^" src/research_agent/api.py
```

Expected: File should be shorter than before. The `niches_score` handler body should be ~15 lines.

- [ ] **Step 8: Verify response contract unchanged**

The `test_post_niches_score_dry_run_returns_report_and_opportunity` test validates the response shape. Additionally, manually confirm that `ScoreResult.to_api_response()` produces exactly these keys:
- `report_id`, `opportunity_score`, `classification_label`, `evidence`, `report`, `entity_id`, `snapshot_id`
- Plus optional `persist_warning` when persistence fails

This matches the handler's current response at `api.py:568-582`.
