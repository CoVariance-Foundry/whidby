"""Map legacy strategy_profile names to ScoringLens objects."""

from __future__ import annotations

from src.domain.lenses import ScoringLens, get_lens

LEGACY_PROFILE_TO_LENS: dict[str, str] = {
    "balanced": "balanced",
    "organic_first": "easy_win",
    "local_dominant": "gbp_blitz",
}


def resolve_lens_id(strategy_profile: str) -> str:
    """Map a legacy strategy_profile name to a lens_id."""
    return LEGACY_PROFILE_TO_LENS.get(strategy_profile, strategy_profile)


def resolve_lens(strategy_profile: str) -> ScoringLens:
    """Resolve a strategy_profile string to a ScoringLens object."""
    return get_lens(resolve_lens_id(strategy_profile))
