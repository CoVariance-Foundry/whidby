"""Explore Cities read-model orchestration."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.domain.explore.entities import (
    ExploreCitySummary,
    ExplorePageResult,
    ExploreServiceMetric,
)
from src.domain.explore.metrics import (
    annualized_growth,
    business_density_per_1k,
    weighted_establishments,
)
from src.pipeline.canonical_key import normalize_niche


class ExploreCityRepository(Protocol):
    """Read boundary for Explore city summaries."""

    def load_metros(self) -> list[dict[str, Any]]:
        ...

    def load_scores(self, cbsa_codes: list[str]) -> list[dict[str, Any]]:
        ...

    def load_metric_inputs(
        self,
        cbsa_codes: list[str],
        niche_normalized: str,
    ) -> dict[str, Any]:
        ...

    def load_city_detail(self, cbsa_code: str) -> dict[str, Any] | None:
        ...


class ExploreCityService:
    """Build Explore city summaries from repository read inputs."""

    def __init__(self, repository: ExploreCityRepository | Any) -> None:
        self._repository = repository

    def list_cities(
        self,
        service_filter: str | None = None,
        *,
        states: list[str] | None = None,
        population_min: int | None = None,
        population_max: int | None = None,
        income_min: int | None = None,
        income_max: int | None = None,
        growing_only: bool = False,
        sort: str = "score",
        direction: str = "desc",
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[ExploreCitySummary] | ExplorePageResult:
        if hasattr(self._repository, "list_city_rows"):
            return self._list_city_rows(
                service_filter=service_filter,
                states=states or [],
                population_min=population_min,
                population_max=population_max,
                income_min=income_min,
                income_max=income_max,
                growing_only=growing_only,
                sort=sort,
                direction=direction,
                limit=limit,
                cursor=cursor,
            )

        normalized_filter = _normalize_service(service_filter)
        metros = self._repository.load_metros()
        cbsa_codes = [str(metro["cbsa_code"]) for metro in metros]

        scores = self._repository.load_scores(cbsa_codes) if cbsa_codes else []
        scores_by_cbsa = _group_scores_by_cbsa(scores, normalized_filter)

        metric_inputs = (
            self._repository.load_metric_inputs(cbsa_codes, normalized_filter)
            if cbsa_codes and normalized_filter is not None
            else None
        )

        return [
            self._build_summary(
                metro=metro,
                cached_scores=scores_by_cbsa.get(str(metro["cbsa_code"]), []),
                metric_inputs=metric_inputs,
            )
            for metro in metros
        ]

    def _list_city_rows(
        self,
        *,
        service_filter: str | None,
        states: list[str],
        population_min: int | None,
        population_max: int | None,
        income_min: int | None,
        income_max: int | None,
        growing_only: bool,
        sort: str,
        direction: str,
        limit: int,
        cursor: str | None,
    ) -> ExplorePageResult:
        normalized_filter = _normalize_service(service_filter)
        safe_limit = max(1, limit)
        rows = self._repository.list_city_rows(
            service=service_filter,
            states=states,
            population_min=population_min,
            population_max=population_max,
            income_min=income_min,
            income_max=income_max,
            growing_only=growing_only,
            sort=sort,
            direction=direction,
            limit=safe_limit,
            cursor=cursor,
        )
        page_rows = rows[:safe_limit]
        cities = [_summary_from_cell_row(row) for row in page_rows]
        offset = _cursor_offset(cursor)
        return {
            "cities": cities,
            "next_cursor": (
                str(offset + safe_limit) if len(rows) > safe_limit else None
            ),
            "growth_available": any(city["growth_available"] for city in cities),
            "service_filter": normalized_filter,
        }

    def _build_summary(
        self,
        *,
        metro: Mapping[str, Any],
        cached_scores: list[dict[str, Any]],
        metric_inputs: Mapping[str, Any] | None,
    ) -> ExploreCitySummary:
        cbsa_code = str(metro["cbsa_code"])
        unique_scores = _latest_unique_scores(cached_scores)
        sorted_scores = _sort_cached_scores(unique_scores)
        summary_freshness = _summary_freshness(
            metro=metro,
            scores=sorted_scores,
        )
        best_score_row = sorted_scores[0] if sorted_scores else None
        metrics = _city_metrics(
            cbsa_code=cbsa_code,
            population=metro.get("population"),
            metric_inputs=metric_inputs,
        )

        return {
            "cbsa_code": cbsa_code,
            "cbsa_name": str(metro["cbsa_name"]),
            "state": metro.get("state"),
            "population": metro.get("population"),
            "population_class": metro.get("population_class"),
            "median_household_income_usd": metro.get("median_household_income_usd"),
            "owner_occupancy_rate": metro.get("owner_occupancy_rate"),
            "median_age_years": metro.get("median_age_years"),
            "business_density_per_1k": metrics["business_density_per_1k"],
            "establishment_growth_yoy": metrics["establishment_growth_yoy"],
            "growth_available": metrics["establishment_growth_yoy"] is not None,
            "cached_services_count": len(sorted_scores),
            "metric_service": None,
            "best_score": _best_score(best_score_row),
            "score_system": (
                str(best_score_row.get("score_system") or "none")
                if best_score_row
                else "none"
            ),
            "last_scored_at": summary_freshness["last_scored_at"],
            "stale": summary_freshness["stale"],
            "cached_scores": sorted_scores,
        }

    def load_city_detail(self, cbsa_code: str) -> dict[str, Any] | None:
        if not hasattr(self._repository, "load_city_detail"):
            raise RuntimeError("Explore city detail repository is not configured")
        return self._repository.load_city_detail(cbsa_code)


def _normalize_service(service_filter: str | None) -> str | None:
    if service_filter is None:
        return None

    normalized = normalize_niche(service_filter)
    return normalized or None


def _cursor_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except (TypeError, ValueError):
        return 0
    return max(0, offset)


def _summary_from_cell_row(row: Mapping[str, Any]) -> ExploreCitySummary:
    cached_score = _cached_score_from_cell_row(row)
    best_score = _best_score(cached_score)
    has_service = bool(cached_score.get("niche_normalized"))
    return {
        "cbsa_code": str(row["cbsa_code"]),
        "cbsa_name": str(row["cbsa_name"]),
        "state": row.get("state"),
        "population": row.get("population"),
        "population_class": row.get("population_class"),
        "median_household_income_usd": row.get("median_household_income_usd"),
        "owner_occupancy_rate": row.get("owner_occupancy_rate"),
        "median_age_years": row.get("median_age_years"),
        "business_density_per_1k": row.get("business_density_per_1k"),
        "establishment_growth_yoy": row.get("establishment_growth_yoy"),
        "growth_available": bool(row.get("growth_available")),
        "cached_services_count": _cached_services_count(row, has_service),
        "metric_service": _metric_service(row),
        "best_score": best_score,
        "score_system": str(row.get("score_system") or "none"),
        "last_scored_at": row.get("latest_scored_at"),
        "stale": _stale_value(row),
        "cached_scores": [cached_score] if has_service else [],
    }


def _cached_score_from_cell_row(row: Mapping[str, Any]) -> ExploreServiceMetric:
    return {
        "cbsa_code": row.get("cbsa_code"),
        "niche_normalized": row.get("niche_normalized"),
        "niche_keyword": row.get("niche_keyword"),
        "report_id": row.get("report_id"),
        "presentation_score": row.get("presentation_score"),
        "score_system": row.get("score_system"),
        "latest_scored_at": row.get("latest_scored_at"),
        "last_refreshed_at": row.get("last_refreshed_at") or row.get("latest_scored_at"),
        "refresh_target_id": row.get("refresh_target_id"),
        "next_refresh_at": row.get("next_refresh_at"),
        "stale": row.get("stale"),
        "business_density_per_1k": row.get("business_density_per_1k"),
        "establishment_growth_yoy": row.get("establishment_growth_yoy"),
        "growth_available": row.get("growth_available"),
    }


def _cached_services_count(row: Mapping[str, Any], has_service: bool) -> int:
    cached_services_count = row.get("cached_services_count")
    if cached_services_count is not None:
        return int(cached_services_count)
    return 1 if has_service else 0


def _metric_service(row: Mapping[str, Any]) -> str | None:
    service = row.get("niche_keyword") or row.get("niche_normalized")
    return str(service) if service is not None else None


def _group_scores_by_cbsa(
    scores: Sequence[Mapping[str, Any]],
    normalized_filter: str | None,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for score in scores:
        if normalized_filter is not None:
            niche_normalized = _score_service_key(score)
            if niche_normalized != normalized_filter:
                continue

        grouped[str(score["cbsa_code"])].append(dict(score))

    return dict(grouped)


def _latest_unique_scores(scores: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    latest_by_service: dict[str, Mapping[str, Any]] = {}

    for score in scores:
        service_key = _score_service_key(score)
        if not service_key:
            continue

        current = latest_by_service.get(service_key)
        if current is None or _prefer_score(score, current):
            latest_by_service[service_key] = score

    return [dict(score) for score in latest_by_service.values()]


def _prefer_score(candidate: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    candidate_is_v2 = _score_system(candidate) == "v2"
    current_is_v2 = _score_system(current) == "v2"
    if candidate_is_v2 != current_is_v2:
        return candidate_is_v2

    return _timestamp_key(candidate) > _timestamp_key(current)


def _score_service_key(score: Mapping[str, Any]) -> str:
    raw_service = score.get("niche_normalized") or score.get("niche_keyword")
    if raw_service is None:
        return ""
    return normalize_niche(str(raw_service))


def _score_system(score: Mapping[str, Any]) -> str:
    return str(score.get("score_system") or "").strip().lower()


def _sort_cached_scores(scores: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sorted_scores = [dict(score) for score in scores]
    sorted_scores.sort(
        key=lambda score: str(
            score.get("niche_keyword") or score.get("niche_normalized") or ""
        )
    )
    sorted_scores.sort(key=_timestamp_key, reverse=True)
    sorted_scores.sort(key=_presentation_score, reverse=True)
    return sorted_scores


def _city_metrics(
    *,
    cbsa_code: str,
    population: Any,
    metric_inputs: Mapping[str, Any] | None,
) -> dict[str, float | None]:
    if metric_inputs is None:
        return {
            "business_density_per_1k": None,
            "establishment_growth_yoy": None,
        }

    weights_by_naics = metric_inputs.get("weights_by_naics")
    latest_year = metric_inputs.get("latest_year")
    prior_year = metric_inputs.get("prior_year")
    cbp_rows = metric_inputs.get("cbp_rows")

    if not isinstance(weights_by_naics, Mapping) or not isinstance(cbp_rows, Mapping):
        return {
            "business_density_per_1k": None,
            "establishment_growth_yoy": None,
        }

    latest_rows = cbp_rows.get((cbsa_code, latest_year), [])
    prior_rows = cbp_rows.get((cbsa_code, prior_year), [])
    latest_establishments = (
        weighted_establishments(latest_rows, weights_by_naics) if latest_rows else None
    )
    prior_establishments = (
        weighted_establishments(prior_rows, weights_by_naics) if prior_rows else None
    )

    growth = None
    if isinstance(latest_year, int) and isinstance(prior_year, int):
        growth = annualized_growth(
            latest=latest_establishments,
            prior=prior_establishments,
            year_span=latest_year - prior_year,
        )

    return {
        "business_density_per_1k": (
            business_density_per_1k(latest_establishments, population)
            if latest_establishments is not None
            else None
        ),
        "establishment_growth_yoy": growth,
    }


def _presentation_score(score: Mapping[str, Any]) -> int:
    presentation_score = score.get("presentation_score")
    if presentation_score is None:
        return 0
    return int(presentation_score)


def _best_score(score: Mapping[str, Any] | None) -> int | None:
    if score is None or score.get("presentation_score") is None:
        return None

    return int(score["presentation_score"])


def _timestamp_key(score: Mapping[str, Any]) -> str:
    timestamp = score.get("last_scored_at") or score.get("latest_scored_at")
    return str(timestamp or "")


def _summary_freshness(
    metro: Mapping[str, Any],
    scores: Sequence[Mapping[str, Any]],
) -> dict[str, Any | bool | None]:
    metro_timestamp = metro.get("last_scored_at") or metro.get("latest_scored_at")
    metro_stale = _stale_value(metro)
    if metro_timestamp is not None and metro_stale is not None:
        return {"last_scored_at": metro_timestamp, "stale": metro_stale}

    latest_score = max(scores, key=_timestamp_key, default=None)
    if latest_score is None:
        return {"last_scored_at": None, "stale": None}

    return {
        "last_scored_at": (
            latest_score.get("last_scored_at") or latest_score.get("latest_scored_at")
        ),
        "stale": _stale_value(latest_score),
    }


def _stale_value(row: Mapping[str, Any]) -> bool | None:
    if "stale" in row:
        return bool(row["stale"]) if row["stale"] is not None else None
    if "is_stale" in row:
        return bool(row["is_stale"]) if row["is_stale"] is not None else None
    return None
