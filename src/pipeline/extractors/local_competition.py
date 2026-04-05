"""Local competition signal extraction."""

from __future__ import annotations

from src.pipeline.gbp_completeness import compute_gbp_completeness
from src.pipeline.review_velocity import compute_reviews_per_month


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def extract_local_competition_signals(
    serp_context: dict[str, object],
    serp_maps_rows: list[dict],
    google_reviews_rows: list[dict],
    gbp_info_rows: list[dict],
    business_listings_rows: list[dict],
) -> dict[str, float | bool]:
    """Build local competition signal block."""
    local_pack_present = bool(serp_context.get("local_pack_present", False))
    local_pack_position = int(serp_context.get("local_pack_position", 10) or 10)

    ratings: list[float] = []
    review_counts: list[float] = []
    velocity_values: list[float] = []

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

    return {
        "local_pack_present": local_pack_present,
        "local_pack_position": local_pack_position if local_pack_present else 10,
        "local_pack_review_count_avg": round(_avg(review_counts), 4),
        "local_pack_review_count_max": round(max(review_counts) if review_counts else 0.0, 4),
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
