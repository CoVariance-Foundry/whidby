from src.domain.lenses import (
    BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
    BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER, SEASONAL_ARBITRAGE,
    LENS_REGISTRY, get_lens, available_lenses,
)


ALL_LENSES = [
    BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
    BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER, SEASONAL_ARBITRAGE,
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
    assert len(LENS_REGISTRY) == 9
    for lens in ALL_LENSES:
        assert lens.lens_id in LENS_REGISTRY


def test_get_lens_returns_correct_lens():
    assert get_lens("easy_win").lens_id == "easy_win"


def test_get_lens_falls_back_to_balanced():
    lens = get_lens("nonexistent")
    assert lens.lens_id == "balanced"


def test_available_lenses_returns_all():
    assert len(available_lenses()) == 9


def test_required_signals_are_frozenset():
    for lens in ALL_LENSES:
        assert isinstance(lens.required_signals, frozenset)
