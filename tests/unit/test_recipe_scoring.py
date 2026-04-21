"""Tests for opportunity_score composite formula."""

from __future__ import annotations

import math

import pytest

from src.research_agent.recipes.scoring import (
    OPPORTUNITY_COMPONENTS,
    OPPORTUNITY_WEIGHTS,
    opportunity_score,
)


def _market(
    search_volume: int | None = 10000,
    avg_competitor_da: float | None = 40.0,
    avg_backlink_strength: float | None = 500.0,
    gmb_saturation: float | None = 3.0,
    cpc_value: float | None = 5.0,
) -> dict:
    return {
        "search_volume": search_volume,
        "avg_competitor_da": avg_competitor_da,
        "avg_backlink_strength": avg_backlink_strength,
        "gmb_saturation": gmb_saturation,
        "cpc_value": cpc_value,
    }


class TestWeights:
    def test_weights_sum_to_one(self) -> None:
        total = sum(OPPORTUNITY_WEIGHTS.values())
        assert math.isclose(total, 1.0, abs_tol=1e-9)

    def test_weight_keys(self) -> None:
        assert set(OPPORTUNITY_WEIGHTS.keys()) == {
            "search_volume",
            "avg_competitor_da",
            "avg_backlink_strength",
            "gmb_saturation",
            "cpc_value",
        }

    def test_components_tuple_ordered_and_complete(self) -> None:
        assert OPPORTUNITY_COMPONENTS == (
            "search_volume_norm",
            "inverse_avg_competitor_da",
            "inverse_avg_backlink_strength",
            "inverse_gmb_saturation",
            "cpc_value_norm",
        )


class TestSingleMarketBatch:
    def test_all_factors_present_scores_neutral_half(self) -> None:
        market = _market()
        result = opportunity_score(market, [market])

        # single-market batch -> each factor normalizes to 0.5 neutral.
        # For inverse factors: 1 - 0.5 = 0.5.
        # Composite: 0.30*0.5 + 0.25*0.5 + 0.20*0.5 + 0.15*0.5 + 0.10*0.5 = 0.5
        assert math.isclose(result["score"], 0.5, abs_tol=1e-9)

    def test_components_all_present(self) -> None:
        market = _market()
        result = opportunity_score(market, [market])
        assert set(result["components"].keys()) == set(OPPORTUNITY_COMPONENTS)

    def test_weights_returned_for_audit(self) -> None:
        market = _market()
        result = opportunity_score(market, [market])
        assert result["weights"] == OPPORTUNITY_WEIGHTS


class TestTwoMarketBatch:
    def test_better_market_scores_higher(self) -> None:
        # high_opp: big volume, low competition, low backlinks, low GMB,
        # higher CPC -> should score clearly higher.
        high_opp = _market(
            search_volume=50000,
            avg_competitor_da=20.0,
            avg_backlink_strength=100.0,
            gmb_saturation=1.0,
            cpc_value=10.0,
        )
        low_opp = _market(
            search_volume=1000,
            avg_competitor_da=80.0,
            avg_backlink_strength=5000.0,
            gmb_saturation=20.0,
            cpc_value=1.0,
        )
        batch = [high_opp, low_opp]

        high_result = opportunity_score(high_opp, batch)
        low_result = opportunity_score(low_opp, batch)

        assert high_result["score"] > low_result["score"]
        # With two markets fully separated on every axis the higher one
        # should saturate near 1.0 and the lower near 0.0.
        assert math.isclose(high_result["score"], 1.0, abs_tol=1e-9)
        assert math.isclose(low_result["score"], 0.0, abs_tol=1e-9)

    def test_score_in_unit_interval(self) -> None:
        a = _market(search_volume=10000, avg_competitor_da=35.0)
        b = _market(search_volume=20000, avg_competitor_da=55.0)
        for m in (a, b):
            res = opportunity_score(m, [a, b])
            assert 0.0 <= res["score"] <= 1.0

    def test_identical_markets_both_neutral(self) -> None:
        m = _market()
        other = dict(m)
        batch = [m, other]
        res = opportunity_score(m, batch)
        # max == min on every axis -> each factor is 0.5 -> score = 0.5
        assert math.isclose(res["score"], 0.5, abs_tol=1e-9)


class TestMissingFields:
    def test_none_search_volume_still_in_unit_interval(self) -> None:
        a = _market(search_volume=None)
        b = _market(search_volume=20000)
        res = opportunity_score(a, [a, b])
        assert 0.0 <= res["score"] <= 1.0

    def test_none_contributes_zero_and_rescales_weights(self) -> None:
        # If every field is None except one present neutral factor, the score
        # should equal that factor (since remaining weights rescale to 1).
        market = {
            "search_volume": None,
            "avg_competitor_da": 40.0,
            "avg_backlink_strength": None,
            "gmb_saturation": None,
            "cpc_value": None,
        }
        other = {
            "search_volume": None,
            "avg_competitor_da": 40.0,
            "avg_backlink_strength": None,
            "gmb_saturation": None,
            "cpc_value": None,
        }
        res = opportunity_score(market, [market, other])
        # Only avg_competitor_da present; max == min => neutral 0.5;
        # inverse: 1 - 0.5 = 0.5. All remaining weight goes here -> score 0.5.
        assert math.isclose(res["score"], 0.5, abs_tol=1e-9)

    def test_all_fields_none_scores_zero(self) -> None:
        empty = {
            "search_volume": None,
            "avg_competitor_da": None,
            "avg_backlink_strength": None,
            "gmb_saturation": None,
            "cpc_value": None,
        }
        res = opportunity_score(empty, [empty])
        # No present weight to rescale; score defaults to 0.0.
        assert res["score"] == 0.0

    def test_components_report_none_or_zero_for_missing(self) -> None:
        market = _market(search_volume=None)
        other = _market(search_volume=20000)
        res = opportunity_score(market, [market, other])
        # Missing factor contributes 0 to the composite; component value
        # should be 0 (or equivalent) for that field.
        assert res["components"]["search_volume_norm"] == 0.0


class TestComponentValues:
    def test_min_normalizes_to_zero_max_to_one(self) -> None:
        lo = _market(
            search_volume=1000,
            avg_competitor_da=20.0,
            avg_backlink_strength=100.0,
            gmb_saturation=1.0,
            cpc_value=1.0,
        )
        hi = _market(
            search_volume=50000,
            avg_competitor_da=80.0,
            avg_backlink_strength=5000.0,
            gmb_saturation=20.0,
            cpc_value=10.0,
        )
        batch = [lo, hi]

        lo_res = opportunity_score(lo, batch)
        hi_res = opportunity_score(hi, batch)

        # Direct factors: hi is max (1.0), lo is min (0.0)
        assert math.isclose(hi_res["components"]["search_volume_norm"], 1.0)
        assert math.isclose(lo_res["components"]["search_volume_norm"], 0.0)
        assert math.isclose(hi_res["components"]["cpc_value_norm"], 1.0)
        assert math.isclose(lo_res["components"]["cpc_value_norm"], 0.0)

        # Inverse factors: hi has the WORST (highest) raw value -> inverse 0.0;
        # lo has the BEST (lowest) raw value -> inverse 1.0.
        assert math.isclose(
            hi_res["components"]["inverse_avg_competitor_da"], 0.0
        )
        assert math.isclose(
            lo_res["components"]["inverse_avg_competitor_da"], 1.0
        )
        assert math.isclose(
            hi_res["components"]["inverse_avg_backlink_strength"], 0.0
        )
        assert math.isclose(
            lo_res["components"]["inverse_avg_backlink_strength"], 1.0
        )
        assert math.isclose(
            hi_res["components"]["inverse_gmb_saturation"], 0.0
        )
        assert math.isclose(
            lo_res["components"]["inverse_gmb_saturation"], 1.0
        )


class TestTypeContract:
    def test_returns_dict_with_expected_keys(self) -> None:
        market = _market()
        res = opportunity_score(market, [market])
        assert set(res.keys()) == {"score", "components", "weights"}
        assert isinstance(res["score"], float)
        assert isinstance(res["components"], dict)
        assert isinstance(res["weights"], dict)

    def test_batch_must_contain_market(self) -> None:
        # A market not in the batch is still allowed (caller might be probing),
        # normalize against batch range. Just ensure no crash.
        a = _market(search_volume=5000)
        b = _market(search_volume=10000)
        probe = _market(search_volume=7500)
        res = opportunity_score(probe, [a, b])
        assert 0.0 <= res["score"] <= 1.0

    def test_empty_batch_raises(self) -> None:
        with pytest.raises(ValueError, match="batch"):
            opportunity_score(_market(), [])
