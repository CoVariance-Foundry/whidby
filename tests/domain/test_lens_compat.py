"""Tests for legacy strategy_profile -> lens mapping."""

from src.domain.lens_compat import resolve_lens_id, resolve_lens


def test_balanced_maps_to_balanced():
    assert resolve_lens_id("balanced") == "balanced"


def test_organic_first_maps_to_easy_win():
    assert resolve_lens_id("organic_first") == "easy_win"


def test_local_dominant_maps_to_gbp_blitz():
    assert resolve_lens_id("local_dominant") == "gbp_blitz"


def test_unknown_profile_passes_through():
    assert resolve_lens_id("ai_proof") == "ai_proof"


def test_resolve_lens_returns_lens_object():
    lens = resolve_lens("balanced")
    assert lens.lens_id == "balanced"


def test_resolve_lens_with_legacy_name():
    lens = resolve_lens("organic_first")
    assert lens.lens_id == "easy_win"
