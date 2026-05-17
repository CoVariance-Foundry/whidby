from pathlib import Path


MIGRATION = Path("supabase/migrations/018_explore_market_cells.sql")


def _sql() -> str:
    assert MIGRATION.exists(), f"Missing migration: {MIGRATION}"
    return MIGRATION.read_text()


def test_explore_market_cells_is_derived_read_model() -> None:
    sql = _sql()

    assert "explore_market_cells" in sql
    assert "public.metros" in sql
    assert "public.census_cbp_establishments" in sql
    assert "public.niche_naics_mapping" in sql
    assert "public.metro_score_v2" in sql
    assert "public.metro_scores" in sql
    assert "CREATE TABLE public.cities" not in sql
    assert "_simplified" not in sql


def test_explore_market_cells_exposes_metric_contract() -> None:
    sql = _sql()

    for column in (
        "cbsa_code",
        "niche_normalized",
        "niche_keyword",
        "presentation_score",
        "score_system",
        "business_density_per_1k",
        "establishment_growth_yoy",
        "growth_available",
        "latest_scored_at",
        "refresh_target_id",
        "stale",
    ):
        assert column in sql


def test_explore_market_cells_has_lookup_indexes() -> None:
    sql = _sql()

    assert "idx_explore_market_cells_niche_cbsa" in sql
    assert "idx_explore_market_cells_cbsa" in sql
    assert "idx_explore_market_cells_score" in sql
