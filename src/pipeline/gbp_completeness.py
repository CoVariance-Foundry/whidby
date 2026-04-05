"""Google Business Profile completeness scoring."""

from __future__ import annotations


GBP_COMPLETENESS_FIELDS: tuple[str, ...] = (
    "phone",
    "hours",
    "website",
    "photos",
    "description",
    "services",
    "attributes",
)


def compute_gbp_completeness(gbp_profile: dict[str, object]) -> float:
    """Compute normalized GBP completeness score.

    Args:
        gbp_profile: GBP record with potential completeness fields.

    Returns:
        Score in range [0.0, 1.0].
    """
    if not gbp_profile:
        return 0.0

    score = 0
    for field in GBP_COMPLETENESS_FIELDS:
        value = gbp_profile.get(field)
        if isinstance(value, bool):
            score += int(value)
        elif isinstance(value, (int, float)):
            score += int(value > 0)
        elif isinstance(value, str):
            score += int(bool(value.strip()))
        elif isinstance(value, (list, tuple, set, dict)):
            score += int(len(value) > 0)

    return round(score / len(GBP_COMPLETENESS_FIELDS), 4)
