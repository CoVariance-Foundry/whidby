"""Unit tests for canonical key resolution."""

from __future__ import annotations

from src.pipeline.canonical_key import (
    CanonicalKey,
    normalize_geo,
    normalize_niche,
    resolve_canonical_key,
)


def test_normalize_niche_strips_service_suffixes() -> None:
    assert normalize_niche("Roofing Services") == "roofing"
    assert normalize_niche("water damage restoration company") == "water damage restoration"
    assert normalize_niche("PEST CONTROL near me") == "pest control"


def test_normalize_niche_collapses_whitespace() -> None:
    assert normalize_niche("  plumbing    repair  ") == "plumbing repair"


def test_normalize_niche_preserves_core_term() -> None:
    assert normalize_niche("roofing") == "roofing"


def test_normalize_geo_parses_city_state() -> None:
    assert normalize_geo("Phoenix", "AZ") == "phoenix, AZ"
    assert normalize_geo("Phoenix, AZ") == "phoenix, AZ"


def test_normalize_geo_handles_missing_state() -> None:
    assert normalize_geo("Paris") == "paris"


def test_normalize_geo_extracts_state_from_city_comma() -> None:
    result = normalize_geo("Austin, TX")
    assert result == "austin, TX"


def test_resolve_canonical_key_returns_frozen_dataclass() -> None:
    key = resolve_canonical_key(niche="roofing", city="Phoenix", state="AZ")
    assert isinstance(key, CanonicalKey)
    assert key.niche_normalized == "roofing"
    assert key.geo_normalized == "phoenix, AZ"
    assert key.geo_scope == "city"


def test_canonical_key_deterministic_input_hash() -> None:
    k1 = resolve_canonical_key(niche="Roofing", city="Phoenix", state="AZ")
    k2 = resolve_canonical_key(niche="roofing", city="Phoenix, AZ")
    assert k1.input_hash("balanced") == k2.input_hash("balanced")


def test_canonical_key_hash_changes_with_strategy() -> None:
    key = resolve_canonical_key(niche="roofing", city="Phoenix", state="AZ")
    assert key.input_hash("balanced") != key.input_hash("organic_first")


def test_resolve_canonical_key_with_place_id() -> None:
    key = resolve_canonical_key(
        niche="plumbing",
        city="Paris",
        place_id="place.123",
        dataforseo_location_code=98765,
    )
    assert key.place_id == "place.123"
    assert key.dataforseo_location_code == 98765


def test_different_niches_different_keys() -> None:
    k1 = resolve_canonical_key(niche="roofing", city="Phoenix", state="AZ")
    k2 = resolve_canonical_key(niche="plumbing", city="Phoenix", state="AZ")
    assert k1.niche_normalized != k2.niche_normalized
    assert k1.input_hash("balanced") != k2.input_hash("balanced")
