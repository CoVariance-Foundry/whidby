"""Persist M9 reports to the Supabase schema defined in 001_core_schema.sql."""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Protocol

from src.domain.services.explore_refresh_service import RefreshTarget

logger = logging.getLogger(__name__)


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any: ...


_EXPLORE_TARGET_SELECT = (
    "id,policy_id,niche_keyword,niche_normalized,cbsa_code,cbsa_name,state,"
    "latest_report_id,latest_scored_at,next_refresh_at,active,priority,created_at,updated_at"
)


def _raise_on_error(result: Any) -> None:
    error = getattr(result, "error", None)
    if error:
        message = getattr(error, "message", None) or str(error)
        raise RuntimeError(f"Supabase request failed: {message}")


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _iso_dt(value: datetime) -> str:
    return value.isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result_data(result: Any) -> Any:
    _raise_on_error(result)
    return getattr(result, "data", None)


def _result_rows(result: Any) -> list[dict[str, Any]]:
    data = _result_data(result)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise RuntimeError(f"Unexpected Supabase response data: {data!r}")


def _score_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("score")
    if value is None:
        return None
    numeric = float(value)
    if 0 <= numeric <= 1:
        numeric *= 100
    return int(round(numeric))


def _target_from_row(row: dict[str, Any]) -> RefreshTarget:
    latest_opportunity_score = row.get("latest_opportunity_score")
    return RefreshTarget(
        id=str(row["id"]),
        policy_id=str(row["policy_id"]),
        niche_keyword=str(row["niche_keyword"]),
        niche_normalized=str(row["niche_normalized"]),
        cbsa_code=str(row["cbsa_code"]),
        cbsa_name=str(row["cbsa_name"]),
        state=row.get("state"),
        latest_report_id=row.get("latest_report_id"),
        latest_scored_at=_parse_dt(row.get("latest_scored_at")),
        next_refresh_at=_parse_dt(row.get("next_refresh_at")),
        latest_opportunity_score=(
            int(latest_opportunity_score) if latest_opportunity_score is not None else None
        ),
    )


def _non_empty_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item not in (None, "")]
    return [value] if value != "" else []


def _matching_metro(report: dict[str, Any], cbsa_code: str) -> dict[str, Any] | None:
    for metro in report.get("metros", []):
        if str(metro.get("cbsa_code")) == str(cbsa_code):
            return metro
    return None


def _expanded_keywords(report: dict[str, Any]) -> list[dict[str, Any]]:
    keyword_expansion = report.get("keyword_expansion") or {}
    keywords = keyword_expansion.get("expanded_keywords", [])
    return keywords if isinstance(keywords, list) else []


def _flatten_signal_buckets(signals: dict[str, Any]) -> dict[str, Any]:
    flattened = dict(signals)
    for key in (
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
    ):
        value = signals.get(key)
        if isinstance(value, dict):
            flattened.update(value)
    return flattened


def _niche_normalized(report: dict[str, Any], metro: dict[str, Any] | None = None) -> str:
    v2_scores = (metro or {}).get("v2_scores") or {}
    v2_niche = v2_scores.get("niche_normalized")
    if isinstance(v2_niche, str) and v2_niche.strip():
        return v2_niche.strip().lower()
    return str(report.get("input", {}).get("niche_keyword", "")).strip().lower()


def _snapshot_date(report: dict[str, Any]) -> str | None:
    try:
        parsed = _parse_dt(report.get("generated_at"))
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date().isoformat()


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _keyword_tier(value: Any) -> int:
    try:
        tier = int(value)
    except (TypeError, ValueError):
        return 3
    return tier if tier in {1, 2, 3} else 3


def _keyword_intent(value: Any) -> str:
    if isinstance(value, str):
        intent = value.strip().lower()
        if intent in {"transactional", "commercial", "informational"}:
            return intent
    return "informational"


def _score_value(v2_scores: dict[str, Any], dimension: str) -> Any:
    dimension_score = (v2_scores.get("scores") or {}).get(dimension) or {}
    if isinstance(dimension_score, dict):
        return dimension_score.get("value")
    return None


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
        "owner_account_id": report.get("owner_account_id"),
        "created_by_user_id": report.get("created_by_user_id"),
        "access_scope": report.get(
            "access_scope",
            "account" if report.get("owner_account_id") else "cached",
        ),
    }


def build_keyword_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    keywords = _expanded_keywords(report)
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


def build_metro_score_v2_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build rows for public.metro_score_v2 from attached V2 score vectors."""
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    dimensions = (
        "demand_strength",
        "organic_difficulty",
        "local_difficulty",
        "monetization_signal",
        "ai_resilience",
    )
    for metro in report.get("metros", []):
        v2_scores = metro.get("v2_scores")
        if not isinstance(v2_scores, dict):
            continue

        row: dict[str, Any] = {
            "report_id": report_id,
            "niche_normalized": _niche_normalized(report, metro),
            "cbsa_code": v2_scores.get("cbsa_code") or metro.get("cbsa_code"),
            "serp_archetype": metro.get("serp_archetype"),
            "ai_exposure": metro.get("ai_exposure"),
            "spec_version": v2_scores.get("spec_version", "2.0"),
        }

        score_map = v2_scores.get("scores") or {}
        for dimension in dimensions:
            row[dimension] = _score_value(v2_scores, dimension)
            dimension_score = score_map.get(dimension) or {}
            if (
                isinstance(dimension_score, dict)
                and "higher_is_better" in dimension_score
            ):
                row[f"{dimension}_higher_is_better"] = bool(
                    dimension_score["higher_is_better"]
                )

        benchmark = v2_scores.get("benchmark") or {}
        if isinstance(benchmark, dict):
            row["benchmark_population_class"] = benchmark.get("population_class")
            row["benchmark_confidence"] = benchmark.get("confidence_label")
            row["benchmark_sample_size"] = benchmark.get("sample_size")

        flags = v2_scores.get("flags") or {}
        if isinstance(flags, dict):
            row["no_local_pack_detected"] = bool(
                flags.get("no_local_pack_detected", False)
            )
            row["benchmark_undersampled"] = bool(
                flags.get("benchmark_undersampled", False)
            )
            row["cbp_data_missing"] = bool(flags.get("cbp_data_missing", False))

        rows.append(row)
    return rows


def build_seo_fact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build denormalized keyword-level facts for public.seo_facts."""
    report_id = report["report_id"]
    niche_keyword = report.get("input", {}).get("niche_keyword")
    snapshot_date = _snapshot_date(report)
    rows: list[dict[str, Any]] = []

    for metro in report.get("metros", []):
        if not isinstance(metro.get("v2_scores"), dict):
            continue
        signals = _flatten_signal_buckets(metro.get("signals") or {})
        niche_normalized = _niche_normalized(report, metro)
        for keyword in _expanded_keywords(report):
            row = {
                "niche_keyword": niche_keyword,
                "niche_normalized": niche_normalized,
                "cbsa_code": metro.get("cbsa_code"),
                "keyword": keyword["keyword"],
                "keyword_tier": _keyword_tier(keyword.get("tier")),
                "intent": _keyword_intent(keyword.get("intent")),
                "search_volume_monthly": keyword.get("search_volume"),
                "cpc_usd": keyword.get("cpc"),
                "aio_present": signals.get("aio_present"),
                "local_pack_present": signals.get("local_pack_present"),
                "local_pack_position": signals.get("local_pack_position"),
                "aggregator_count_top10": _int_or_none(
                    signals.get("aggregator_count_top10", signals.get("aggregator_count"))
                ),
                "local_biz_count_top10": _int_or_none(
                    signals.get("local_biz_count_top10", signals.get("local_biz_count"))
                ),
                "featured_snippet_present": signals.get("featured_snippet_present"),
                "paa_count": signals.get("paa_count"),
                "ads_present": signals.get("ads_present", signals.get("ads_top_present")),
                "lsa_present": signals.get("lsa_present"),
                "top3_review_count_min": _int_or_none(
                    signals.get("top3_review_count_min")
                ),
                "top3_review_count_avg": _int_or_none(
                    signals.get(
                        "top3_review_count_avg",
                        signals.get("local_pack_review_count_avg"),
                    )
                ),
                "top3_review_velocity_avg": signals.get("top3_review_velocity_avg"),
                "top3_rating_avg": signals.get("top3_rating_avg"),
                "avg_top5_da": _float_or_none(signals.get("avg_top5_da")),
                "avg_top5_lighthouse": _float_or_none(
                    signals.get("avg_top5_lighthouse")
                ),
                "top5_da_coverage": _float_or_none(signals.get("top5_da_coverage")),
                "top5_lighthouse_coverage": _float_or_none(
                    signals.get("top5_lighthouse_coverage")
                ),
                "top5_organic_data_confidence": signals.get(
                    "top5_organic_data_confidence"
                ),
                "report_id": report_id,
                "source": "orchestrator",
            }
            if snapshot_date is not None:
                row["snapshot_date"] = snapshot_date
            rows.append(row)

    return rows


class SupabaseExploreRefreshStore:
    """Supabase-backed persistence for Explore refresh orchestration."""

    def __init__(self, *, client: _SupabaseLike) -> None:
        self._client = client

    def _targets_from_rows(self, rows: list[dict[str, Any]]) -> list[RefreshTarget]:
        if not rows:
            return []

        scores_by_target = self._latest_opportunity_scores(
            [str(row["id"]) for row in rows]
        )
        enriched_rows: list[dict[str, Any]] = []
        for row in rows:
            target_id = str(row["id"])
            row_with_score = dict(row)
            if target_id in scores_by_target:
                row_with_score["latest_opportunity_score"] = scores_by_target[target_id]
            enriched_rows.append(row_with_score)
        return [_target_from_row(row) for row in enriched_rows]

    def _latest_opportunity_scores(self, target_ids: Sequence[str]) -> dict[str, int | None]:
        if not target_ids:
            return {}

        result = (
            self._client.table("explore_latest_target_scores")
            .select("target_id,opportunity_score")
            .in_("target_id", list(target_ids))
            .execute()
        )
        rows = _result_rows(result)
        return {
            str(row["target_id"]): (
                int(row["opportunity_score"])
                if row.get("opportunity_score") is not None
                else None
            )
            for row in rows
        }

    def list_due_targets(self, now: datetime, limit: int) -> list[RefreshTarget]:
        if limit <= 0:
            return []
        result = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .eq("active", True)
            .lte("next_refresh_at", _iso_dt(now))
            .order("priority", desc=False)
            .limit(limit)
            .execute()
        )
        return self._targets_from_rows(_result_rows(result))

    def create_run(self, payload: dict[str, Any]) -> str:
        result = self._client.table("explore_refresh_runs").insert(payload).execute()
        rows = _result_rows(result)
        if not rows or not rows[0].get("id"):
            raise RuntimeError("Supabase create_run returned no run id")
        return str(rows[0]["id"])

    def create_run_items(
        self,
        run_id: str,
        targets: Sequence[RefreshTarget],
    ) -> None:
        rows = [
            {
                "run_id": run_id,
                "target_id": target.id,
                "old_report_id": target.latest_report_id,
                "status": "queued",
            }
            for target in targets
        ]
        if not rows:
            return
        result = self._client.table("explore_refresh_run_items").insert(rows).execute()
        _raise_on_error(result)

    def mark_run_running(self, run_id: str) -> None:
        result = (
            self._client.table("explore_refresh_runs")
            .update(
                {
                    "status": "running",
                    "started_at": _now_iso(),
                }
            )
            .eq("id", run_id)
            .execute()
        )
        _raise_on_error(result)

    def mark_item_succeeded(self, payload: dict[str, Any]) -> None:
        result = (
            self._client.table("explore_refresh_run_items")
            .update(
                {
                    "status": "succeeded",
                    "old_report_id": payload.get("old_report_id"),
                    "new_report_id": payload.get("new_report_id"),
                    "opportunity_before": payload.get("opportunity_before"),
                    "opportunity_after": payload.get("opportunity_after"),
                    "score_delta": payload.get("score_delta"),
                    "completed_at": _now_iso(),
                }
            )
            .eq("run_id", payload["run_id"])
            .eq("target_id", payload["target_id"])
            .execute()
        )
        _raise_on_error(result)

    def mark_item_failed(self, payload: dict[str, Any]) -> None:
        result = (
            self._client.table("explore_refresh_run_items")
            .update(
                {
                    "status": "failed",
                    "old_report_id": payload.get("old_report_id"),
                    "error_message": payload.get("error_message"),
                    "completed_at": _now_iso(),
                }
            )
            .eq("run_id", payload["run_id"])
            .eq("target_id", payload["target_id"])
            .execute()
        )
        _raise_on_error(result)

    def mark_run_complete(
        self,
        run_id: str,
        success_count: int,
        failure_count: int,
    ) -> None:
        if failure_count == 0:
            status = "succeeded"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial_failed"

        result = (
            self._client.table("explore_refresh_runs")
            .update(
                {
                    "status": status,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "completed_at": _now_iso(),
                }
            )
            .eq("id", run_id)
            .execute()
        )
        _raise_on_error(result)

    def upsert_target_after_success(
        self,
        *,
        target_id: str,
        policy_id: str,
        niche_keyword: str,
        niche_normalized: str,
        cbsa_code: str,
        cbsa_name: str,
        state: str | None,
        latest_report_id: str,
        latest_scored_at: datetime,
        next_refresh_at: datetime,
        latest_opportunity_score: int,
        opportunity_before: int | None,
        opportunity_after: int,
        score_delta: int | None,
        strategy_profile: str,
    ) -> None:
        result = (
            self._client.table("explore_refresh_targets")
            .update(
                {
                    "policy_id": policy_id,
                    "niche_keyword": niche_keyword,
                    "niche_normalized": niche_normalized,
                    "cbsa_code": cbsa_code,
                    "cbsa_name": cbsa_name,
                    "state": state,
                    "latest_report_id": latest_report_id,
                    "latest_scored_at": _iso_dt(latest_scored_at),
                    "next_refresh_at": _iso_dt(next_refresh_at),
                    "updated_at": _now_iso(),
                }
            )
            .eq("id", target_id)
            .execute()
        )
        _raise_on_error(result)

    def record_snapshot_from_report(
        self,
        *,
        run_id: str,
        target_id: str,
        report_id: str,
        report: dict[str, Any],
        niche_keyword: str,
        niche_normalized: str,
        cbsa_code: str,
        cbsa_name: str,
        state: str | None,
        strategy_profile: str,
        scored_at: datetime,
        opportunity_before: int | None,
        opportunity_after: int,
        score_delta: int | None,
    ) -> None:
        metro = _matching_metro(report, cbsa_code)
        scores = metro.get("scores", {}) if metro else {}
        meta = {
            "opportunity_before": opportunity_before,
            "opportunity_after": opportunity_after,
            "score_delta": score_delta,
            "source_report_id": report.get("report_id", report_id),
            "matched_metro": metro is not None,
        }
        if isinstance(report.get("meta"), dict):
            meta["report_meta"] = report["meta"]

        opportunity_score = _score_int(scores.get("opportunity"))
        if opportunity_score is None:
            opportunity_score = opportunity_after

        result = (
            self._client.table("explore_report_snapshots")
            .insert(
                {
                    "report_id": report_id,
                    "run_id": run_id,
                    "target_id": target_id,
                    "niche_keyword": niche_keyword,
                    "niche_normalized": niche_normalized,
                    "cbsa_code": cbsa_code,
                    "cbsa_name": cbsa_name,
                    "state": state,
                    "strategy_profile": strategy_profile,
                    "scored_at": _iso_dt(scored_at),
                    "opportunity_score": opportunity_score,
                    "demand_score": _score_int(scores.get("demand")),
                    "organic_competition_score": _score_int(
                        scores.get("organic_competition")
                    ),
                    "local_competition_score": _score_int(scores.get("local_competition")),
                    "monetization_score": _score_int(scores.get("monetization")),
                    "ai_resilience_score": _score_int(scores.get("ai_resilience")),
                    "confidence_score": _score_int(scores.get("confidence")),
                    "serp_archetype": metro.get("serp_archetype") if metro else None,
                    "ai_exposure": metro.get("ai_exposure") if metro else None,
                    "difficulty_tier": metro.get("difficulty_tier") if metro else None,
                    "meta": meta,
                }
            )
            .execute()
        )
        _raise_on_error(result)

    def list_targets_by_ids(self, target_ids: Sequence[str]) -> list[RefreshTarget]:
        if not target_ids:
            return []
        result = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .in_("id", list(target_ids))
            .execute()
        )
        return self._targets_from_rows(_result_rows(result))

    def list_targets_by_report_ids(
        self,
        report_ids: Sequence[str],
    ) -> list[RefreshTarget]:
        if not report_ids:
            return []
        result = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .in_("latest_report_id", list(report_ids))
            .execute()
        )
        return self._targets_from_rows(_result_rows(result))

    def list_targets_for_filters(
        self,
        filters: dict[str, Any],
        limit: int,
    ) -> list[RefreshTarget]:
        if limit <= 0:
            return []
        query = (
            self._client.table("explore_refresh_targets")
            .select(_EXPLORE_TARGET_SELECT)
            .eq("active", True)
        )

        if filters.get("state"):
            query = query.eq("state", filters["state"])
        states = _non_empty_values(filters.get("states"))
        if states:
            query = query.in_("state", states)
        if filters.get("niche_normalized"):
            query = query.eq("niche_normalized", filters["niche_normalized"])
        if filters.get("niche"):
            query = query.eq("niche_keyword", filters["niche"])
        if filters.get("service"):
            query = query.eq("niche_keyword", filters["service"])
        if filters.get("cbsa_code"):
            query = query.eq("cbsa_code", filters["cbsa_code"])
        cbsa_codes = _non_empty_values(filters.get("cbsa_codes"))
        if cbsa_codes:
            query = query.in_("cbsa_code", cbsa_codes)

        result = query.order("priority", desc=False).limit(limit).execute()
        return self._targets_from_rows(_result_rows(result))

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        run_result = (
            self._client.table("explore_refresh_runs")
            .select("*")
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        run_rows = _result_rows(run_result)
        if not run_rows:
            return {"id": run_id, "status": "missing", "items": []}

        item_result = (
            self._client.table("explore_refresh_run_items")
            .select("*")
            .eq("run_id", run_id)
            .order("created_at", desc=False)
            .execute()
        )
        return {**run_rows[0], "items": _result_rows(item_result)}


class SupabasePersistence:
    """Writes an M9 report and its normalized children to Supabase."""

    def __init__(self, *, client: _SupabaseLike | None = None) -> None:
        if client is None:
            from supabase import create_client

            url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                missing = [v for v in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
                           if not os.environ.get(v)]
                raise RuntimeError(
                    f"Cannot persist report — missing env var(s): {', '.join(missing)}"
                )
            client = create_client(url, key)
        self._client = client

    @property
    def client(self) -> _SupabaseLike:
        return self._client

    def persist_report(self, report: dict[str, Any]) -> str:
        report_id = report["report_id"]
        persist_start = time.monotonic()
        logger.info("persist_report START report_id=%s", report_id)

        t0 = time.monotonic()
        self._client.table("reports").insert(build_report_row(report)).execute()
        reports_ms = int((time.monotonic() - t0) * 1000)
        logger.info("persist_report inserted reports row for %s duration_ms=%d",
                     report_id, reports_ms)

        keyword_rows = build_keyword_rows(report)
        if keyword_rows:
            t0 = time.monotonic()
            self._client.table("report_keywords").insert(keyword_rows).execute()
            kw_ms = int((time.monotonic() - t0) * 1000)
            logger.info("persist_report inserted %d report_keywords rows duration_ms=%d",
                        len(keyword_rows), kw_ms)

        signal_rows = build_metro_signal_rows(report)
        if signal_rows:
            t0 = time.monotonic()
            self._client.table("metro_signals").insert(signal_rows).execute()
            sig_ms = int((time.monotonic() - t0) * 1000)
            logger.info("persist_report inserted %d metro_signals rows duration_ms=%d",
                        len(signal_rows), sig_ms)

        score_rows = build_metro_score_rows(report)
        if score_rows:
            t0 = time.monotonic()
            self._client.table("metro_scores").insert(score_rows).execute()
            score_ms = int((time.monotonic() - t0) * 1000)
            logger.info("persist_report inserted %d metro_scores rows duration_ms=%d",
                        len(score_rows), score_ms)

        score_v2_rows = build_metro_score_v2_rows(report)
        if score_v2_rows:
            t0 = time.monotonic()
            self._client.table("metro_score_v2").insert(score_v2_rows).execute()
            score_v2_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "persist_report inserted %d metro_score_v2 rows duration_ms=%d",
                len(score_v2_rows),
                score_v2_ms,
            )

        fact_rows = build_seo_fact_rows(report)
        if fact_rows:
            t0 = time.monotonic()
            facts_table = self._client.table("seo_facts")
            if not hasattr(facts_table, "upsert"):
                raise RuntimeError(
                    "Cannot persist seo_facts: Supabase table client lacks upsert; "
                    "idempotent writes are required."
                )
            facts_table.upsert(
                fact_rows,
                on_conflict="niche_normalized,cbsa_code,keyword,snapshot_date",
            ).execute()
            facts_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "persist_report upserted %d seo_facts rows duration_ms=%d",
                len(fact_rows),
                facts_ms,
            )

        total_ms = int((time.monotonic() - persist_start) * 1000)
        logger.info("persist_report DONE report_id=%s total_ms=%d", report_id, total_ms)
        return report_id
