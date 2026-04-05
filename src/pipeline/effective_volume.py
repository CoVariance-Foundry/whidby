"""AIO-adjusted effective volume utility."""

from __future__ import annotations

from src.config.constants import AIO_CTR_REDUCTION, INTENT_AIO_RATES


def compute_effective_volume(
    keyword_volume: float,
    intent: str,
    aio_detected_in_serp: bool,
) -> float:
    """Compute effective search volume after AIO impact adjustment.

    Args:
        keyword_volume: Raw keyword volume.
        intent: Keyword intent.
        aio_detected_in_serp: Whether AIO was explicitly detected in SERP.

    Returns:
        AIO-adjusted effective volume.
    """
    volume = max(float(keyword_volume), 0.0)
    if aio_detected_in_serp:
        return volume * (1 - AIO_CTR_REDUCTION)

    expected_rate = INTENT_AIO_RATES.get(str(intent).lower(), 0.10)
    return volume * (1 - expected_rate * AIO_CTR_REDUCTION)
