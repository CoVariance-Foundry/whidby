"""Composite opportunity scoring for recipe reports.

Given a single market's raw signals and the batch of markets being compared,
``opportunity_score`` returns a 0.0-1.0 composite combining:

- search_volume (direct, higher is better)
- avg_competitor_da (inverse, lower is better)
- avg_backlink_strength (inverse, lower is better)
- gmb_saturation (inverse, lower is better)
- cpc_value (direct, higher is better - proxies monetization)

Normalization is min-max across the *batch* of markets, so scores are
relative to the comparison set. Missing (None) fields contribute 0 to the
composite, and the remaining weights are rescaled so the composite stays
in 0.0-1.0 regardless of data coverage.
"""

from __future__ import annotations

from typing import Any

OPPORTUNITY_WEIGHTS: dict[str, float] = {
    "search_volume": 0.30,
    "avg_competitor_da": 0.25,
    "avg_backlink_strength": 0.20,
    "gmb_saturation": 0.15,
    "cpc_value": 0.10,
}

OPPORTUNITY_COMPONENTS: tuple[str, ...] = (
    "search_volume_norm",
    "inverse_avg_competitor_da",
    "inverse_avg_backlink_strength",
    "inverse_gmb_saturation",
    "cpc_value_norm",
)

# Mapping of raw field name -> (component name, inverse?)
# Preserves both the ordering of OPPORTUNITY_COMPONENTS and the inversion
# semantics without duplicating the pairing in two places.
_FIELD_TO_COMPONENT: dict[str, tuple[str, bool]] = {
    "search_volume": ("search_volume_norm", False),
    "avg_competitor_da": ("inverse_avg_competitor_da", True),
    "avg_backlink_strength": ("inverse_avg_backlink_strength", True),
    "gmb_saturation": ("inverse_gmb_saturation", True),
    "cpc_value": ("cpc_value_norm", False),
}


def _min_max_norm(
    value: float,
    batch_values: list[float],
) -> float:
    """Min-max normalize *value* against *batch_values*.

    Returns 0.5 (neutral) when the batch is degenerate (single element or
    all values equal).
    """
    if not batch_values:
        return 0.5
    lo = min(batch_values)
    hi = max(batch_values)
    if hi == lo:
        return 0.5
    return (value - lo) / (hi - lo)


def opportunity_score(
    market: dict[str, Any],
    batch: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute the composite opportunity score for *market*.

    Args:
        market: Raw signal dict for the market being scored. Expected keys:
            ``search_volume`` (int|None), ``avg_competitor_da`` (float|None),
            ``avg_backlink_strength`` (float|None), ``gmb_saturation``
            (float|None), ``cpc_value`` (float|None). Missing or ``None``
            values are treated as "field not available".
        batch: The full list of market dicts being compared. Min/max
            normalization uses this batch's range. Must be non-empty.

    Returns:
        A dict with keys:

        - ``score`` (float, 0.0-1.0): the weighted composite.
        - ``components`` (dict[str, float]): each normalized factor,
          keyed by the names in :data:`OPPORTUNITY_COMPONENTS`. Inverse
          factors have already been inverted (so higher = better for all
          components). Missing factors report ``0.0``.
        - ``weights`` (dict[str, float]): the static weights for
          auditability; equal to :data:`OPPORTUNITY_WEIGHTS`.

    Normalization rules:
        1. For each raw field, scan *batch* for non-None values and take
           min/max. Normalize to 0-1.
        2. If the batch yields a degenerate range (single value or
           max == min), the factor normalizes to 0.5 (neutral).
        3. Inverse factors are flipped via ``1 - normalized`` so higher
           always means better.
        4. When a field is ``None`` for *market*, its component contributes
           0.0 to the composite AND its weight is removed from the active
           weight pool. The remaining component weights are rescaled to
           sum to 1.0 so the composite stays in 0.0-1.0. If *all* fields
           are missing, the score is 0.0.

    Raises:
        ValueError: If *batch* is empty.
    """
    if not batch:
        raise ValueError("batch must contain at least one market")

    components: dict[str, float] = {name: 0.0 for name in OPPORTUNITY_COMPONENTS}
    active_weight_total = 0.0
    raw_score = 0.0

    for field_name, (component_name, inverse) in _FIELD_TO_COMPONENT.items():
        raw_value = market.get(field_name)
        if raw_value is None:
            continue

        batch_values = [
            m[field_name]
            for m in batch
            if m.get(field_name) is not None
        ]
        if not batch_values:
            # Field is None for every market in the batch -> skip.
            continue

        normalized = _min_max_norm(float(raw_value), [float(v) for v in batch_values])
        component_value = 1.0 - normalized if inverse else normalized
        components[component_name] = component_value

        weight = OPPORTUNITY_WEIGHTS[field_name]
        raw_score += weight * component_value
        active_weight_total += weight

    if active_weight_total == 0.0:
        score = 0.0
    else:
        # Rescale so the composite stays in 0-1 when some fields are missing.
        score = raw_score / active_weight_total

    return {
        "score": score,
        "components": components,
        "weights": dict(OPPORTUNITY_WEIGHTS),
    }
