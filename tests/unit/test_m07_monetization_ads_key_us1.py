"""Regression: SERP-derived ads key must affect monetization active_market term."""

from src.scoring.monetization_score import compute_monetization_score
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_ads_top_present_contributes_to_monetization_score() -> None:
    with_ads = metro_signal(ads_top_present=True, ads_present=False, lsa_present=False)
    without_ads = metro_signal(ads_top_present=False, ads_present=False, lsa_present=False)
    assert compute_monetization_score(with_ads) > compute_monetization_score(without_ads)


def test_legacy_ads_present_still_contributes() -> None:
    with_legacy = metro_signal(ads_top_present=False, ads_present=True, lsa_present=False)
    without = metro_signal(ads_top_present=False, ads_present=False, lsa_present=False)
    assert compute_monetization_score(with_legacy) > compute_monetization_score(without)


def test_ads_top_present_and_ads_present_produce_equivalent_scores() -> None:
    base = metro_signal(lsa_present=False, ads_top_present=False, ads_present=False)
    via_canonical = dict(base, ads_top_present=True, ads_present=False)
    via_legacy = dict(base, ads_top_present=False, ads_present=True)
    assert compute_monetization_score(via_canonical) == compute_monetization_score(via_legacy)
