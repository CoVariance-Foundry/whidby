import json

import pytest

from scripts.explore import audit_scoring_strategy


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows, *, failure=None):
        self._rows = rows
        self._failure = failure
        self._range = (0, len(rows) - 1)

    def select(self, _columns):
        if self._failure:
            raise self._failure
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        start, end = self._range
        return FakeResponse(self._rows[start : end + 1])


class FakeSupabase:
    def __init__(self, rows_by_table, failing_tables=None):
        self.rows_by_table = rows_by_table
        self.failing_tables = failing_tables or {}

    def table(self, table_name):
        return FakeQuery(
            self.rows_by_table.get(table_name, []),
            failure=self.failing_tables.get(table_name),
        )


def full_data(*, sample_size: int = 8, include_second_class_gap: bool = False):
    metros = [
        {
            "cbsa_code": "11111",
            "cbsa_name": "Austin-Round Rock-Georgetown, TX",
            "state": "TX",
            "population": 2300000,
            "population_class": "metro_1m_5m",
        }
    ]
    if include_second_class_gap:
        metros.append(
            {
                "cbsa_code": "22222",
                "cbsa_name": "Tyler, TX",
                "state": "TX",
                "population": 250000,
                "population_class": "medium_100_300k",
            }
        )

    metric_sufficiency = [
        {
            "benchmark_run_id": "run-1",
            "niche_normalized": "roofing",
            "population_class": "metro_1m_5m",
            "metric_family": family,
            "attempted_metros": sample_size,
            "non_null_metros": sample_size,
            "attempted_observations": sample_size * 2,
            "non_null_observations": sample_size * 2,
            "confidence_label": "medium" if sample_size >= 8 else "low",
            "source_endpoint": "benchmark_fixture",
            "source_window_start": "2026-05-01",
            "source_window_end": "2026-05-24",
            "created_at": "2026-05-24T00:00:00+00:00",
        }
        for family in audit_scoring_strategy.METRIC_FAMILIES
    ]

    return {
        "metros": metros,
        "niche_naics_mapping": [
            {
                "niche_normalized": "roofing",
                "niche_keyword": "roofing",
                "naics_code": "238160",
            }
        ],
        "seo_facts": [
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "intent": "commercial",
                "search_volume_monthly": 120,
                "cpc_usd": 12.5,
                "aio_present": False,
                "local_pack_present": True,
                "aggregator_count_top10": 2,
                "local_biz_count_top10": 5,
                "paa_count": 3,
                "ads_present": True,
                "lsa_present": True,
                "top3_review_count_min": 30,
                "top3_review_velocity_avg": 4.2,
                "avg_top5_da": 35,
                "avg_top5_lighthouse": 82,
                "top5_da_coverage": 0.8,
                "top5_lighthouse_coverage": 0.8,
                "report_id": "report-1",
            }
        ],
        "seo_benchmarks": [
            {
                "benchmark_run_id": "run-1",
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": sample_size,
                "confidence_label": "medium",
                "median_total_volume_per_capita": 0.001,
                "median_avg_cpc": 10,
                "median_aggregator_count": 2,
                "median_local_biz_count": 5,
                "median_top3_review_count_min": 25,
                "median_top3_review_velocity": 3,
                "median_establishments_per_100k": 50,
                "median_lsa_present_rate": 0.4,
                "median_ads_present_rate": 0.5,
                "median_aio_trigger_rate": 0.2,
            }
        ],
        "seo_benchmark_metric_sufficiency": metric_sufficiency,
        "metro_score_v2": [
            {
                "niche_normalized": "roofing",
                "cbsa_code": "11111",
                "report_id": "report-1",
                "demand_strength": 120,
                "organic_difficulty": 42,
                "local_difficulty": 35,
                "monetization_signal": 130,
                "ai_resilience": 80,
                "benchmark_confidence": "medium",
                "benchmark_sample_size": sample_size,
                "no_local_pack_detected": False,
                "benchmark_undersampled": sample_size < 8,
                "cbp_data_missing": False,
            }
        ],
        "explore_market_cells": [
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
                "score_system": "v2",
                "benchmark_confidence": "medium",
                "demand_strength": 120,
                "organic_difficulty": 42,
                "local_difficulty": 35,
                "monetization_signal": 130,
                "ai_resilience_score": 80,
                "business_density_per_1k": 2.5,
            }
        ],
        "reports": [],
        "metro_scores": [],
    }


def metric(report, component, metric_name):
    return next(
        item
        for item in report["metrics"]
        if item["component"] == component and item["metric"] == metric_name
    )


def build_report(data):
    return audit_scoring_strategy.build_report(
        data=data,
        services=("roofing",),
        population_classes=("metro_1m_5m",),
        reliable_threshold=0.8,
        slice_floor=0.6,
        min_benchmark_sample_size=8,
        expected_project_ref="eoajvifhbmqmoluiokcj",
        api_url="https://whidby-1.onrender.com",
        pilot_cities=12,
        pilot_concurrency=3,
    )


def test_build_report_marks_fully_covered_component_metrics_reliable():
    report = build_report(full_data())

    assert report["status"] == "pass"
    assert report["inventory"]["intended_market_pairs"] == 1
    assert metric(report, "demand", "commercial_volume")["status"] == "reliable"
    assert metric(report, "organic", "aggregator_count")["recommendation"] == "keep scored"
    assert metric(report, "app_surface", "explore_v2_preferred")["overall_coverage"] == 1.0


def test_build_report_summarizes_by_population_class_service_and_benchmark_cell():
    report = build_report(full_data())
    demand = metric(report, "demand", "commercial_volume")

    assert demand["by_population_class"] == {"metro_1m_5m": 1.0}
    assert demand["by_service"] == {"roofing": 1.0}
    assert demand["by_benchmark_cell"] == {"roofing|metro_1m_5m": 1.0}


def test_build_report_identifies_legacy_only_and_missing_explore_pairs():
    data = full_data(include_second_class_gap=True)
    data["reports"] = [{"id": "legacy-2", "niche_keyword": "roofing"}]
    data["metro_scores"] = [
        {
            "report_id": "legacy-2",
            "cbsa_code": "22222",
            "opportunity_score": 71,
        }
    ]

    report = audit_scoring_strategy.build_report(
        data=data,
        services=("roofing",),
        population_classes=("metro_1m_5m", "medium_100_300k"),
        reliable_threshold=0.8,
        slice_floor=0.6,
        min_benchmark_sample_size=8,
        expected_project_ref=None,
        api_url="https://whidby-1.onrender.com",
        pilot_cities=12,
        pilot_concurrency=3,
    )

    gaps = report["app_surface_gaps"]
    assert gaps["missing_v2_count"] == 1
    assert gaps["legacy_only_count"] == 1
    assert gaps["missing_explore_count"] == 1
    assert gaps["legacy_only_pairs"][0]["cbsa_code"] == "22222"


def test_component_metric_becomes_sparse_when_city_size_slice_is_under_floor():
    data = full_data(include_second_class_gap=True)
    report = audit_scoring_strategy.build_report(
        data=data,
        services=("roofing",),
        population_classes=("metro_1m_5m", "medium_100_300k"),
        reliable_threshold=0.8,
        slice_floor=0.6,
        min_benchmark_sample_size=8,
        expected_project_ref=None,
        api_url="https://whidby-1.onrender.com",
        pilot_cities=12,
        pilot_concurrency=3,
    )

    demand = metric(report, "demand", "commercial_volume")
    assert demand["overall_coverage"] == 0.5
    assert demand["minimum_required_population_class_coverage"] == 0.0
    assert demand["status"] == "sparse"
    assert demand["recommendation"] == "score with warning"


def test_benchmark_metric_is_undersampled_below_sample_size_threshold():
    report = build_report(full_data(sample_size=1))
    demand_benchmark = metric(report, "demand", "demand_benchmark")

    assert demand_benchmark["status"] == "undersampled"
    assert demand_benchmark["recommendation"] == "requires data acquisition"
    assert any("demand.demand_benchmark is undersampled" in failure for failure in report["critical_failures"])
    demand_sufficiency = report["metric_sufficiency"]["cells"][0]["families"]["demand"]
    assert demand_sufficiency["status"] == "metric_undersampled"
    assert report["strategy_readiness"]["strategy_totals"]["Easy Win"]["blocked"] == 1
    assert any(
        candidate["metric_family"] == "demand"
        and candidate["status"] == "metric_undersampled"
        for candidate in report["canary_guidance"]["paid_collection_candidates"]
    )


def test_strategy_readiness_blocks_required_families_and_warns_on_optional_families():
    data = full_data()
    for row in data["seo_benchmark_metric_sufficiency"]:
        if row["metric_family"] == "local_pack":
            row["non_null_metros"] = 0
            row["non_null_observations"] = 0
            row["confidence_label"] = "insufficient"
        if row["metric_family"] == "organic_authority":
            row["non_null_metros"] = 0
            row["non_null_observations"] = 0
            row["confidence_label"] = "insufficient"

    report = build_report(data)
    cell = report["strategy_readiness"]["cells"][0]
    strategies = {item["strategy"]: item for item in cell["strategies"]}

    assert report["metric_sufficiency"]["cells"][0]["families"]["local_pack"]["status"] == "metric_missing"
    assert strategies["GBP Blitz"]["status"] == "blocked"
    assert strategies["GBP Blitz"]["blockers"][0]["metric_family"] == "local_pack"
    assert strategies["Easy Win"]["status"] == "warning"
    assert strategies["Easy Win"]["warnings"][0]["metric_family"] == "organic_authority"
    assert report["canary_guidance"]["blocked_cells"] == [
        {
            "niche_normalized": "roofing",
            "population_class": "metro_1m_5m",
            "blocked_metric_families": ["organic_authority", "local_pack"],
        }
    ]


def test_metric_sufficiency_ignores_stale_rows_from_wrong_benchmark_run():
    data = full_data()
    data["seo_benchmarks"][0]["benchmark_run_id"] = "run-2"

    report = build_report(data)
    demand = report["metric_sufficiency"]["cells"][0]["families"]["demand"]
    easy_win = next(
        strategy
        for strategy in report["strategy_readiness"]["cells"][0]["strategies"]
        if strategy["strategy"] == "Easy Win"
    )

    assert demand["status"] == "metric_missing"
    assert demand["benchmark_run_id"] is None
    assert easy_win["status"] == "blocked"
    assert any(blocker["metric_family"] == "demand" for blocker in easy_win["blockers"])


def test_metric_sufficiency_ignores_orphan_rows_without_benchmark_cell():
    data = full_data()
    data["seo_benchmarks"] = []

    report = build_report(data)
    demand = report["metric_sufficiency"]["cells"][0]["families"]["demand"]
    easy_win = next(
        strategy
        for strategy in report["strategy_readiness"]["cells"][0]["strategies"]
        if strategy["strategy"] == "Easy Win"
    )

    assert demand["status"] == "metric_missing"
    assert demand["benchmark_run_id"] is None
    assert easy_win["status"] == "blocked"
    assert any(blocker["metric_family"] == "demand" for blocker in easy_win["blockers"])


def test_metric_sufficiency_allows_legacy_fallback_when_benchmark_cell_has_no_run_id():
    data = full_data()
    data["seo_benchmarks"][0]["benchmark_run_id"] = None

    report = build_report(data)
    demand = report["metric_sufficiency"]["cells"][0]["families"]["demand"]
    easy_win = next(
        strategy
        for strategy in report["strategy_readiness"]["cells"][0]["strategies"]
        if strategy["strategy"] == "Easy Win"
    )

    assert demand["status"] == "metric_ready"
    assert demand["benchmark_run_id"] == "run-1"
    assert easy_win["status"] == "ready"


def test_missing_top5_signal_is_telemetry_only_not_scored_reliable():
    data = full_data()
    data["seo_facts"][0]["avg_top5_da"] = None
    data["seo_facts"][0]["top5_da_coverage"] = None

    report = build_report(data)
    da_metric = metric(report, "organic", "top5_da_value")

    assert da_metric["status"] == "missing"
    assert da_metric["recommendation"] == "telemetry-only"
    measurement = metric(report, "organic", "top5_da_measurement")
    assert measurement["status"] == "missing"


def test_catalog_missing_service_is_a_critical_failure():
    data = full_data()
    report = audit_scoring_strategy.build_report(
        data=data,
        services=("roofing", "pest control"),
        population_classes=("metro_1m_5m",),
        reliable_threshold=0.8,
        slice_floor=0.6,
        min_benchmark_sample_size=8,
        expected_project_ref=None,
        api_url="https://whidby-1.onrender.com",
        pilot_cities=12,
        pilot_concurrency=3,
    )

    assert "pest control" in report["inventory"]["missing_catalog_services"]
    assert any("service catalog missing" in failure for failure in report["critical_failures"])


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (
            {
                "status": "success",
                "persistence": {
                    "ok": True,
                    "report_exists": True,
                    "metro_scores_count": 1,
                    "metro_score_v2_count": 1,
                    "seo_facts_count": 3,
                },
            },
            "success",
        ),
        (
            {"status": "failed", "error": "upstream timeout", "persistence": {}},
            "api_failure",
        ),
        (
            {
                "status": "partial_failure",
                "persistence": {"ok": False, "missing": ["metro_score_v2"]},
            },
            "persistence_partial_failure",
        ),
        (
            {"status": "failed", "error": "column avg_top5_da does not exist"},
            "schema_failure",
        ),
    ],
)
def test_classify_pilot_record(record, expected):
    assert audit_scoring_strategy.classify_pilot_record(record) == expected


def test_read_pilot_results_groups_by_status_population_and_service(tmp_path):
    path = tmp_path / "pilot.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "status": "success",
                        "request": {
                            "population_class": "metro_1m_5m",
                            "service": "roofing",
                        },
                        "persistence": {
                            "ok": True,
                            "report_exists": True,
                            "metro_scores_count": 1,
                            "metro_score_v2_count": 1,
                            "seo_facts_count": 3,
                        },
                    }
                ),
                json.dumps(
                    {
                        "status": "partial_failure",
                        "request": {
                            "population_class": "large_300k_1m",
                            "service": "plumbing",
                        },
                        "persistence": {"ok": False},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = audit_scoring_strategy.read_pilot_results([path])

    assert summary["record_count"] == 2
    assert summary["by_status"] == {"persistence_partial_failure": 1, "success": 1}
    assert summary["by_population_class"]["metro_1m_5m"]["success"] == 1
    assert summary["by_service"]["plumbing"]["persistence_partial_failure"] == 1


def test_pilot_failures_block_audit_status():
    report = audit_scoring_strategy.build_report(
        data=full_data(),
        services=("roofing",),
        population_classes=("metro_1m_5m",),
        reliable_threshold=0.8,
        slice_floor=0.6,
        min_benchmark_sample_size=8,
        expected_project_ref=None,
        api_url="https://whidby-1.onrender.com",
        pilot_cities=12,
        pilot_concurrency=3,
        pilot_results={
            "record_count": 2,
            "by_status": {"api_failure": 1, "success": 1},
            "by_population_class": {},
            "by_service": {},
        },
    )

    assert report["status"] == "fail"
    assert any("API pilot has non-success rows" in failure for failure in report["critical_failures"])


def test_expected_project_ref_guard_rejects_mismatch_and_suffixed_hosts(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://abc123.supabase.co")
    with pytest.raises(RuntimeError, match="expected def456, got abc123"):
        audit_scoring_strategy.validate_expected_project_ref("def456")

    monkeypatch.setenv(
        "NEXT_PUBLIC_SUPABASE_URL",
        "https://abc123.supabase.co.evil.test",
    )
    with pytest.raises(RuntimeError, match="expected abc123, got <unknown>"):
        audit_scoring_strategy.validate_expected_project_ref("abc123")


def test_fetch_pages_wraps_missing_column_errors(monkeypatch):
    class FakePostgrestError(Exception):
        code = "42703"

    monkeypatch.setattr(
        audit_scoring_strategy,
        "POSTGREST_API_ERROR_TYPES",
        (FakePostgrestError,),
    )
    supabase = FakeSupabase(
        rows_by_table={"seo_facts": []},
        failing_tables={"seo_facts": FakePostgrestError("column does not exist")},
    )

    with pytest.raises(RuntimeError, match="seo_facts missing required column"):
        audit_scoring_strategy.fetch_pages(supabase, "seo_facts", ("avg_top5_da",))


def test_fetch_pages_preserves_non_schema_postgrest_errors(monkeypatch):
    class FakePostgrestError(Exception):
        code = "PGRST301"

    monkeypatch.setattr(
        audit_scoring_strategy,
        "POSTGREST_API_ERROR_TYPES",
        (FakePostgrestError,),
    )
    supabase = FakeSupabase(
        rows_by_table={"seo_facts": []},
        failing_tables={"seo_facts": FakePostgrestError("JWT expired")},
    )

    with pytest.raises(FakePostgrestError, match="JWT expired"):
        audit_scoring_strategy.fetch_pages(supabase, "seo_facts", ("avg_top5_da",))


def test_fetch_pages_preserves_transport_errors():
    supabase = FakeSupabase(
        rows_by_table={"seo_facts": []},
        failing_tables={"seo_facts": TimeoutError("request timed out")},
    )

    with pytest.raises(TimeoutError, match="request timed out"):
        audit_scoring_strategy.fetch_pages(supabase, "seo_facts", ("avg_top5_da",))


def test_parse_args_uses_plan_defaults():
    args = audit_scoring_strategy.parse_args([])

    assert args.reliable_threshold == 0.8
    assert args.slice_floor == 0.6
    assert args.min_benchmark_sample_size == 8
    assert args.pilot_cities == 12
    assert args.pilot_concurrency == 3


def test_render_markdown_includes_component_summary_and_pilot_command():
    report = build_report(full_data())

    markdown = audit_scoring_strategy.render_markdown(report)

    assert "# Scoring Strategy Audit" in markdown
    assert "Component Summary" in markdown
    assert "Metric Sufficiency" in markdown
    assert "| Metric family | Ready | Undersampled | Missing |" in markdown
    assert "App Surface Gaps" in markdown
    assert "Strategy Readiness" in markdown
    assert "Canary Guidance" in markdown
    assert "scripts/explore/bulk_score.py --apply" in markdown


def test_write_reports_handles_guard_failure_markdown(tmp_path):
    report = {
        "generated_at": "2026-05-22T00:00:00+00:00",
        "status": "fail",
        "critical_failures": ["seo_facts missing required column(s): avg_top5_da"],
    }

    _json_path, markdown_path = audit_scoring_strategy.write_reports(report, tmp_path)

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Critical Failures" in markdown
    assert "avg_top5_da" in markdown
