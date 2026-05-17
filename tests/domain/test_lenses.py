import pytest

from src.domain.lenses import (
    BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
    KEYWORD_HIJACK, BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER,
    SEASONAL_ARBITRAGE,
    LENS_REGISTRY, get_lens, available_lenses,
)
from src.domain.entities import City, Market, Service
from src.domain.scoring import FilterNotMetError, score_market


ALL_LENSES = [
    BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
    KEYWORD_HIJACK, BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER,
    SEASONAL_ARBITRAGE,
]


def test_all_lens_weights_sum_is_valid():
    for lens in ALL_LENSES:
        total = sum(lens.weights.values())
        assert 0.90 <= total <= 1.01, (
            f"Lens '{lens.lens_id}' weights sum to {total}, expected 0.90-1.01"
        )


def test_all_lenses_have_unique_ids():
    ids = [lens.lens_id for lens in ALL_LENSES]
    assert len(ids) == len(set(ids))


def test_all_lenses_have_descriptions():
    for lens in ALL_LENSES:
        assert lens.description, f"Lens '{lens.lens_id}' has no description"


def test_balanced_lens_matches_legacy_profile_exactly():
    """BALANCED lens weights must match legacy balanced strategy profile."""
    assert BALANCED.weights == {
        "demand": 0.25,
        "organic_competition": 0.15,
        "local_competition": 0.20,
        "monetization": 0.20,
        "ai_resilience": 0.15,
    }


def test_registry_contains_all_lenses():
    assert len(LENS_REGISTRY) == 10
    for lens in ALL_LENSES:
        assert lens.lens_id in LENS_REGISTRY


def test_get_lens_returns_correct_lens():
    assert get_lens("easy_win").lens_id == "easy_win"


def test_get_lens_falls_back_to_balanced():
    lens = get_lens("nonexistent")
    assert lens.lens_id == "balanced"


def test_available_lenses_returns_all():
    ids = [lens.lens_id for lens in available_lenses()]
    assert ids == [
        "balanced",
        "easy_win",
        "gbp_blitz",
        "keyword_hijack",
        "expand_conquer",
    ]


def test_cash_cow_stays_registered_as_phase_2():
    assert LENS_REGISTRY["cash_cow"].phase == "phase_2"
    assert get_lens("cash_cow").lens_id == "cash_cow"


def test_keyword_hijack_requires_raw_gate_fields_to_score():
    market = Market(
        city=City(city_id="boise-id", name="Boise", state="ID"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals={
            "demand": {"score": 90.0},
            "monetization": {"score": 85.0},
            "gbp": {"score": 80.0},
            "commercial_intent": {"score": 90.0},
        },
    )
    with pytest.raises(FilterNotMetError):
        score_market(market, KEYWORD_HIJACK)


def test_required_signals_are_frozenset():
    for lens in ALL_LENSES:
        assert isinstance(lens.required_signals, frozenset)
