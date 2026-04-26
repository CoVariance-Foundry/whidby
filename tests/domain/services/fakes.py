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
