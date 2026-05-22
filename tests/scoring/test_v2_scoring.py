"""Tests for V2 benchmark-relative scoring."""
from __future__ import annotations

from src.scoring.benchmark_repository import SeoBenchmarkCell
from src.scoring.v2 import compute_v2_scores, compute_v2_scores_with_repository


class FakeBenchmarkRepository:
    def __init__(self, cell: SeoBenchmarkCell | None) -> None:
        self.cell = cell
        self.calls: list[tuple[str, str]] = []

    def get(self, *, niche_normalized: str, population_class: str) -> SeoBenchmarkCell | None:
        self.calls.append((niche_normalized, population_class))
        return self.cell


def benchmark_cell(**overrides: object) -> SeoBenchmarkCell:
    row: dict[str, object] = {
        "niche_normalized": "plumber",
        "naics_code": "238220",
        "population_class": "metro_1m_5m",
        "p25_total_volume_per_capita": 0.001,
        "median_total_volume_per_capita": 0.002,
        "p75_total_volume_per_capita": 0.004,
        "p25_avg_cpc": 7.5,
        "median_avg_cpc": 10.0,
        "p75_avg_cpc": 15.0,
        "median_top3_review_count_min": 40,
        "median_top3_review_velocity": 3.0,
        "pct_with_local_pack": 0.8,
        "median_aggregator_count": 2.0,
        "median_local_biz_count": 5.0,
        "median_establishments_per_100k": 50.0,
        "median_lsa_present_rate": 0.25,
        "median_ads_present_rate": 0.5,
        "median_aio_trigger_rate": 0.1,
        "sample_size_metros": 12,
        "sample_size_observations": 120,
        "confidence_label": "medium",
    }
    row.update(overrides)
    return SeoBenchmarkCell.from_mapping(row)


def signal_fixture(**overrides: object) -> dict[str, object]:
    signals: dict[str, object] = {
        "population": 500_000,
        "population_class": "metro_1m_5m",
        "commercial_search_volume": 2_000,
        "total_search_volume": 2_000,
        "avg_cpc": 12.0,
        "aggregator_count": 2.0,
        "local_biz_count": 5.0,
        "avg_top5_da": 30.0,
        "avg_top5_lighthouse": 70.0,
        "top5_da_coverage": 0.8,
        "top5_lighthouse_coverage": 0.8,
        "top5_organic_data_confidence": "high",
        "local_pack_present": True,
        "top3_review_count_min": 60,
        "review_velocity_avg": 4.5,
        "cbp_establishments": 350,
        "lsa_present": True,
        "ads_present": True,
        "aio_trigger_rate": 0.08,
        "transactional_keyword_ratio": 0.7,
        "local_fulfillment_required": 1.0,
        "paa_density": 2.0,
    }
    signals.update(overrides)
    return signals


def test_compute_v2_scores_with_repository_uses_niche_and_population_key() -> None:
    repo = FakeBenchmarkRepository(benchmark_cell())

    result = compute_v2_scores_with_repository(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(),
        benchmark_repository=repo,
    )

    assert repo.calls == [("plumber", "metro_1m_5m")]
    assert result["benchmark"] == {
        "population_class": "metro_1m_5m",
        "sample_size": 12,
        "confidence_label": "medium",
    }
    assert result["flags"]["benchmark_undersampled"] is False
    assert result["scores"]["demand_strength"]["higher_is_better"] is True
    assert result["scores"]["organic_difficulty"]["higher_is_better"] is False
    assert result["scores"]["demand_strength"]["value"] == 200
    assert result["scores"]["organic_difficulty"]["value"] == 30
    assert result["scores"]["local_difficulty"]["value"] == 50
    assert result["scores"]["monetization_signal"]["value"] == 120
    assert result["scores"]["ai_resilience"]["value"] == 69
    assert result["flags"]["top5_organic_data_low_coverage"] is False


def test_missing_benchmark_sets_undersampled_flag_and_still_scores() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(),
        benchmark=None,
    )

    assert result["benchmark"] == {
        "population_class": "metro_1m_5m",
        "sample_size": 0,
        "confidence_label": "insufficient",
    }
    assert result["flags"]["benchmark_undersampled"] is True
    assert isinstance(result["scores"]["demand_strength"]["value"], int)
    assert isinstance(result["scores"]["monetization_signal"]["value"], int)


def test_local_difficulty_is_null_when_no_local_pack_is_detected() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(
            local_pack_present=False,
            top3_review_count_coverage=0.0,
            top3_review_velocity_coverage=0.0,
        ),
        benchmark=benchmark_cell(),
    )

    assert result["scores"]["local_difficulty"]["value"] is None
    assert result["flags"]["no_local_pack_detected"] is True
    assert result["flags"]["top3_review_data_low_coverage"] is False


def test_missing_top3_review_data_uses_benchmark_neutral_fallback() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(
            top3_review_count_min=None,
            top3_review_velocity_avg=None,
            local_pack_review_count_avg=0,
            review_velocity_avg=0,
            top3_review_count_coverage=0.0,
            top3_review_velocity_coverage=0.0,
        ),
        benchmark=benchmark_cell(),
    )

    assert result["scores"]["local_difficulty"]["value"] == 33
    assert result["flags"]["top3_review_data_low_coverage"] is True


def test_missing_top3_review_data_can_fallback_to_positive_legacy_average() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(
            top3_review_count_min=None,
            top3_review_velocity_avg=None,
            local_pack_review_count_avg=80,
            review_velocity_avg=6,
            top3_review_count_coverage=0.0,
            top3_review_velocity_coverage=0.0,
        ),
        benchmark=benchmark_cell(),
    )

    assert result["scores"]["local_difficulty"]["value"] == 67


def test_missing_top5_da_does_not_become_zero_organic_difficulty() -> None:
    with_da = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(avg_top5_da=0),
        benchmark=benchmark_cell(),
    )
    missing_da = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(avg_top5_da=None),
        benchmark=benchmark_cell(),
    )

    assert with_da["scores"]["organic_difficulty"]["value"] == 22
    assert missing_da["scores"]["organic_difficulty"]["value"] == 26


def test_top5_organic_low_coverage_flag_does_not_change_score_values() -> None:
    baseline = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(),
        benchmark=benchmark_cell(),
    )
    low_coverage = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(top5_da_coverage=0.4),
        benchmark=benchmark_cell(),
    )
    low_confidence = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(top5_organic_data_confidence="low"),
        benchmark=benchmark_cell(),
    )

    assert low_coverage["scores"] == baseline["scores"]
    assert low_confidence["scores"] == baseline["scores"]
    assert low_coverage["flags"]["top5_organic_data_low_coverage"] is True
    assert low_confidence["flags"]["top5_organic_data_low_coverage"] is True


def test_top5_organic_missing_evidence_sets_low_coverage_flag() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(
            avg_top5_da=None,
            avg_top5_lighthouse=None,
            top5_da_coverage=0.0,
            top5_lighthouse_coverage=0.0,
            top5_organic_data_confidence="missing",
        ),
        benchmark=benchmark_cell(),
    )

    assert result["scores"]["organic_difficulty"]["value"] == 26
    assert result["flags"]["top5_organic_data_low_coverage"] is True


def test_low_confidence_benchmark_sets_undersampled_flag() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(),
        benchmark=benchmark_cell(sample_size_metros=12, confidence_label="low"),
    )

    assert result["benchmark"]["confidence_label"] == "low"
    assert result["flags"]["benchmark_undersampled"] is True


def test_demand_ignores_v1_total_and_effective_volume() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(
            commercial_search_volume=0,
            total_search_volume=99_999,
            effective_search_volume=99_999,
        ),
        benchmark=benchmark_cell(),
    )

    assert result["scores"]["demand_strength"]["value"] == 0


def test_demand_derives_commercial_volume_from_nested_m6_demand_ratio() -> None:
    signals = signal_fixture()
    signals.pop("commercial_search_volume")
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals={
            **signals,
            "demand": {
                "total_search_volume": 2_000,
                "transactional_ratio": 0.7,
                "avg_cpc": 12.0,
                "effective_search_volume": 99_999,
            },
        },
        benchmark=benchmark_cell(),
    )

    assert result["scores"]["demand_strength"]["value"] == 168


def test_ai_resilience_sanitizes_null_inputs() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(
            aio_trigger_rate=None,
            transactional_keyword_ratio=None,
            local_fulfillment_required=None,
            paa_density=None,
        ),
        benchmark=benchmark_cell(),
    )

    assert isinstance(result["scores"]["ai_resilience"]["value"], int)
