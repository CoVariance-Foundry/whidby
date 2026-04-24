"""Normalize raw DataForSEO API responses into flat row format.

The DFS API returns nested structures (wrapper dict with `items[]` sub-array).
The M6 extractors expect flat rows with top-level scalar fields. These
normalizers bridge that gap, following the same pattern as
`serp_parser._parse_dfs_items_row` and `demand_signals._normalize_keyword_rows`.
"""
from __future__ import annotations


def _extract_rating(rating_obj: object) -> tuple[float, int]:
    """Extract (value, votes_count) from a DFS rating object or scalar."""
    if isinstance(rating_obj, dict):
        value = float(rating_obj.get("value", 0) or 0)
        votes = int(rating_obj.get("votes_count", 0) or 0)
        return value, votes
    if isinstance(rating_obj, (int, float)):
        return float(rating_obj), 0
    return 0.0, 0


def normalize_serp_maps_rows(raw_rows: list[dict]) -> list[dict]:
    """Flatten DFS Maps SERP responses into per-business rows.

    DFS returns: [{"keyword": ..., "items": [{"rating": {"value": 4.5, "votes_count": 80}, ...}]}]
    Extractor expects: [{"rating": 4.5, "review_count": 80, ...}]
    """
    flat: list[dict] = []
    for row in raw_rows:
        items = row.get("items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                rating_val, votes = _extract_rating(item.get("rating"))
                flat.append({
                    **item,
                    "rating": rating_val,
                    "review_count": votes,
                })
        else:
            flat.append(row)
    return flat


def normalize_google_reviews_rows(raw_rows: list[dict]) -> list[dict]:
    """Flatten DFS Google Reviews responses into per-business rows.

    DFS returns one result per business with aggregate rating at the top level
    and individual reviews in ``items[]``. The extractor needs a single row per
    business with: rating (float), review_count (int), review_timestamps (list[str]).
    """
    flat: list[dict] = []
    for row in raw_rows:
        items = row.get("items")
        if isinstance(items, list) or "reviews_count" in row:
            rating_val, votes = _extract_rating(row.get("rating"))
            review_count = int(row.get("reviews_count", votes) or votes)

            timestamps: list[str] = []
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    ts = item.get("timestamp")
                    if ts:
                        timestamps.append(str(ts))

            flat.append({
                **{k: v for k, v in row.items() if k not in ("items", "rating")},
                "rating": rating_val,
                "review_count": review_count,
                "review_timestamps": timestamps,
            })
        elif "review_timestamps" in row:
            flat.append(row)
        else:
            flat.append(row)
    return flat


def normalize_gbp_info_rows(raw_rows: list[dict]) -> list[dict]:
    """Flatten DFS My Business Info responses into GBP profile rows.

    DFS returns: items[] with ``phone``, ``url``, ``work_time``, ``total_photos``,
    ``category``, ``additional_categories``, ``attributes``.
    Extractor expects: ``phone``, ``hours``, ``website``, ``photos``, ``description``,
    ``services``, ``attributes``, ``photo_count``, ``has_recent_post``.
    """
    flat: list[dict] = []
    for row in raw_rows:
        items = row.get("items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                flat.append(_map_gbp_item(item))
        elif "phone" in row and ("hours" in row or "website" in row):
            flat.append(row)
        else:
            flat.append(row)
    return flat


def _map_gbp_item(item: dict) -> dict:
    """Map a single DFS business info item to the extractor contract."""
    work_time = item.get("work_time")
    has_hours = False
    if isinstance(work_time, dict):
        timetable = work_time.get("work_hours", {})
        if isinstance(timetable, dict):
            has_hours = bool(timetable.get("timetable"))

    total_photos = int(item.get("total_photos", 0) or 0)

    categories: list[str] = []
    cat = item.get("category")
    if cat:
        categories.append(str(cat))
    for extra in item.get("additional_categories", []) or []:
        if extra:
            categories.append(str(extra))

    raw_attrs = item.get("attributes", {})
    attr_list: list[str] = []
    if isinstance(raw_attrs, dict):
        for attr in raw_attrs.get("available_attributes", []) or []:
            if isinstance(attr, dict):
                name = attr.get("attribute", "")
                if name:
                    attr_list.append(str(name))
    elif isinstance(raw_attrs, list):
        attr_list = [str(a) for a in raw_attrs if a]

    return {
        **item,
        "phone": str(item.get("phone", "") or ""),
        "hours": has_hours,
        "website": str(item.get("url", "") or ""),
        "photos": (
            [item.get("main_image")]
            if item.get("main_image")
            else (["photo"] * total_photos if total_photos else [])
        ),
        "description": str(item.get("description", "") or ""),
        "services": categories,
        "attributes": attr_list,
        "photo_count": total_photos,
        "has_recent_post": False,
    }


def normalize_business_listings_rows(raw_rows: list[dict]) -> list[dict]:
    """Flatten DFS Business Listings responses into per-business rows.

    DFS has no ``nap_consistency`` field. We compute it from the presence of
    name (title), address, and phone -- the three NAP components.
    """
    flat: list[dict] = []
    for row in raw_rows:
        items = row.get("items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                rating_val, votes = _extract_rating(item.get("rating"))
                nap = _compute_nap_consistency(item)
                flat.append({
                    **item,
                    "rating": rating_val,
                    "review_count": votes,
                    "nap_consistency": nap,
                })
        elif "nap_consistency" in row or "citation_consistency" in row:
            flat.append(row)
        else:
            flat.append(row)
    return flat


def _compute_nap_consistency(listing: dict) -> float:
    """Compute NAP (Name, Address, Phone) consistency score.

    Returns fraction of the three core NAP signals that are present:
    - Name (title): always present in a listing
    - Address: non-empty address string
    - Phone: non-empty phone string
    """
    signals = 3
    present = 0
    if listing.get("title"):
        present += 1
    if listing.get("address") or (
        isinstance(listing.get("address_info"), dict)
        and listing["address_info"].get("address")
    ):
        present += 1
    if listing.get("phone"):
        present += 1
    return round(present / signals, 4)
