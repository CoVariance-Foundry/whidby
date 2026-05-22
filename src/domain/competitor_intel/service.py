from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol


class CompetitorIntelReadRepository(Protocol):
    """Read boundary for durable competitor-intel facts."""

    def find_metro(self, *, city: str | None, state: str | None) -> dict[str, Any] | None:
        ...

    def fetch_score_context(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        report_id: str | None,
        account_id: str | None,
    ) -> dict[str, Any] | None:
        ...

    def fetch_keyword_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str | None,
        account_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        ...

    def fetch_organic_competitor_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str | None,
        account_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        ...

    def fetch_local_pack_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str | None,
        account_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        ...

    def fetch_report_context(
        self,
        *,
        report_id: str,
        account_id: str | None,
    ) -> dict[str, Any] | None:
        ...

    def create_run_record(self, payload: dict[str, Any]) -> str:
        ...


class CompetitorIntelService:
    """Build status-shaped competitor intel from already-persisted facts."""

    def __init__(self, repository: CompetitorIntelReadRepository) -> None:
        self._repository = repository

    def get_read_model(self, request: dict[str, Any]) -> dict[str, Any]:
        target = _target_from_request(request)
        account_id = _string_or_none(request.get("account_id"))
        report_context = None
        if target.get("report_id"):
            report_context = self._repository.fetch_report_context(
                report_id=str(target["report_id"]),
                account_id=account_id,
            )
            if report_context is None:
                return {
                    "status": "not_found",
                    "message": "Report context is unavailable for competitor intel.",
                    "target": target,
                }
            target = _merge_report_context(target, report_context)

        target = self._resolve_metro(target)
        if not _has_runnable_target(target):
            return {
                "status": "not_found",
                "message": "City and service are required for competitor intel.",
                "target": target,
            }

        cbsa_code = target.get("cbsa_code")
        niche_normalized = target.get("niche_normalized")
        if not cbsa_code or not niche_normalized:
            return {
                "status": "ready_to_run",
                "message": "Competitor intel can be run once this market is resolved.",
                "target": target,
            }

        report_id = _string_or_none(target.get("report_id"))
        keyword = _string_or_none(target.get("primary_keyword") or target.get("niche_keyword"))
        score_context = self._repository.fetch_score_context(
            cbsa_code=cbsa_code,
            niche_normalized=niche_normalized,
            report_id=report_id,
            account_id=account_id,
        )
        if not report_id and score_context:
            report_id = _string_or_none(score_context.get("report_id"))
            target["report_id"] = report_id

        keyword_facts = self._repository.fetch_keyword_facts(
            cbsa_code=cbsa_code,
            niche_normalized=niche_normalized,
            keyword=keyword,
            account_id=account_id,
            limit=20,
        )
        organic_facts = self._repository.fetch_organic_competitor_facts(
            cbsa_code=cbsa_code,
            niche_normalized=niche_normalized,
            keyword=keyword,
            account_id=account_id,
            limit=10,
        )
        local_pack_facts = self._repository.fetch_local_pack_facts(
            cbsa_code=cbsa_code,
            niche_normalized=niche_normalized,
            keyword=keyword,
            account_id=account_id,
            limit=10,
        )
        if report_context is None and report_id:
            report_context = self._repository.fetch_report_context(
                report_id=report_id,
                account_id=account_id,
            )

        summary = _summary(score_context, keyword_facts, local_pack_facts)
        facts = _facts(keyword_facts, organic_facts, local_pack_facts)
        report = _report(report_context)

        if organic_facts or local_pack_facts:
            status = "dossier"
            message = "Competitor dossier is available from durable facts."
        elif score_context or keyword_facts:
            status = "aggregate_only"
            message = "Aggregate competitor signals are available; detailed listings can be refreshed."
        else:
            status = "ready_to_run"
            message = "No durable competitor facts found yet for this market."

        response: dict[str, Any] = {
            "status": status,
            "message": message,
            "target": target,
            "summary": summary,
            "organic_competitors": [_organic_competitor(row) for row in organic_facts],
            "local_pack_competitors": [
                _local_pack_competitor(row) for row in local_pack_facts
            ],
            "facts": facts,
            "report": report,
        }
        if status == "dossier":
            response["dossier"] = _dossier(
                target=target,
                summary=summary,
                organic_facts=organic_facts,
                local_pack_facts=local_pack_facts,
                facts=facts,
                report=report,
            )
        elif status == "aggregate_only":
            response["aggregate"] = _aggregate(
                target=target,
                summary=summary,
                facts=facts,
                report=report,
            )
        return response

    def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        read_model = self.get_read_model(request)
        state = str(read_model.get("status") or "ready_to_run")
        if state not in {"dossier", "aggregate_only"}:
            raise RuntimeError(
                "Fresh competitor intel collection is not available for this target yet."
            )
        run_status = "succeeded" if state in {"dossier", "aggregate_only"} else "queued"
        result = read_model if run_status == "succeeded" else None
        run_id = self._repository.create_run_record(
            {
                "account_id": _string_or_none(request.get("account_id")),
                "created_by_user_id": _string_or_none(request.get("created_by_user_id")),
                "report_id": _string_or_none(read_model.get("target", {}).get("report_id")),
                "cbsa_code": _string_or_none(read_model.get("target", {}).get("cbsa_code")),
                "niche_normalized": _string_or_none(
                    read_model.get("target", {}).get("niche_normalized")
                ),
                "service": _string_or_none(read_model.get("target", {}).get("service")),
                "keyword": _string_or_none(
                    read_model.get("target", {}).get("primary_keyword")
                    or read_model.get("target", {}).get("niche_keyword")
                ),
                "input_payload": request,
                "quota_consumed": int(request.get("quota_consumed") or 0),
                "status": run_status,
                "result_summary": _run_summary(read_model),
                "errors": [],
            }
        )
        return {
            "run_id": run_id,
            "status": run_status,
            "state": state,
            "quota_consumed": int(request.get("quota_consumed") or 0),
            "target": read_model.get("target", {}),
            "result": result,
        }

    def _resolve_metro(self, target: dict[str, Any]) -> dict[str, Any]:
        if target.get("cbsa_code") or not target.get("city"):
            return target

        metro = self._repository.find_metro(
            city=_string_or_none(target.get("city")),
            state=_string_or_none(target.get("state")),
        )
        if not metro:
            return target

        resolved = dict(target)
        resolved["cbsa_code"] = _string_or_none(metro.get("cbsa_code"))
        resolved["cbsa_name"] = _string_or_none(metro.get("cbsa_name"))
        resolved["state"] = _string_or_none(resolved.get("state") or metro.get("state"))
        return resolved


def _target_from_request(request: dict[str, Any]) -> dict[str, Any]:
    service = _string_or_none(request.get("service") or request.get("niche_keyword"))
    return {
        "city": _string_or_none(request.get("city")),
        "state": _string_or_none(request.get("state")),
        "service": service,
        "niche_keyword": _string_or_none(request.get("niche_keyword") or service),
        "niche_normalized": _normalize_niche(
            request.get("niche_normalized") or request.get("service") or service
        ),
        "cbsa_code": _string_or_none(request.get("cbsa_code")),
        "cbsa_name": _string_or_none(request.get("cbsa_name")),
        "primary_keyword": _string_or_none(request.get("primary_keyword")),
        "report_id": _string_or_none(request.get("report_id")),
    }


def _has_runnable_target(target: dict[str, Any]) -> bool:
    return bool((target.get("city") or target.get("cbsa_code")) and target.get("service"))


def _merge_report_context(
    target: dict[str, Any],
    report_context: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(target)
    merged["service"] = merged.get("service") or _string_or_none(
        report_context.get("niche_keyword")
    )
    merged["niche_keyword"] = merged.get("niche_keyword") or merged.get("service")

    metros = report_context.get("metros")
    first_metro = metros[0] if isinstance(metros, list) and metros else {}
    if isinstance(first_metro, dict):
        merged["cbsa_code"] = merged.get("cbsa_code") or _string_or_none(
            first_metro.get("cbsa_code")
        )
        merged["cbsa_name"] = merged.get("cbsa_name") or _string_or_none(
            first_metro.get("cbsa_name")
        )
        merged["state"] = merged.get("state") or _string_or_none(
            first_metro.get("state")
        )

    geo_target = _string_or_none(report_context.get("geo_target"))
    if geo_target and not merged.get("city"):
        city, state = _city_state_from_geo_target(geo_target)
        merged["city"] = city
        merged["state"] = merged.get("state") or state

    merged["niche_normalized"] = merged.get("niche_normalized") or _normalize_niche(
        merged.get("service")
    )
    return merged


def _city_state_from_geo_target(value: str) -> tuple[str | None, str | None]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        return None, None
    city = parts[0]
    state = parts[1] if len(parts) > 1 and len(parts[1]) <= 3 else None
    return city, state


def _normalize_niche(value: Any) -> str | None:
    text = _string_or_none(value)
    if not text:
        return None
    return text.lower().replace("-", " ").replace("_", " ").strip().replace(" ", "_")


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return _string_or_none(value)


def _summary(
    score_context: dict[str, Any] | None,
    keyword_facts: list[dict[str, Any]],
    local_pack_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_fact = keyword_facts[0] if keyword_facts else {}
    top_review_counts = [
        _number(row.get("review_count")) for row in local_pack_facts if row.get("review_count") is not None
    ]
    return {
        "demand_strength": _number((score_context or {}).get("demand_strength")),
        "organic_difficulty": _number((score_context or {}).get("organic_difficulty")),
        "local_difficulty": _number((score_context or {}).get("local_difficulty")),
        "ai_resilience": _number((score_context or {}).get("ai_resilience")),
        "benchmark_confidence": _string_or_none((score_context or {}).get("benchmark_confidence")),
        "search_volume_monthly": _number(latest_fact.get("search_volume_monthly")),
        "avg_top5_da": _number(latest_fact.get("avg_top5_da")),
        "top5_organic_data_confidence": _string_or_none(
            latest_fact.get("top5_organic_data_confidence")
        ),
        "local_pack_competitor_count": len(local_pack_facts),
        "top_review_count": max(top_review_counts) if top_review_counts else None,
    }


def _organic_competitor(row: dict[str, Any]) -> dict[str, Any]:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    return {
        "rank": row.get("result_rank"),
        "domain": _string_or_none(row.get("domain")) or _string_or_none(row.get("url")),
        "title": _string_or_none(row.get("title")),
        "url": _string_or_none(row.get("url")),
        "domain_authority": _number(row.get("domain_authority")),
        "backlink_count": _number(
            row.get("backlinks_count", evidence.get("backlinks_count"))
        ),
        "referring_domains": _number(
            row.get("referring_domains_count", evidence.get("referring_domains_count"))
        ),
        "lighthouse_score": _number(row.get("lighthouse_score")),
        "schema_adoption": row.get("has_localbusiness_schema"),
        "schema_types": row.get("schema_types") if isinstance(row.get("schema_types"), list) else [],
        "title_keyword_match": row.get("title_keyword_match"),
        "is_aggregator": row.get("is_aggregator") is True,
        "source": _string_or_none(row.get("source")),
        "snapshot_date": _iso(row.get("snapshot_date")),
    }


def _local_pack_competitor(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": row.get("listing_rank"),
        "name": _string_or_none(row.get("business_name")),
        "exact_match_name": row.get("exact_match_name") is True,
        "review_count": row.get("review_count"),
        "review_velocity_monthly": _number(row.get("review_velocity_monthly")),
        "rating": _number(row.get("rating")),
        "gbp_completeness": _number(row.get("gbp_completeness")),
        "photo_count": row.get("photo_count"),
        "has_recent_post": row.get("has_recent_post"),
        "categories": row.get("categories") if isinstance(row.get("categories"), list) else [],
        "source": _string_or_none(row.get("source")),
        "snapshot_date": _iso(row.get("snapshot_date")),
    }


def _facts(
    keyword_facts: list[dict[str, Any]],
    organic_facts: list[dict[str, Any]],
    local_pack_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_keyword = keyword_facts[0] if keyword_facts else {}
    latest_pack = local_pack_facts[0] if local_pack_facts else {}
    return {
        "keyword_fact_count": len(keyword_facts),
        "organic_competitor_fact_count": len(organic_facts),
        "local_pack_fact_count": len(local_pack_facts),
        "latest_keyword_snapshot_date": _iso(latest_keyword.get("snapshot_date")),
        "latest_organic_snapshot_date": _iso(
            (organic_facts[0] if organic_facts else {}).get("snapshot_date")
        ),
        "latest_local_pack_snapshot_date": _iso(latest_pack.get("snapshot_date")),
        "local_pack_present": any(row.get("local_pack_present") is True for row in keyword_facts)
        or bool(local_pack_facts),
    }


def _report(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "report_id": _string_or_none(row.get("id")),
        "created_at": _iso(row.get("created_at")),
        "niche_keyword": _string_or_none(row.get("niche_keyword")),
        "geo_scope": _string_or_none(row.get("geo_scope")),
        "geo_target": _string_or_none(row.get("geo_target")),
        "strategy_profile": _string_or_none(row.get("strategy_profile")),
    }


def _coverage(facts: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label": "Organic SERP competitors",
            "status": "available"
            if facts["organic_competitor_fact_count"]
            else ("partial" if facts["keyword_fact_count"] else "missing"),
            "detail": (
                f"{facts['organic_competitor_fact_count']} ranked organic rows"
                if facts["organic_competitor_fact_count"]
                else "Aggregate top-5 signals only."
            ),
        },
        {
            "label": "Local pack competitors",
            "status": "available" if facts["local_pack_fact_count"] else "missing",
            "detail": (
                f"{facts['local_pack_fact_count']} local pack rows"
                if facts["local_pack_fact_count"]
                else "No local pack rows persisted yet."
            ),
        },
        {
            "label": "Freshness",
            "status": "available"
            if facts.get("latest_organic_snapshot_date")
            or facts.get("latest_local_pack_snapshot_date")
            else "partial",
            "detail": (
                facts.get("latest_organic_snapshot_date")
                or facts.get("latest_local_pack_snapshot_date")
                or facts.get("latest_keyword_snapshot_date")
                or "No snapshot date available."
            ),
        },
    ]


def _summary_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"label": "Organic difficulty", "value": summary.get("organic_difficulty")},
        {"label": "Avg top-5 DA", "value": summary.get("avg_top5_da")},
        {"label": "Local difficulty", "value": summary.get("local_difficulty")},
        {"label": "Search volume", "value": summary.get("search_volume_monthly")},
        {"label": "Data confidence", "value": summary.get("top5_organic_data_confidence")},
    ]


def _ledger(target: dict[str, Any], report: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        {
            "label": "Market",
            "value": ", ".join(
                str(part)
                for part in (target.get("city"), target.get("state"))
                if part
            )
            or target.get("cbsa_name")
            or target.get("cbsa_code"),
        },
        {"label": "Service", "value": target.get("service")},
        {"label": "CBSA", "value": target.get("cbsa_code")},
        {"label": "Report", "value": (report or {}).get("report_id")},
        {"label": "Generated", "value": (report or {}).get("created_at")},
    ]


def _win_plan(
    organic_competitors: list[dict[str, Any]],
    local_pack_competitors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plays: list[dict[str, Any]] = []
    if any(item.get("schema_adoption") is False for item in organic_competitors):
        plays.append(
            {
                "title": "Ship structured data before the field catches up",
                "play": "Add LocalBusiness, Service, FAQ, and Breadcrumb schema across the local landing page set.",
                "estimated_impact": "High",
                "rationale": "At least one ranking competitor lacks visible schema evidence.",
            }
        )
    if any(_number(item.get("lighthouse_score")) is not None and _number(item.get("lighthouse_score")) < 70 for item in organic_competitors):
        plays.append(
            {
                "title": "Exploit technical softness",
                "play": "Beat the current SERP with faster page load, tighter internal links, and cleaner core landing-page templates.",
                "estimated_impact": "Medium",
                "rationale": "Persisted Lighthouse evidence shows technical weakness in the current field.",
            }
        )
    if local_pack_competitors:
        plays.append(
            {
                "title": "Close the GBP review gap",
                "play": "Build a review-generation and GBP freshness plan around the top local-pack review counts.",
                "estimated_impact": "Medium",
                "rationale": "Local-pack rows are available for review and profile completeness comparison.",
            }
        )
    if not plays:
        plays.append(
            {
                "title": "Run a fresh competitor crawl",
                "play": "Collect durable organic and local-pack rows before choosing the launch attack path.",
                "estimated_impact": "Medium",
                "rationale": "Only aggregate evidence is available for this market.",
            }
        )
    return plays[:5]


def _dossier(
    *,
    target: dict[str, Any],
    summary: dict[str, Any],
    organic_facts: list[dict[str, Any]],
    local_pack_facts: list[dict[str, Any]],
    facts: dict[str, Any],
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    organic_competitors = [_organic_competitor(row) for row in organic_facts]
    local_pack_competitors = [_local_pack_competitor(row) for row in local_pack_facts]
    return {
        "report_id": target.get("report_id") or (report or {}).get("report_id"),
        "city": target.get("city"),
        "state": target.get("state"),
        "service": target.get("service"),
        "generated_at": (report or {}).get("created_at"),
        "market_ledger": _ledger(target, report),
        "summary_metrics": _summary_metrics(summary),
        "organic_competitors": organic_competitors,
        "local_pack_competitors": local_pack_competitors,
        "win_plan": _win_plan(organic_competitors, local_pack_competitors),
        "coverage": _coverage(facts),
    }


def _aggregate(
    *,
    target: dict[str, Any],
    summary: dict[str, Any],
    facts: dict[str, Any],
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "city": target.get("city"),
        "state": target.get("state"),
        "service": target.get("service"),
        "market_ledger": _ledger(target, report),
        "summary_metrics": _summary_metrics(summary),
        "coverage": _coverage(facts),
    }


def _run_summary(read_model: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": read_model.get("status"),
        "target": read_model.get("target"),
        "facts": read_model.get("facts"),
    }
