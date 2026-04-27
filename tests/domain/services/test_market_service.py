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
