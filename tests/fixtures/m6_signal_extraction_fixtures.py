"""Fixtures for M6 signal extraction unit tests.

Data and dry-run helpers live in ``src.pipeline.dry_run_fixtures`` so they
ship with the Docker image. This module re-exports everything for backward
compatibility with existing test imports.
"""

from __future__ import annotations

from copy import deepcopy

from src.pipeline.dry_run_fixtures import (
    SAMPLE_KEYWORD_EXPANSION,
    SAMPLE_RAW_METRO_BUNDLE,
    fixture_keyword_expansion,
    fixture_metro_signals,
)

__all__ = [
    "SAMPLE_KEYWORD_EXPANSION",
    "SAMPLE_RAW_METRO_BUNDLE",
    "NO_LOCAL_PACK_RAW_METRO_BUNDLE",
    "build_sample_bundle",
    "build_no_local_pack_bundle",
    "build_keyword_expansion",
    "fixture_metro_signals",
    "fixture_keyword_expansion",
]

NO_LOCAL_PACK_RAW_METRO_BUNDLE = {
    **SAMPLE_RAW_METRO_BUNDLE,
    "serp_organic": [
        {
            "keyword": "plumber near me",
            "aio_present": False,
            "serp_features": [],
            "paa_count": 0,
            "organic_results": [{"url": "https://localplumbingco.com", "domain": "localplumbingco.com"}],
        }
    ],
    "serp_maps": [],
    "google_reviews": [],
    "gbp_info": [],
}


def build_sample_bundle() -> dict:
    return deepcopy(SAMPLE_RAW_METRO_BUNDLE)


def build_no_local_pack_bundle() -> dict:
    return deepcopy(NO_LOCAL_PACK_RAW_METRO_BUNDLE)


def build_keyword_expansion() -> list[dict]:
    return deepcopy(SAMPLE_KEYWORD_EXPANSION)
