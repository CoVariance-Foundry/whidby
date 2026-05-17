from scripts.explore.audit_explore_sources import (
    REQUIRED_TABLES,
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
