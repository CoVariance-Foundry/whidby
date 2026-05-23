"""V2 benchmark-relative score vector implementation."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.config.constants import MEDIAN_LOCAL_SERVICE_CPC

from .ai_resilience_score import compute_ai_resilience_score
from .benchmark_repository import SeoBenchmarkCell, SeoBenchmarkRepository
from .normalization import clamp

DEFAULT_VOLUME_PER_CAPITA = 0.0025
DEFAULT_ESTABLISHMENTS_PER_100K = 50.0
DEFAULT_REVIEW_FLOOR = 30.0
DEFAULT_REVIEW_VELOCITY = 3.0


def compute_v2_scores_with_repository(
    *,
    niche_normalized: str,
    cbsa_code: str,
    metro_signals: Mapping[str, Any],
    benchmark_repository: SeoBenchmarkRepository,
) -> dict[str, Any]:
    """Compute V2 scores after reading the benchmark through the repository."""
    signals = _flatten_signals(metro_signals)
    population_class = str(signals.get("population_class") or "").strip()
    benchmark = None
    if population_class:
        benchmark = benchmark_repository.get(
            niche_normalized=niche_normalized,
            population_class=population_class,
        )
    return compute_v2_scores(
        niche_normalized=niche_normalized,
        cbsa_code=cbsa_code,
        metro_signals=signals,
        benchmark=benchmark,
    )


def compute_v2_scores(
    *,
    niche_normalized: str,
    cbsa_code: str,
    metro_signals: Mapping[str, Any],
    benchmark: SeoBenchmarkCell | None,
) -> dict[str, Any]:
    """Compute the V2 score vector for one metro."""
    signals = _flatten_signals(metro_signals)
    population_class = (
        benchmark.population_class
        if benchmark is not None
        else str(signals.get("population_class") or "").strip() or None
    )
    no_local_pack = not _bool(signals.get("local_pack_present"))
    cbp_missing = signals.get("cbp_establishments") is None and signals.get("establishments") is None
    benchmark_confidence = benchmark.confidence_label if benchmark else "insufficient"
    benchmark_sample_size = benchmark.sample_size_metros if benchmark else 0
    top3_review_data_low_coverage = (
        not no_local_pack
        and (
            _number(signals.get("top3_review_count_coverage")) < 0.67
            or _number(signals.get("top3_review_velocity_coverage")) < 0.67
        )
    )
    top5_organic_data_low_coverage = _top5_organic_data_low_coverage(signals)

    return {
        "niche_normalized": niche_normalized,
        "cbsa_code": cbsa_code,
        "scores": {
            "demand_strength": {
                "value": _demand_strength(signals, benchmark),
                "higher_is_better": True,
                "range": "0-200",
            },
            "organic_difficulty": {
                "value": _organic_difficulty(signals),
                "higher_is_better": False,
                "range": "0-100",
            },
            "local_difficulty": {
                "value": None if no_local_pack else _local_difficulty(signals, benchmark),
                "higher_is_better": False,
                "range": "0-100",
            },
            "monetization_signal": {
                "value": _monetization_signal(signals, benchmark),
                "higher_is_better": True,
                "range": "0-200",
            },
            "ai_resilience": {
                "value": _ai_resilience(signals),
                "higher_is_better": True,
                "range": "0-100",
            },
        },
        "benchmark": {
            "population_class": population_class or None,
            "sample_size": benchmark_sample_size,
            "confidence_label": benchmark_confidence,
        },
        "flags": {
            "no_local_pack_detected": no_local_pack,
            "benchmark_undersampled": benchmark is None or benchmark.is_undersampled,
            "cbp_data_missing": cbp_missing,
            "top3_review_data_low_coverage": top3_review_data_low_coverage,
            "top5_organic_data_low_coverage": top5_organic_data_low_coverage,
        },
        "spec_version": "2.0",
    }


def _flatten_signals(signals: Mapping[str, Any]) -> dict[str, Any]:
    flattened = dict(signals)
    for key in (
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
    ):
        value = signals.get(key)
        if isinstance(value, Mapping):
            flattened.update(value)
    if "commercial_search_volume" not in flattened:
        transactional_ratio = clamp(_number(flattened.get("transactional_ratio")), 0.0, 1.0)
        flattened["commercial_search_volume"] = (
            _number(flattened.get("total_search_volume")) * transactional_ratio
        )
    return flattened


def _number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    return bool(value)


def _top5_organic_data_low_coverage(signals: Mapping[str, Any]) -> bool:
    return _top5_metric_coverage(signals, "top5_da_coverage", "avg_top5_da") < 0.6 or (
        _top5_metric_coverage(
            signals,
            "top5_lighthouse_coverage",
            "avg_top5_lighthouse",
        )
        < 0.6
    )


def _top5_metric_coverage(
    signals: Mapping[str, Any],
    coverage_key: str,
    value_key: str,
) -> float:
    coverage = _optional_number(signals.get(coverage_key))
    if coverage is not None:
        return clamp(coverage, 0.0, 1.0)
    return 1.0 if _optional_number(signals.get(value_key)) is not None else 0.0


def _positive(value: float | None, default: float) -> float:
    if value is None or value <= 0:
        return default
    return value


def _ai_resilience(signals: Mapping[str, Any]) -> int:
    transactional_ratio = _number(
        signals.get("transactional_keyword_ratio"),
        _number(signals.get("transactional_ratio")),
    )
    sanitized = {
        "aio_trigger_rate": _number(signals.get("aio_trigger_rate")),
        "transactional_keyword_ratio": transactional_ratio,
        "local_fulfillment_required": _number(signals.get("local_fulfillment_required"), 1.0),
        "paa_density": _number(signals.get("paa_density")),
        "niche_type": str(signals.get("niche_type") or "local_service").strip() or "local_service",
    }
    return int(round(compute_ai_resilience_score(sanitized)))


def _demand_strength(signals: Mapping[str, Any], benchmark: SeoBenchmarkCell | None) -> int:
    observed_volume = _number(signals.get("commercial_search_volume"))
    population = max(_number(signals.get("population"), 1.0), 1.0)
    observed_cpc = _number(signals.get("avg_cpc"))

    observed_per_capita = observed_volume / population
    benchmark_per_capita = _positive(
        benchmark.median_total_volume_per_capita if benchmark else None,
        DEFAULT_VOLUME_PER_CAPITA,
    )
    benchmark_cpc = _positive(
        benchmark.median_avg_cpc if benchmark else None,
        MEDIAN_LOCAL_SERVICE_CPC,
    )

    volume_score = min(observed_per_capita / benchmark_per_capita, 2.0) * 100.0
    cpc_ratio = observed_cpc / max(benchmark_cpc, 0.01)
    cpc_adjustment = clamp(cpc_ratio, 0.5, 1.5)
    return int(round(clamp(volume_score * cpc_adjustment, 0.0, 200.0)))


def _organic_difficulty(signals: Mapping[str, Any]) -> int:
    aggregator_count = _number(signals.get("aggregator_count"))
    local_biz_count = _number(signals.get("local_biz_count"))
    avg_top5_da = _optional_number(signals.get("avg_top5_da"))

    aggregator_pressure = clamp(aggregator_count / 10.0, 0.0, 1.0)
    local_density = clamp(local_biz_count / 10.0, 0.0, 1.0)
    raw = (aggregator_pressure * 0.55 + local_density * 0.30) * 100.0

    if avg_top5_da is not None:
        da_score = clamp(avg_top5_da / 60.0, 0.0, 1.0) * 100.0
        raw = raw * 0.85 + da_score * 0.15
    return int(round(clamp(raw)))


def _local_difficulty(signals: Mapping[str, Any], benchmark: SeoBenchmarkCell | None) -> int:
    benchmark_floor = _positive(
        float(benchmark.median_top3_review_count_min)
        if benchmark and benchmark.median_top3_review_count_min is not None
        else None,
        DEFAULT_REVIEW_FLOOR,
    )
    benchmark_velocity = _positive(
        benchmark.median_top3_review_velocity if benchmark else None,
        DEFAULT_REVIEW_VELOCITY,
    )
    review_floor = _first_positive(
        signals.get("top3_review_count_min"),
        signals.get("local_pack_review_count_avg"),
        default=benchmark_floor,
    )
    velocity = _first_positive(
        signals.get("top3_review_velocity_avg"),
        signals.get("review_velocity_avg"),
        default=benchmark_velocity,
    )

    review_pressure = min(review_floor / max(benchmark_floor, 1.0), 3.0)
    velocity_pressure = min(velocity / max(benchmark_velocity, 0.1), 3.0)
    raw = (review_pressure / 3.0) * 60.0 + (velocity_pressure / 3.0) * 40.0
    return int(round(clamp(raw)))


def _first_positive(*values: Any, default: float) -> float:
    for value in values:
        numeric = _optional_number(value)
        if numeric is not None and numeric > 0:
            return numeric
    return default


def _monetization_signal(signals: Mapping[str, Any], benchmark: SeoBenchmarkCell | None) -> int:
    population = max(_number(signals.get("population"), 1.0), 1.0)
    establishments = signals.get("cbp_establishments", signals.get("establishments"))

    if establishments is None:
        cbp_score = 50.0
    else:
        establishments_per_100k = (_number(establishments) / population) * 100_000.0
        benchmark_density = _positive(
            benchmark.median_establishments_per_100k if benchmark else None,
            DEFAULT_ESTABLISHMENTS_PER_100K,
        )
        cbp_score = min(establishments_per_100k / benchmark_density, 2.0) * 100.0

    spend_signal = 0.0
    if _bool(signals.get("lsa_present")):
        spend_signal += 30.0
    if _bool(signals.get("ads_present") or signals.get("ads_top_present")):
        spend_signal += 20.0

    raw = cbp_score * 0.70 + spend_signal * 1.5 * 0.30
    return int(round(clamp(raw, 0.0, 200.0)))
