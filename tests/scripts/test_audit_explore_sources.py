from scripts.explore.audit_explore_sources import (
    REQUIRED_TABLES,
    get_cbp_years,
    summarize_explore_readiness,
    summarize_table_health,
)


def test_required_tables_include_explore_sources() -> None:
    assert REQUIRED_TABLES == (
        "metros",
        "census_cbp_establishments",
        "niche_naics_mapping",
        "reports",
        "metro_scores",
        "metro_score_v2",
        "explore_market_cells",
        "seo_facts",
        "seo_benchmarks",
    )


def test_summarize_table_health_flags_sparse_metros() -> None:
    summary = summarize_table_health(
        table="metros",
        row_count=11,
        non_null_counts={
            "population": 0,
            "median_household_income_usd": 0,
            "population_class": 0,
        },
    )

    assert summary["table"] == "metros"
    assert summary["row_count"] == 11
    assert summary["status"] == "fail"
    assert "population" in summary["missing_required_fields"]
    assert "median_household_income_usd" in summary["missing_required_fields"]
    assert "population_class" in summary["missing_required_fields"]


def test_summarize_table_health_allows_optional_fields() -> None:
    summary = summarize_table_health(
        table="metros",
        row_count=120,
        non_null_counts={
            "population": 120,
            "median_household_income_usd": 118,
            "population_class": 120,
            "median_age_years": 0,
        },
    )

    assert summary["status"] == "warn"
    assert summary["missing_required_fields"] == []
    assert summary["missing_optional_fields"] == ["median_age_years"]


def test_summarize_explore_readiness_keeps_one_year_growth_as_warning() -> None:
    summary = summarize_explore_readiness(
        explore_market_cells_count=120,
        market_cells_with_density=100,
        cbp_years=[2023],
    )

    assert summary["status"] == "warn"
    assert summary["explore_market_cells_count"] == 120
    assert summary["market_cells_with_density"] == 100
    assert summary["cbp_years"] == [2023]
    assert summary["growth_available"] is False
    assert summary["message"] == (
        "growth unavailable: census_cbp_establishments has 1 year loaded"
    )


def test_summarize_explore_readiness_passes_with_two_cbp_years() -> None:
    summary = summarize_explore_readiness(
        explore_market_cells_count=120,
        market_cells_with_density=100,
        cbp_years=[2022, 2023],
    )

    assert summary["status"] == "pass"
    assert summary["growth_available"] is True


def test_get_cbp_years_checks_candidate_years_without_row_sampling(monkeypatch) -> None:
    calls: list[dict[str, str] | None] = []

    def fake_get_count(config, table, params=None):  # noqa: ANN001
        calls.append(params)
        if params in ({"year": "eq.2022"}, {"year": "eq.2023"}):
            return 1, None
        return 0, None

    monkeypatch.setattr(
        "scripts.explore.audit_explore_sources.get_count",
        fake_get_count,
    )

    years, error = get_cbp_years(object())  # type: ignore[arg-type]

    assert error is None
    assert years == [2022, 2023]
    assert {"year": "eq.2022"} in calls
    assert {"year": "eq.2023"} in calls
