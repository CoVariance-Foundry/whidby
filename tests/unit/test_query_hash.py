"""Unit tests for deterministic query hash computation."""

from __future__ import annotations

from src.clients.dataforseo.query_hash import EXCLUDED_KEYS, compute_query_hash

from tests.fixtures.observation_fixtures import (
    SAMPLE_ENDPOINT,
    SAMPLE_PARAMS,
    SAMPLE_PARAMS_REORDERED,
    SAMPLE_PARAMS_WITH_EXCLUDED,
    SAMPLE_PARAMS_WITH_NONE,
)


class TestComputeQueryHash:
    def test_returns_64_char_hex_string(self):
        h = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic_same_input_same_output(self):
        h1 = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        h2 = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        assert h1 == h2

    def test_param_order_does_not_affect_hash(self):
        h1 = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        h2 = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS_REORDERED)
        assert h1 == h2

    def test_excluded_keys_stripped_before_hashing(self):
        h_clean = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        h_with_excluded = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS_WITH_EXCLUDED)
        assert h_clean == h_with_excluded

    def test_none_values_stripped_before_hashing(self):
        h_clean = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        h_with_none = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS_WITH_NONE)
        assert h_clean == h_with_none

    def test_different_endpoint_produces_different_hash(self):
        h1 = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        h2 = compute_query_hash("serp/google/maps/task_post", SAMPLE_PARAMS)
        assert h1 != h2

    def test_different_params_produces_different_hash(self):
        h1 = compute_query_hash(SAMPLE_ENDPOINT, SAMPLE_PARAMS)
        h2 = compute_query_hash(SAMPLE_ENDPOINT, {"keyword": "electrician", "location_code": 1012873})
        assert h1 != h2

    def test_empty_params(self):
        h = compute_query_hash(SAMPLE_ENDPOINT, {})
        assert len(h) == 64

    def test_excluded_keys_frozenset_contains_expected(self):
        assert "tag" in EXCLUDED_KEYS
        assert "postback_url" in EXCLUDED_KEYS
        assert "pingback_url" in EXCLUDED_KEYS
