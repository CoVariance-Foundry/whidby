"""Review velocity calculations for local competition signals."""

from __future__ import annotations

from datetime import UTC, datetime


def _parse_timestamp(value: str | datetime) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def compute_reviews_per_month(review_timestamps: list[str | datetime]) -> float:
    """Compute average monthly review velocity from timestamps.

    Args:
        review_timestamps: Review creation timestamps.

    Returns:
        Reviews per month, rounded to 4 decimal places.
    """
    parsed = [stamp for stamp in (_parse_timestamp(item) for item in review_timestamps) if stamp]
    if not parsed:
        return 0.0
    if len(parsed) == 1:
        return 1.0

    newest = max(parsed)
    oldest = min(parsed)
    span_days = max((newest - oldest).days, 1)
    span_months = max(span_days / 30.4375, 1 / 30.4375)
    return round(len(parsed) / span_months, 4)
