"""Pure metric formulas for Explore Cities data population."""

from collections.abc import Mapping, Sequence
from typing import Any


def weighted_establishments(
    cbp_rows: Sequence[Mapping[str, Any]],
    weights_by_naics: Mapping[str, float],
) -> float:
    """Sum CBP establishment counts after applying NAICS-specific weights."""
    total = 0.0

    for row in cbp_rows:
        naics_code = row.get("naics_code")
        if naics_code not in weights_by_naics:
            continue

        establishment_count = row.get("est")
        if establishment_count is None:
            continue

        total += float(establishment_count) * weights_by_naics[naics_code]

    return round(total, 10)


def business_density_per_1k(
    weighted_establishment_count: float,
    population: int | None,
) -> float | None:
    """Return weighted businesses per 1,000 residents, or None without population."""
    if population is None or population <= 0:
        return None

    return round((weighted_establishment_count / population) * 1000, 10)


def annualized_growth(
    latest: float | None,
    prior: float | None,
    year_span: int,
) -> float | None:
    """Return compound annual growth over the supplied span."""
    if latest is None or prior is None:
        return None
    if prior <= 0 or latest < 0 or year_span <= 0:
        return None

    growth = (latest / prior) ** (1 / year_span) - 1
    return round(growth, 10)
