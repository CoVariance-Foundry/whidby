"""Persist M9 reports to the Supabase schema defined in 001_core_schema.sql."""
from __future__ import annotations

import logging
import os
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any: ...


def build_report_row(report: dict[str, Any]) -> dict[str, Any]:
    run_input = report["input"]
    return {
        "id": report["report_id"],
        "created_at": report["generated_at"],
        "spec_version": report["spec_version"],
        "niche_keyword": run_input["niche_keyword"],
        "geo_scope": run_input["geo_scope"],
        "geo_target": run_input["geo_target"],
        "report_depth": run_input.get("report_depth", "standard"),
        "strategy_profile": run_input.get("strategy_profile", "balanced"),
        "resolved_weights": (
            report["metros"][0]["scores"].get("resolved_weights") if report["metros"] else None
        ),
        "keyword_expansion": report["keyword_expansion"],
        "metros": report["metros"],
        "meta": report["meta"],
        "feedback_log_id": report["meta"].get("feedback_log_id"),
    }


def build_keyword_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    keywords = report["keyword_expansion"].get("expanded_keywords", [])
    rows: list[dict[str, Any]] = []
    for kw in keywords:
        rows.append(
            {
                "report_id": report_id,
                "keyword": kw["keyword"],
                "tier": int(kw.get("tier", 3)),
                "intent": kw.get("intent", "informational"),
                "source": kw.get("source", "llm"),
                "aio_risk": kw.get("aio_risk", "low"),
                "search_volume": kw.get("search_volume"),
                "cpc": kw.get("cpc"),
            }
        )
    return rows


def build_metro_signal_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    for metro in report["metros"]:
        signals = metro.get("signals") or {}
        rows.append(
            {
                "report_id": report_id,
                "cbsa_code": metro["cbsa_code"],
                "cbsa_name": metro["cbsa_name"],
                "demand": signals.get("demand"),
                "organic_competition": signals.get("organic_competition"),
                "local_competition": signals.get("local_competition"),
                "ai_resilience": signals.get("ai_resilience"),
                "monetization": signals.get("monetization"),
            }
        )
    return rows


def build_metro_score_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build metro_scores rows matching 001_core_schema.sql:55-71.

    Schema columns (adjusted from plan draft):
      - confidence_score INT  (plan used 'confidence' float — converted to int 0-100)
      - confidence_flags JSONB  (plan omitted — populated from scores if present)
      - guidance JSONB  (plan omitted — populated from metro.guidance)
    """
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    for metro in report["metros"]:
        scores = metro["scores"]
        raw_confidence = scores.get("confidence", {})
        if isinstance(raw_confidence, dict):
            confidence_score = int(round(float(raw_confidence.get("score", 0))))
            confidence_flags = raw_confidence.get("flags")
        else:
            confidence_score = int(round(float(raw_confidence) * 100))
            confidence_flags = scores.get("confidence_flags")
        rows.append(
            {
                "report_id": report_id,
                "cbsa_code": metro["cbsa_code"],
                "demand_score": int(round(scores["demand"])),
                "organic_competition_score": int(round(scores["organic_competition"])),
                "local_competition_score": int(round(scores["local_competition"])),
                "monetization_score": int(round(scores["monetization"])),
                "ai_resilience_score": int(round(scores["ai_resilience"])),
                "opportunity_score": int(round(scores["opportunity"])),
                "confidence_score": confidence_score,
                "confidence_flags": confidence_flags,
                "serp_archetype": metro["serp_archetype"],
                "ai_exposure": metro["ai_exposure"],
                "difficulty_tier": metro["difficulty_tier"],
                "guidance": metro.get("guidance"),
            }
        )
    return rows


class SupabasePersistence:
    """Writes an M9 report and its normalized children to Supabase."""

    def __init__(self, *, client: _SupabaseLike | None = None) -> None:
        if client is None:
            from supabase import create_client

            url = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
            key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
            client = create_client(url, key)
        self._client = client

    def persist_report(self, report: dict[str, Any]) -> str:
        report_id = report["report_id"]
        logger.info("persist_report START report_id=%s", report_id)

        self._client.table("reports").insert(build_report_row(report)).execute()
        logger.info("persist_report inserted reports row for %s", report_id)

        keyword_rows = build_keyword_rows(report)
        if keyword_rows:
            self._client.table("report_keywords").insert(keyword_rows).execute()
            logger.info("persist_report inserted %d report_keywords rows", len(keyword_rows))

        signal_rows = build_metro_signal_rows(report)
        if signal_rows:
            self._client.table("metro_signals").insert(signal_rows).execute()
            logger.info("persist_report inserted %d metro_signals rows", len(signal_rows))

        score_rows = build_metro_score_rows(report)
        if score_rows:
            self._client.table("metro_scores").insert(score_rows).execute()
            logger.info("persist_report inserted %d metro_scores rows", len(score_rows))

        logger.info("persist_report DONE report_id=%s", report_id)
        return report_id
