from __future__ import annotations

from typing import Any

from src.domain.competitor_intel import CompetitorIntelService


class FakeCompetitorIntelRepository:
    def __init__(self) -> None:
        self.metro: dict[str, Any] | None = {
            "cbsa_code": "13820",
            "cbsa_name": "Boise City, ID",
            "state": "ID",
        }
        self.score_context: dict[str, Any] | None = None
        self.keyword_facts: list[dict[str, Any]] = []
        self.organic_facts: list[dict[str, Any]] = []
        self.local_pack_facts: list[dict[str, Any]] = []
        self.report_context: dict[str, Any] | None = None
        self.run_records: list[dict[str, Any]] = []

    def find_metro(self, *, city: str | None, state: str | None) -> dict[str, Any] | None:
        return self.metro

    def fetch_score_context(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        report_id: str | None,
        account_id: str | None,
    ) -> dict[str, Any] | None:
        return self.score_context

    def fetch_keyword_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str | None,
        account_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.keyword_facts[:limit]

    def fetch_organic_competitor_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str | None,
        account_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.organic_facts[:limit]

    def fetch_local_pack_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str | None,
        account_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.local_pack_facts[:limit]

    def fetch_report_context(
        self,
        *,
        report_id: str,
        account_id: str | None,
    ) -> dict[str, Any] | None:
        return self.report_context

    def create_run_record(self, payload: dict[str, Any]) -> str:
        self.run_records.append(payload)
        return "55555555-5555-5555-5555-555555555555"


def test_competitor_intel_returns_not_found_without_runnable_target() -> None:
    service = CompetitorIntelService(FakeCompetitorIntelRepository())

    result = service.get_read_model({})

    assert result["status"] == "not_found"
    assert result["target"]["niche_normalized"] is None


def test_competitor_intel_returns_ready_to_run_without_durable_facts() -> None:
    service = CompetitorIntelService(FakeCompetitorIntelRepository())

    result = service.get_read_model({"city": "Boise", "state": "ID", "service": "Roof Repair"})

    assert result["status"] == "ready_to_run"
    assert result["target"]["cbsa_code"] == "13820"
    assert result["target"]["niche_normalized"] == "roof repair"


def test_competitor_intel_resolves_report_id_only_target() -> None:
    repo = FakeCompetitorIntelRepository()
    repo.report_context = {
        "id": "report-1",
        "niche_keyword": "roofing",
        "geo_target": "Boise, ID",
        "access_scope": "account",
        "owner_account_id": "33333333-3333-3333-3333-333333333333",
        "metros": [
            {
                "cbsa_code": "13820",
                "cbsa_name": "Boise City, ID",
                "state": "ID",
            }
        ],
    }
    repo.organic_facts = [{"result_rank": 1, "domain": "roof.example"}]
    service = CompetitorIntelService(repo)

    result = service.get_read_model(
        {
            "report_id": "report-1",
            "account_id": "33333333-3333-3333-3333-333333333333",
        }
    )

    assert result["status"] == "dossier"
    assert result["target"]["city"] == "Boise"
    assert result["target"]["service"] == "roofing"
    assert result["target"]["cbsa_code"] == "13820"


def test_report_context_without_durable_facts_stays_ready_to_run() -> None:
    repo = FakeCompetitorIntelRepository()
    repo.report_context = {
        "id": "report-1",
        "niche_keyword": "roofing",
        "geo_target": "Boise, ID",
        "access_scope": "account",
        "owner_account_id": "33333333-3333-3333-3333-333333333333",
        "metros": [
            {
                "cbsa_code": "13820",
                "cbsa_name": "Boise City, ID",
                "state": "ID",
            }
        ],
    }
    service = CompetitorIntelService(repo)

    result = service.get_read_model(
        {
            "report_id": "report-1",
            "account_id": "33333333-3333-3333-3333-333333333333",
        }
    )

    assert result["status"] == "ready_to_run"
    assert result["target"]["city"] == "Boise"


def test_competitor_intel_returns_aggregate_only_from_score_and_keyword_facts() -> None:
    repo = FakeCompetitorIntelRepository()
    repo.score_context = {
        "report_id": "report-1",
        "demand_strength": 141,
        "organic_difficulty": 28,
        "local_difficulty": 35,
        "benchmark_confidence": "high",
    }
    repo.keyword_facts = [
        {
            "keyword": "boise roofing",
            "search_volume_monthly": 720,
            "avg_top5_da": 24.5,
            "top5_organic_data_confidence": "medium",
            "snapshot_date": "2026-05-22",
        }
    ]
    service = CompetitorIntelService(repo)

    result = service.get_read_model({"city": "Boise", "state": "ID", "service": "roofing"})

    assert result["status"] == "aggregate_only"
    assert result["summary"]["organic_difficulty"] == 28.0
    assert result["summary"]["avg_top5_da"] == 24.5
    assert result["facts"]["keyword_fact_count"] == 1
    assert result["organic_competitors"] == []
    assert result["aggregate"]["coverage"][0]["status"] == "partial"


def test_competitor_intel_returns_dossier_from_local_pack_facts() -> None:
    repo = FakeCompetitorIntelRepository()
    repo.local_pack_facts = [
        {
            "listing_rank": 1,
            "business_name": "Boise Roof Pros",
            "review_count": 42,
            "rating": 4.7,
            "categories": ["Roofing contractor"],
            "source": "dataforseo",
            "snapshot_date": "2026-05-22",
        }
    ]
    service = CompetitorIntelService(repo)

    result = service.get_read_model({"city": "Boise", "state": "ID", "service": "roofing"})

    assert result["status"] == "dossier"
    assert result["local_pack_competitors"] == [
        {
            "rank": 1,
            "name": "Boise Roof Pros",
            "exact_match_name": False,
            "review_count": 42,
            "review_velocity_monthly": None,
            "rating": 4.7,
            "gbp_completeness": None,
            "photo_count": None,
            "has_recent_post": None,
            "categories": ["Roofing contractor"],
            "source": "dataforseo",
            "snapshot_date": "2026-05-22",
        }
    ]
    assert result["dossier"]["local_pack_competitors"][0]["name"] == "Boise Roof Pros"


def test_competitor_intel_returns_dossier_from_organic_competitor_facts() -> None:
    repo = FakeCompetitorIntelRepository()
    repo.organic_facts = [
        {
            "result_rank": 1,
            "domain": "boiseroofpros.com",
            "title": "Boise Roof Pros",
            "url": "https://boiseroofpros.com/",
            "domain_authority": 23,
            "backlinks_count": 120,
            "referring_domains_count": 18,
            "lighthouse_score": 67,
            "has_localbusiness_schema": False,
            "schema_types": [],
            "title_keyword_match": True,
            "is_aggregator": False,
            "source": "dataforseo",
            "snapshot_date": "2026-05-22",
        }
    ]
    service = CompetitorIntelService(repo)

    result = service.get_read_model({"city": "Boise", "state": "ID", "service": "roofing"})

    assert result["status"] == "dossier"
    assert result["organic_competitors"][0]["domain"] == "boiseroofpros.com"
    assert result["organic_competitors"][0]["backlink_count"] == 120.0
    assert result["dossier"]["coverage"][0]["status"] == "available"


def test_competitor_intel_run_shape_uses_deterministic_read_model() -> None:
    repo = FakeCompetitorIntelRepository()
    repo.keyword_facts = [{"search_volume_monthly": 100, "snapshot_date": "2026-05-22"}]
    service = CompetitorIntelService(repo)

    result = service.create_run(
        {"city": "Boise", "state": "ID", "service": "roofing", "quota_consumed": 2}
    )

    assert result["status"] == "succeeded"
    assert result["state"] == "aggregate_only"
    assert result["quota_consumed"] == 2
    assert result["result"]["status"] == "aggregate_only"
    assert result["run_id"] == "55555555-5555-5555-5555-555555555555"
    assert repo.run_records[0]["quota_consumed"] == 2
    assert repo.run_records[0]["status"] == "succeeded"


def test_competitor_intel_run_queues_without_durable_result() -> None:
    repo = FakeCompetitorIntelRepository()
    service = CompetitorIntelService(repo)

    result = service.create_run(
        {"city": "Boise", "state": "ID", "service": "roofing", "quota_consumed": 2}
    )

    assert result["status"] == "queued"
    assert result["state"] == "ready_to_run"
    assert result["result"] is None
    assert repo.run_records[0]["status"] == "queued"


def test_report_context_only_run_queues_without_durable_result() -> None:
    repo = FakeCompetitorIntelRepository()
    repo.report_context = {
        "id": "report-1",
        "niche_keyword": "roofing",
        "geo_target": "Boise, ID",
        "access_scope": "account",
        "owner_account_id": "33333333-3333-3333-3333-333333333333",
        "metros": [
            {
                "cbsa_code": "13820",
                "cbsa_name": "Boise City, ID",
                "state": "ID",
            }
        ],
    }
    service = CompetitorIntelService(repo)

    result = service.create_run(
        {
            "report_id": "report-1",
            "account_id": "33333333-3333-3333-3333-333333333333",
            "quota_consumed": 2,
        }
    )

    assert result["status"] == "queued"
    assert result["state"] == "ready_to_run"
    assert result["result"] is None
    assert repo.run_records[0]["report_id"] == "report-1"
