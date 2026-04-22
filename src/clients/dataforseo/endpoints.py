"""DataForSEO endpoint definitions. (Algo Spec V1.1, §14)

Each endpoint is defined by its path, queue mode, and approximate cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QueueMode(Enum):
    STANDARD = "standard"
    LIVE = "live"


@dataclass(frozen=True)
class Endpoint:
    post_path: str
    get_path: str | None  # None for live endpoints
    mode: QueueMode
    cost_per_call: float

    @property
    def is_live(self) -> bool:
        return self.mode == QueueMode.LIVE


# --- Core endpoints used by V1.1 ---

SERP_ORGANIC = Endpoint(
    post_path="serp/google/organic/live/advanced",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.002,
)

SERP_MAPS = Endpoint(
    post_path="serp/google/maps/live/advanced",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.002,
)

SERP_ORGANIC_QUEUED = Endpoint(
    post_path="serp/google/organic/task_post",
    get_path="serp/google/organic/task_get/advanced/{task_id}",
    mode=QueueMode.STANDARD,
    cost_per_call=0.0006,
)

SERP_MAPS_QUEUED = Endpoint(
    post_path="serp/google/maps/task_post",
    get_path="serp/google/maps/task_get/advanced/{task_id}",
    mode=QueueMode.STANDARD,
    cost_per_call=0.0006,
)

KEYWORD_VOLUME = Endpoint(
    post_path="keywords_data/google/search_volume/task_post",
    get_path="keywords_data/google/search_volume/task_get/{task_id}",
    mode=QueueMode.STANDARD,
    cost_per_call=0.05,
)

KEYWORD_SUGGESTIONS = Endpoint(
    post_path="dataforseo_labs/google/keyword_suggestions/live",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.05,
)

BUSINESS_LISTINGS = Endpoint(
    post_path="business_data/business_listings/search/live",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.01,
)

GOOGLE_MY_BUSINESS_INFO = Endpoint(
    post_path="business_data/google/my_business_info/live",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.004,
)

GOOGLE_REVIEWS = Endpoint(
    post_path="business_data/google/reviews/task_post",
    get_path="business_data/google/reviews/task_get/{task_id}",
    mode=QueueMode.STANDARD,
    cost_per_call=0.005,
)

BACKLINKS_SUMMARY = Endpoint(
    post_path="backlinks/summary/live",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.002,
)

LIGHTHOUSE = Endpoint(
    post_path="on_page/lighthouse/live",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.006,
)

LIGHTHOUSE_QUEUED = Endpoint(
    post_path="on_page/lighthouse/task_post",
    get_path="on_page/lighthouse/task_get/{task_id}",
    mode=QueueMode.STANDARD,
    cost_per_call=0.002,
)

LOCATIONS = Endpoint(
    post_path="serp/google/locations",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.0,
)
