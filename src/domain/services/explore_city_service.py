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
        normalized_filter = _normalize_filter(service_filter)
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
        sorted_scores = sorted(
            cached_scores,
            key=lambda score: (
                -_presentation_score(score),
                str(score.get("niche_keyword") or ""),
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
            "cached_scores": sorted_scores,
        }


def _normalize_filter(service_filter: str | None) -> str | None:
    if service_filter is None:
        return None

    normalized = service_filter.strip().lower()
    return normalized or None


def _group_scores_by_cbsa(
    scores: Sequence[Mapping[str, Any]],
    normalized_filter: str | None,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for score in scores:
        if normalized_filter is not None:
            niche_normalized = str(score.get("niche_normalized") or "").strip().lower()
            if niche_normalized != normalized_filter:
                continue

        grouped[str(score["cbsa_code"])].append(dict(score))

    return dict(grouped)


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
