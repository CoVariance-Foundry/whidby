"""Region-to-state definitions for geo scope expansion. (Algo Spec V1.1, §3.3)"""

from src.config.constants import REGIONS


def states_for_region(region: str) -> list[str]:
    """Return state codes belonging to the named region.

    Raises:
        ValueError: If the region name is not recognised.
    """
    if region not in REGIONS:
        raise ValueError(
            f"Unknown region '{region}'. Valid regions: {', '.join(sorted(REGIONS))}"
        )
    return REGIONS[region]
