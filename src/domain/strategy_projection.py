from __future__ import annotations

import math
from typing import Any

from src.domain.strategy_entities import StrategyProjection
from src.scoring.benchmark_warnings import warning_codes_from_mapping


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _number_or_default(row: dict[str, Any], key: str, default: float) -> float:
    value = row.get(key)
    if value is None:
        return default
    return float(value)


def _finite_number(row: dict[str, Any], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite")
    return value


def _warnings(row: dict[str, Any], *codes: str) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    for code in (*codes, *warning_codes_from_mapping(row)):
        if code and code not in seen:
            warnings.append(code)
            seen.add(code)
    return warnings


def project_easy_win(row: dict[str, Any]) -> StrategyProjection:
    demand = min(_number_or_default(row, "demand_strength", 0.0) / 140.0, 1.0) * 100.0
    organic_ease = 100.0 - _number_or_default(row, "organic_difficulty", 100.0)
    local_raw = row.get("local_difficulty")
    local_ease = 65.0 if local_raw is None else 100.0 - float(local_raw)
    ai = _number_or_default(row, "ai_resilience", 50.0)
    score = _clamp(
        (demand * 0.25)
        + (organic_ease * 0.45)
        + (local_ease * 0.20)
        + (ai * 0.10)
    )
    return StrategyProjection(
        strategy_id="easy_win",
        score=round(score, 2),
        evidence={
            "demand_strength": row.get("demand_strength"),
            "organic_difficulty": row.get("organic_difficulty"),
            "local_difficulty": row.get("local_difficulty"),
            "ai_resilience": row.get("ai_resilience"),
        },
        warnings=_warnings(row),
    )


def project_gbp_blitz(row: dict[str, Any]) -> StrategyProjection:
    if not row.get("local_pack_present", True):
        return StrategyProjection(
            strategy_id="gbp_blitz",
            score=0.0,
            evidence={"local_pack_present": False},
            warnings=_warnings(row, "no_local_pack_detected"),
        )
    demand = min(_number_or_default(row, "demand_strength", 0.0) / 120.0, 1.0) * 100.0
    review_floor = _number_or_default(row, "top3_review_count_min", 100.0)
    velocity = _number_or_default(row, "top3_review_velocity_avg", 5.0)
    completeness = _number_or_default(row, "gbp_completeness_avg", 1.0)
    review_ease = 100.0 - min(review_floor, 100.0)
    velocity_ease = 100.0 - min(velocity * 25.0, 100.0)
    completeness_gap = (1.0 - min(completeness, 1.0)) * 100.0
    score = _clamp(
        (demand * 0.20)
        + (review_ease * 0.40)
        + (velocity_ease * 0.20)
        + (completeness_gap * 0.20)
    )
    return StrategyProjection(
        strategy_id="gbp_blitz",
        score=round(score, 2),
        evidence={
            "top3_review_count_min": row.get("top3_review_count_min"),
            "top3_review_velocity_avg": row.get("top3_review_velocity_avg"),
            "gbp_completeness_avg": row.get("gbp_completeness_avg"),
        },
        warnings=_warnings(row),
    )


def project_keyword_hijack(row: dict[str, Any]) -> StrategyProjection:
    if row.get("search_volume_monthly") is None:
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"search_volume_monthly": None},
            warnings=_warnings(row, "primary_keyword_volume_missing"),
        )
    if row.get("local_pack_present") is None:
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"local_pack_present": None},
            warnings=_warnings(row, "local_pack_presence_missing"),
        )
    if row.get("exact_match_name_taken") is None:
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"exact_match_name_available": None},
            warnings=_warnings(row, "exact_match_gbp_name_availability_missing"),
        )

    volume = _number_or_default(row, "search_volume_monthly", 0.0)
    if volume < 200:
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"search_volume_monthly": volume},
            warnings=_warnings(row, "primary_keyword_volume_below_200"),
        )
    if not row.get("local_pack_present", False):
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"local_pack_present": False},
            warnings=_warnings(row, "no_local_pack_detected"),
        )
    if row.get("exact_match_name_taken", False):
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"exact_match_name_available": False},
            warnings=_warnings(row, "exact_match_gbp_name_taken"),
        )
    volume_score = min(volume / 300.0, 1.0) * 45.0
    cpc_score = min(_number_or_default(row, "cpc_usd", 0.0) / 50.0, 1.0) * 30.0
    intent_score = min(_number_or_default(row, "commercial_intent_score", 0.5), 1.0) * 25.0
    return StrategyProjection(
        strategy_id="keyword_hijack",
        score=round(_clamp(volume_score + cpc_score + intent_score), 2),
        evidence={
            "search_volume_monthly": volume,
            "cpc_usd": row.get("cpc_usd"),
            "local_pack_present": True,
            "exact_match_name_available": True,
        },
        warnings=_warnings(row),
    )


def project_expand_conquer(row: dict[str, Any]) -> StrategyProjection:
    if (
        row.get("reference_city_id")
        and row.get("cbsa_code")
        and str(row.get("reference_city_id")) == str(row.get("cbsa_code"))
    ):
        return StrategyProjection(
            strategy_id="expand_conquer",
            score=0.0,
            evidence={
                "cbsa_code": row.get("cbsa_code"),
                "reference_city_id": row.get("reference_city_id"),
            },
            warnings=_warnings(row, "reference_city_not_candidate"),
        )

    similarity_raw = row.get("similarity_score")
    if similarity_raw is None:
        return StrategyProjection(
            strategy_id="expand_conquer",
            score=0.0,
            evidence={"similarity_score": None},
            warnings=_warnings(row, "feature_vector_similarity_missing"),
        )

    competition_keys = (
        "organic_difficulty",
        "reference_organic_difficulty",
        "local_difficulty",
        "reference_local_difficulty",
    )
    if any(row.get(key) is None for key in competition_keys):
        return StrategyProjection(
            strategy_id="expand_conquer",
            score=0.0,
            evidence={key: row.get(key) for key in competition_keys},
            warnings=_warnings(row, "competition_baseline_missing"),
        )

    similarity = _finite_number(row, "similarity_score")
    similarity_pct = _clamp(similarity * 100.0 if similarity <= 1 else similarity)
    organic = _finite_number(row, "organic_difficulty")
    reference_organic = _finite_number(row, "reference_organic_difficulty")
    local = _finite_number(row, "local_difficulty")
    reference_local = _finite_number(row, "reference_local_difficulty")
    if organic > reference_organic or local > reference_local:
        return StrategyProjection(
            strategy_id="expand_conquer",
            score=0.0,
            evidence={
                "similarity_score": similarity_raw,
                "organic_difficulty": organic,
                "reference_organic_difficulty": reference_organic,
                "local_difficulty": local,
                "reference_local_difficulty": reference_local,
            },
            warnings=_warnings(row, "competition_higher_than_reference"),
        )

    competition_margin = _clamp(
        ((reference_organic - organic) + (reference_local - local)) / 2.0
    )
    score = _clamp((similarity_pct * 0.75) + (competition_margin * 0.25))
    return StrategyProjection(
        strategy_id="expand_conquer",
        score=round(score, 2),
        evidence={
            "similarity_score": similarity_raw,
            "organic_difficulty": organic,
            "reference_organic_difficulty": reference_organic,
            "local_difficulty": local,
            "reference_local_difficulty": reference_local,
        },
        warnings=_warnings(row),
    )


def project_ai_resilience_warning(row: dict[str, Any]) -> dict[str, str] | None:
    try:
        aio_rate = _number_or_default(row, "aio_trigger_rate", 0.0)
        score = _number_or_default(row, "ai_resilience", 100.0)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(aio_rate) or not math.isfinite(score):
        return None
    if aio_rate >= 0.15 or score < 65:
        return {
            "code": "ai_resilience_risk",
            "severity": "warning",
            "message": "AI Overview exposure is elevated for this market.",
        }
    return None
