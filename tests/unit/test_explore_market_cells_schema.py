from pathlib import Path


MIGRATION = Path("supabase/migrations/018_explore_market_cells.sql")


def _sql() -> str:
    assert MIGRATION.exists(), f"Missing migration: {MIGRATION}"
    return MIGRATION.read_text()


def test_explore_market_cells_is_derived_read_model() -> None:
    sql = _sql()

    assert "explore_market_cells" in sql
    assert "CREATE MATERIALIZED VIEW public.explore_market_cells" in sql
    assert "CREATE TABLE public.explore_market_cells" not in sql
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


def test_explore_market_cells_dedupes_refresh_targets() -> None:
    sql = _sql()

    assert "SELECT DISTINCT ON (t.cbsa_code, t.niche_normalized)" in sql
    assert "public.explore_refresh_policies" in sql
    assert "p.enabled IS TRUE" in sql
    assert "t.active IS TRUE" in sql


def test_explore_market_cells_uses_refresh_cadence_for_staleness() -> None:
    sql = _sql()

    assert "cadence_days" in sql
    assert "COALESCE(refresh.cadence_days, 30) * interval '1 day'" in sql
    assert "now() - interval '30 days'" not in sql


def test_explore_market_cells_normalizes_legacy_suffixes() -> None:
    sql = _sql()

    assert "services?" in sql
    assert "company" in sql
    assert "contractors?" in sql
    assert "lower(trim(r.niche_keyword))" in sql
