"""Explore Cities read-model orchestration."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.domain.explore.entities import ExploreCitySummary
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


class ExploreCityService:
    """Build Explore city summaries from repository read inputs."""

    def __init__(self, repository: ExploreCityRepository) -> None:
        self._repository = repository

    def list_cities(self, service_filter: str | None = None) -> list[ExploreCitySummary]:
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

    def _build_summary(
        self,
        *,
        metro: Mapping[str, Any],
        cached_scores: list[dict[str, Any]],
        metric_inputs: Mapping[str, Any] | None,
    ) -> ExploreCitySummary:
        cbsa_code = str(metro["cbsa_code"])
        unique_scores = _latest_unique_scores(cached_scores)
        sorted_scores = sorted(
            unique_scores,
            key=lambda score: (
                -_presentation_score(score),
                _timestamp_key(score),
                str(score.get("niche_keyword") or score.get("niche_normalized") or ""),
            ),
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
            "best_score": _best_score(best_score_row),
            "score_system": (
                str(best_score_row.get("score_system") or "none")
                if best_score_row
                else "none"
            ),
            "last_scored_at": _summary_last_scored_at(metro, sorted_scores),
            "stale": _summary_stale(metro, best_score_row),
            "cached_scores": sorted_scores,
        }


def _normalize_service(service_filter: str | None) -> str | None:
    if service_filter is None:
        return None

    normalized = normalize_niche(service_filter)
    return normalized or None


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


def _summary_last_scored_at(
    metro: Mapping[str, Any],
    scores: Sequence[Mapping[str, Any]],
) -> Any | None:
    metro_timestamp = metro.get("last_scored_at") or metro.get("latest_scored_at")
    if metro_timestamp is not None:
        return metro_timestamp

    latest_score = max(scores, key=_timestamp_key, default=None)
    if latest_score is None:
        return None
    return latest_score.get("last_scored_at") or latest_score.get("latest_scored_at")


def _summary_stale(
    metro: Mapping[str, Any],
    best_score_row: Mapping[str, Any] | None,
) -> bool | None:
    if "stale" in metro:
        return bool(metro["stale"]) if metro["stale"] is not None else None
    if "is_stale" in metro:
        return bool(metro["is_stale"]) if metro["is_stale"] is not None else None

    if best_score_row is None:
        return None
    if "stale" in best_score_row:
        return (
            bool(best_score_row["stale"])
            if best_score_row["stale"] is not None
            else None
        )
    if "is_stale" in best_score_row:
        return (
            bool(best_score_row["is_stale"])
            if best_score_row["is_stale"] is not None
            else None
        )
    return None
