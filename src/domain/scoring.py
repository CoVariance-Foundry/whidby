"""Score computation: apply a ScoringLens to a Market's pre-computed signals.

Bridges the domain model (Market, ScoringLens) to the scoring engine in
src/scoring/composite_score.py. Component scores must be pre-computed and
stored in Market.signals as {component_name: {"score": float, ...}}.
"""

from __future__ import annotations

from typing import Any

from src.domain.entities import Market, ScoredMarket
from src.domain.lenses import ScoringLens
from src.scoring.composite_score import compute_opportunity_score


class MissingSignalsError(Exception):
    """Market doesn't have the signals required by this lens."""


class FilterNotMetError(Exception):
    """Market doesn't meet a lens's filter pre-conditions."""


def score_market(market: Market, lens: ScoringLens) -> ScoredMarket:
    """Apply a ScoringLens to a Market's pre-computed component scores."""
    component_scores = _extract_component_scores(market.signals, lens)

    missing = lens.required_signals - set(component_scores.keys())
    if missing:
        raise MissingSignalsError(
            f"Lens '{lens.lens_id}' requires {missing} "
            f"but market only has {set(component_scores.keys())}"
        )

    _check_filters(market, lens)

    opportunity = compute_opportunity_score(
        component_scores=component_scores,
        weights=lens.weights,
    )

    score_breakdown = {
        name: component_scores.get(name, 0.0) * weight
        for name, weight in lens.weights.items()
    }

    return ScoredMarket(
        market=market,
        opportunity_score=opportunity,
        lens_id=lens.lens_id,
        score_breakdown=score_breakdown,
    )


def score_markets_batch(
    markets: list[Market],
    lens: ScoringLens,
) -> list[ScoredMarket]:
    """Score multiple markets, sort by opportunity, assign ranks."""
    scored: list[ScoredMarket] = []
    for market in markets:
        try:
            result = score_market(market, lens)
            scored.append(result)
        except (MissingSignalsError, FilterNotMetError):
            continue

    scored.sort(key=lambda s: s.opportunity_score, reverse=lens.sort_descending)

    return [
        ScoredMarket(
            market=s.market,
            opportunity_score=s.opportunity_score,
            lens_id=s.lens_id,
            rank=i + 1,
            score_breakdown=s.score_breakdown,
        )
        for i, s in enumerate(scored)
    ]


def _extract_component_scores(
    signals: dict[str, dict[str, Any]],
    lens: ScoringLens,
) -> dict[str, float]:
    """Extract component scores from Market.signals for all lens-referenced keys."""
    all_keys = set(lens.weights.keys()) | lens.required_signals
    scores: dict[str, float] = {}
    for key in all_keys:
        bundle = signals.get(key)
        if bundle is None:
            continue
        if isinstance(bundle, dict):
            score = bundle.get("score")
            if score is not None:
                scores[key] = float(score)
        elif isinstance(bundle, (int, float)):
            scores[key] = float(bundle)
    return scores


def _check_filters(market: Market, lens: ScoringLens) -> None:
    """Evaluate all lens filters against the market's signals and attributes."""
    for f in lens.filters:
        value = _extract_filter_value(market, f.signal)
        if value is None:
            continue
        if not _evaluate_filter(value, f.operator, f.value):
            raise FilterNotMetError(
                f"Lens '{lens.lens_id}' filter failed: "
                f"{f.signal} {f.operator} {f.value} (actual: {value})"
            )


def _extract_filter_value(market: Market, signal_name: str) -> float | None:
    """Search market signals and attributes for a filter value."""
    for bundle in market.signals.values():
        if isinstance(bundle, dict) and signal_name in bundle:
            val = bundle[signal_name]
            if isinstance(val, (int, float)):
                return float(val)

    if hasattr(market.service, signal_name):
        val = getattr(market.service, signal_name)
        if val is not None:
            return float(val)

    direct = market.signals.get(signal_name)
    if isinstance(direct, (int, float)):
        return float(direct)
    if isinstance(direct, dict) and "value" in direct:
        return float(direct["value"])

    return None


def _evaluate_filter(value: float, operator: str, threshold: Any) -> bool:
    ops = {
        ">": lambda v, t: v > t,
        "<": lambda v, t: v < t,
        ">=": lambda v, t: v >= t,
        "<=": lambda v, t: v <= t,
        "=": lambda v, t: v == t,
        "!=": lambda v, t: v != t,
    }
    op_fn = ops.get(operator)
    if op_fn is None:
        raise ValueError(f"Unknown filter operator: {operator}")
    return op_fn(value, threshold)
