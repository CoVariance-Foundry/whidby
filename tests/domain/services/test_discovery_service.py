"""Tests for DiscoveryService — multi-market discovery."""
from __future__ import annotations

from typing import Any

import pytest

from src.domain.entities import City, Service
from src.domain.queries import CityFilter, ServiceFilter
from src.domain.services.discovery_service import (
    _evaluate_predicate,
    _passes_city_filters,
    _passes_service_filters,
)


# --- Test data ---

BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PHOENIX = City(city_id="phoenix-az", name="Phoenix", state="AZ", population=1_600_000)
SMALL_TOWN = City(city_id="small-ks", name="Smallville", state="KS", population=45_000)

PLUMBING = Service(service_id="plumbing", name="Plumbing", fulfillment_type="physical")
WEB_DESIGN = Service(service_id="web-design", name="Web Design", fulfillment_type="remote")

FULL_SIGNALS: dict[str, dict[str, Any]] = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
    "gbp": {"score": 45.0},
}


# --- _evaluate_predicate tests ---


def test_predicate_greater_than():
    assert _evaluate_predicate(100, ">", 50) is True
    assert _evaluate_predicate(50, ">", 100) is False


def test_predicate_less_than():
    assert _evaluate_predicate(30, "<", 100) is True
    assert _evaluate_predicate(100, "<", 30) is False


def test_predicate_equality():
    assert _evaluate_predicate("physical", "=", "physical") is True
    assert _evaluate_predicate("remote", "=", "physical") is False


def test_predicate_not_equal():
    assert _evaluate_predicate("remote", "!=", "physical") is True


def test_predicate_gte_lte():
    assert _evaluate_predicate(100, ">=", 100) is True
    assert _evaluate_predicate(99, "<=", 100) is True


def test_predicate_in_operator():
    assert _evaluate_predicate("AZ", "in", ["AZ", "CA", "TX"]) is True
    assert _evaluate_predicate("ID", "in", ["AZ", "CA"]) is False


def test_predicate_like_operator():
    assert _evaluate_predicate("Growth Sunbelt", "like", "sunbelt") is True
    assert _evaluate_predicate("Growth Sunbelt", "like", "arctic") is False


def test_predicate_unknown_operator_raises():
    with pytest.raises(ValueError, match="Unknown filter operator"):
        _evaluate_predicate(1, "~", 1)


# --- Filter helper tests ---


def test_passes_city_filters_population():
    filters = [CityFilter("population", ">", 200_000)]
    assert _passes_city_filters(PHOENIX, filters) is True
    assert _passes_city_filters(SMALL_TOWN, filters) is False


def test_passes_city_filters_state_in():
    filters = [CityFilter("state", "in", ["AZ", "CA"])]
    assert _passes_city_filters(PHOENIX, filters) is True
    assert _passes_city_filters(BOISE, filters) is False


def test_passes_service_filters_fulfillment_type():
    filters = [ServiceFilter("fulfillment_type", "=", "physical")]
    assert _passes_service_filters(PLUMBING, filters) is True
    assert _passes_service_filters(WEB_DESIGN, filters) is False


def test_passes_filters_missing_field_returns_false():
    filters = [CityFilter("nonexistent_field", ">", 0)]
    assert _passes_city_filters(BOISE, filters) is False
