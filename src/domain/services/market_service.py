"""MarketService — single-market scoring orchestration.

Extracted from the niches_score handler in api.py.
Coordinates: canonical key → pipeline execution → persistence → KB update → feedback.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from copy import deepcopy
from typing import Any, Awaitable, Callable
from uuid import uuid4

from src.domain.ports import CityDataProvider
from src.pipeline.canonical_key import resolve_canonical_key
from src.pipeline.feedback_logger import log_feedback
from src.scoring.benchmark_repository import SeoBenchmarkRepository

logger = logging.getLogger(__name__)
_PRIVATE_ARTIFACT_KEYS = {"seo_evidence_artifacts", "raw_evidence_artifacts"}


@dataclass
class ScoreRequest:
    """Input for scoring a single market. Maps from API request params."""

    niche: str
    city: str
    state: str | None = None
    place_id: str | None = None
    dataforseo_location_code: int | None = None
    cbsa_code: str | None = None
    cbsa_name: str | None = None
    population: int | None = None
    metadata_source: str = "typed"
    request_id: str | None = None
    strategy_profile: str = "balanced"
    dry_run: bool = False
    owner_account_id: str | None = None
    created_by_user_id: str | None = None


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
        benchmark_repository: SeoBenchmarkRepository | None = None,
        city_data_provider: CityDataProvider | None = None,
    ) -> None:
        self._pipeline = pipeline_fn
        self._dfs = dfs_client
        self._llm = llm_client
        self._store = market_store
        self._kb = knowledge_store
        self._benchmark_repository = benchmark_repository
        self._city_data_provider = city_data_provider

    async def score(self, request: ScoreRequest) -> ScoreResult:
        request_id = request.request_id or str(uuid4())
        handler_start = time.monotonic()
        logger.info(
            "MarketService.score START request_id=%s niche=%r city=%r state=%r metadata_source=%s dry_run=%s",
            request_id,
            request.niche,
            request.city,
            request.state,
            request.metadata_source,
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
                cbsa_code=request.cbsa_code,
                cbsa_name=request.cbsa_name,
                population=request.population,
                strategy_profile=request.strategy_profile,
                llm_client=None,
                dataforseo_client=None,
                dry_run=True,
                request_id=request_id,
                benchmark_repository=None,
                city_data_provider=None,
            )
        else:
            result = await self._pipeline(
                niche=request.niche,
                city=request.city,
                state=request.state,
                place_id=request.place_id,
                dataforseo_location_code=request.dataforseo_location_code,
                cbsa_code=request.cbsa_code,
                cbsa_name=request.cbsa_name,
                population=request.population,
                strategy_profile=request.strategy_profile,
                llm_client=self._llm,
                dataforseo_client=self._dfs,
                request_id=request_id,
                benchmark_repository=self._benchmark_repository,
                city_data_provider=self._city_data_provider,
            )

        pipeline_ms = int((time.monotonic() - handler_start) * 1000)

        if request.owner_account_id and request.created_by_user_id:
            result.report["owner_account_id"] = request.owner_account_id
            result.report["created_by_user_id"] = request.created_by_user_id
            result.report["access_scope"] = "account"
        _scrub_private_artifacts(result.report)

        # --- Persist report ---
        report_id: str | None = None
        persist_failed = False
        if not request.dry_run:
            try:
                persistence_report = deepcopy(result.report)
                if getattr(result, "seo_evidence_artifacts", None):
                    persistence_report["seo_evidence_artifacts"] = (
                        result.seo_evidence_artifacts
                    )
                report_id = self._store.persist_report(persistence_report)
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
            "snapshot_id=%s metadata_source=%s opportunity=%s persist_ok=%s pipeline_ms=%d total_ms=%d",
            request_id,
            report_id,
            entity_id,
            snapshot_id,
            request.metadata_source,
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


def _scrub_private_artifacts(value: Any) -> None:
    if isinstance(value, dict):
        for key in _PRIVATE_ARTIFACT_KEYS:
            value.pop(key, None)
        for item in value.values():
            _scrub_private_artifacts(item)
    elif isinstance(value, list):
        for item in value:
            _scrub_private_artifacts(item)
