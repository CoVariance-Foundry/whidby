import pytest

from scripts.benchmarks import recompute_benchmarks


MIGRATION = (
    "supabase/migrations/"
    "20260531191233_whi134_metric_sufficiency_recompute.sql"
)
GBP_PROFILE_MIGRATION = (
    "supabase/migrations/"
    "20260531212243_whi138_gbp_profile_sufficiency.sql"
)


def test_parse_args_accepts_expected_project_ref() -> None:
    args = recompute_benchmarks.parse_args(
        ["30", "--expected-project-ref", "wuybidpvqhhgkukpyyhq"]
    )

    assert args.window_days == 30
    assert args.expected_project_ref == "wuybidpvqhhgkukpyyhq"


def test_expected_project_ref_guard_accepts_matching_url(monkeypatch) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co",
    )

    recompute_benchmarks.validate_expected_project_ref("wuybidpvqhhgkukpyyhq")


def test_expected_project_ref_guard_rejects_mismatched_url(monkeypatch) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co",
    )

    with pytest.raises(RuntimeError, match="expected eoajvifhbmqmoluiokcj"):
        recompute_benchmarks.validate_expected_project_ref("eoajvifhbmqmoluiokcj")


def test_expected_project_ref_guard_rejects_suffixed_supabase_host(monkeypatch) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co.evil.test",
    )

    with pytest.raises(RuntimeError, match="expected wuybidpvqhhgkukpyyhq, got <unknown>"):
        recompute_benchmarks.validate_expected_project_ref("wuybidpvqhhgkukpyyhq")


def test_main_validates_project_ref_before_rpc(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co",
    )

    def fail_rpc(*_args, **_kwargs):  # noqa: ANN001
        raise AssertionError("rpc should not run after project mismatch")

    monkeypatch.setattr(recompute_benchmarks, "rpc", fail_rpc)

    with pytest.raises(SystemExit) as exc:
        recompute_benchmarks.main(["--expected-project-ref", "eoajvifhbmqmoluiokcj"])

    assert exc.value.code == 2
    assert "Supabase project ref mismatch" in capsys.readouterr().err


def test_metric_sufficiency_recompute_migration_writes_lineage_and_families() -> None:
    migration = recompute_benchmarks.REPO_ROOT.joinpath(MIGRATION).read_text()

    assert "INSERT INTO public.seo_benchmark_runs" in migration
    assert "INSERT INTO public.seo_benchmark_metric_sufficiency" in migration
    assert "benchmark_run_id = v_run_id" in migration
    for family in (
        "demand",
        "organic_serp",
        "organic_authority",
        "lighthouse_site_quality",
        "local_pack",
        "review_velocity",
        "monetization",
        "ai_serp_displacement",
    ):
        assert f"'{family}'" in migration
    assert "'gbp_profile'" not in migration
    assert "business_data/google/my_business_info/live" not in migration


def test_metric_sufficiency_recompute_migration_sets_function_search_path() -> None:
    migration = recompute_benchmarks.REPO_ROOT.joinpath(MIGRATION).read_text()

    assert "SET search_path = public, pg_temp" in migration
    assert "ALTER FUNCTION public.recompute_seo_benchmarks_without_lineage(INTEGER)" in migration


def test_metric_sufficiency_recompute_uses_family_specific_evidence() -> None:
    migration = recompute_benchmarks.REPO_ROOT.joinpath(MIGRATION).read_text()

    assert "WHERE search_volume_monthly IS NOT NULL OR cpc_usd IS NOT NULL" not in migration
    assert "aggregator_count_top10 IS NOT NULL\n                   OR local_biz_count_top10 IS NOT NULL\n            )::integer" in migration
    assert "OR aio_present IS NOT NULL\n                   OR featured_snippet_present IS NOT NULL\n                   OR paa_count IS NOT NULL\n            )::integer,\n            'serp/google/organic/live/advanced'\n        FROM fact_base\n        GROUP BY niche_normalized, population_class\n\n        UNION ALL\n\n        SELECT\n            niche_normalized,\n            population_class,\n            'organic_authority'" not in migration
    assert "OR lsa_present IS NOT NULL" in migration
    assert "OR ads_present IS NOT NULL" in migration


def test_gbp_profile_sufficiency_recompute_uses_local_pack_evidence() -> None:
    migration = recompute_benchmarks.REPO_ROOT.joinpath(GBP_PROFILE_MIGRATION).read_text()

    assert "CREATE OR REPLACE FUNCTION public.recompute_seo_benchmarks" in migration
    for family in (
        "demand",
        "organic_serp",
        "organic_authority",
        "lighthouse_site_quality",
        "local_pack",
        "review_velocity",
        "gbp_profile",
        "monetization",
        "ai_serp_displacement",
    ):
        assert f"'{family}'" in migration
    assert "local_pack_listing_facts" in migration
    assert "gbp_completeness" in migration
    assert "'business_data/google/my_business_info/live'" in migration
    assert "FROM recomputed_cells rc\n        LEFT JOIN local_pack_base lp" in migration
    assert "count(DISTINCT lp.cbsa_code)::integer" in migration
    assert "count(lp.cbsa_code)::integer" in migration
    assert "count(lp.gbp_completeness)::integer" in migration
    assert "metric_confidence_rollup" in migration
