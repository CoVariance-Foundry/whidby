"""Local competition signal extraction."""

from __future__ import annotations

from src.pipeline.gbp_completeness import compute_gbp_completeness
from src.pipeline.review_velocity import compute_reviews_per_month


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _number(value: object) -> float | None:
    """Return a numeric value when present and parseable."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rank_value(row: dict) -> float | None:
    """Extract the local pack rank field used for top-3 ordering."""
    for field in ("rank_group", "rank", "position", "rank_absolute"):
        value = _number(row.get(field))
        if value is not None:
            return value
    return None


def _top3_local_pack_rows(serp_maps_rows: list[dict]) -> list[dict]:
    """Return the first three local pack rows, ranked when rank data exists."""
    if any(_rank_value(row) is not None for row in serp_maps_rows):
        ordered = sorted(
            enumerate(serp_maps_rows),
            key=lambda item: (
                _rank_value(item[1]) is None,
                _rank_value(item[1]) if _rank_value(item[1]) is not None else 0.0,
                item[0],
            ),
        )
        return [row for _, row in ordered[:3]]
    return serp_maps_rows[:3]


def _review_velocity_value(row: dict) -> float | None:
    """Extract explicit review velocity fields from a local pack row."""
    for field in ("review_velocity", "reviews_per_month"):
        value = _number(row.get(field))
        if value is not None:
            return value
    return None


def _top3_review_data_confidence(count_coverage: float, velocity_coverage: float) -> str:
    """Label confidence in top-3 review signals from count and velocity coverage."""
    if count_coverage >= 0.67 and velocity_coverage >= 0.67:
        return "high"
    if count_coverage >= 0.67:
        return "medium"
    if count_coverage > 0:
        return "low"
    return "missing"


def extract_local_competition_signals(
    serp_context: dict[str, object],
    serp_maps_rows: list[dict],
    google_reviews_rows: list[dict],
    gbp_info_rows: list[dict],
    business_listings_rows: list[dict],
) -> dict[str, float | bool | str | None]:
    """Build local competition signal block."""
    local_pack_present = bool(serp_context.get("local_pack_present", False))
    local_pack_position = int(serp_context.get("local_pack_position", 10) or 10)

    ratings: list[float] = []
    review_counts: list[float] = []
    velocity_values: list[float] = []
    top3_review_counts: list[float] = []
    top3_velocity_values: list[float] = []
    top3_rows = _top3_local_pack_rows(serp_maps_rows)

    for row in top3_rows:
        review_count = _number(row.get("review_count"))
        if review_count is not None:
            top3_review_counts.append(review_count)
        review_velocity = _review_velocity_value(row)
        if review_velocity is not None:
            top3_velocity_values.append(review_velocity)

    for row in serp_maps_rows:
        ratings.append(float(row.get("rating", 0.0) or 0.0))
        review_counts.append(float(row.get("review_count", 0.0) or 0.0))

    for row in google_reviews_rows:
        rating = row.get("rating")
        if rating is not None:
            ratings.append(float(rating))
        review_count = row.get("review_count", row.get("total_reviews"))
        if review_count is not None:
            review_counts.append(float(review_count))
        velocity_values.append(compute_reviews_per_month(list(row.get("review_timestamps", []))))

    completeness_scores: list[float] = []
    photo_counts: list[float] = []
    posting_activity_hits = 0
    for row in gbp_info_rows:
        completeness_scores.append(compute_gbp_completeness(row))
        photo_counts.append(float(row.get("photo_count", 0.0) or 0.0))
        posting_activity_hits += int(bool(row.get("has_recent_post", False)))

    listing_consistency = [
        float(row.get("nap_consistency", row.get("citation_consistency", 0.0)) or 0.0)
        for row in business_listings_rows
    ]
    expected_top3_slots = 3 if local_pack_present and top3_rows else 0
    top3_review_count_coverage = (
        len(top3_review_counts) / expected_top3_slots if expected_top3_slots else 0.0
    )
    top3_review_velocity_coverage = (
        len(top3_velocity_values) / expected_top3_slots if expected_top3_slots else 0.0
    )

    return {
        "local_pack_present": local_pack_present,
        "local_pack_position": local_pack_position if local_pack_present else 10,
        "local_pack_review_count_avg": round(_avg(review_counts), 4),
        "local_pack_review_count_max": round(max(review_counts) if review_counts else 0.0, 4),
        "top3_review_count_min": (
            round(min(top3_review_counts), 4) if top3_review_counts else None
        ),
        "top3_review_velocity_avg": (
            round(_avg(top3_velocity_values), 4) if top3_velocity_values else None
        ),
        "top3_review_count_coverage": round(top3_review_count_coverage, 4),
        "top3_review_velocity_coverage": round(top3_review_velocity_coverage, 4),
        "top3_review_data_confidence": _top3_review_data_confidence(
            top3_review_count_coverage,
            top3_review_velocity_coverage,
        ),
        "local_pack_rating_avg": round(_avg(ratings), 4),
        "review_velocity_avg": round(_avg(velocity_values), 4),
        "gbp_completeness_avg": round(_avg(completeness_scores), 4),
        "gbp_photo_count_avg": round(_avg(photo_counts), 4),
        "gbp_posting_activity": round(
            posting_activity_hits / len(gbp_info_rows) if gbp_info_rows else 0.0,
            4,
        ),
        "citation_consistency": round(_avg(listing_consistency), 4),
    }
