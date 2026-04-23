"""Unit tests for backfill canonical normalization helpers."""

from scripts.backfill_kb_entities import _normalize_geo


def test_normalize_geo_matches_canonical_city_state_format() -> None:
    assert _normalize_geo("Phoenix, AZ") == "phoenix, AZ"


def test_normalize_geo_collapses_whitespace_and_upcases_state() -> None:
    assert _normalize_geo("  Macon   ,   ga ") == "macon, GA"
