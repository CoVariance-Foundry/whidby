import pytest

from scripts.explore import audit_signal_coverage
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
        if not isinstance(self.failing_tables, dict):
            self.failing_tables = {
                table: RuntimeError("column does not exist") for table in self.failing_tables
            }

    def table(self, table_name):
        return FakeQuery(
            self.rows_by_table.get(table_name, []),
            failure=self.failing_tables.get(table_name),
        )


def metric_rows(
    *,
    niche: str = "roofing",
    population_class: str = "metro_1m_5m",
    non_null_metros: int = 8,
    confidence_label: str = "medium",
):
    return [
        {
            "benchmark_run_id": "run-1",
            "niche_normalized": niche,
            "population_class": population_class,
            "metric_family": family,
            "attempted_metros": 8,
            "non_null_metros": non_null_metros,
            "attempted_observations": 16,
            "non_null_observations": non_null_metros * 2,
            "confidence_label": confidence_label,
            "source_endpoint": "benchmark_fixture",
            "source_window_start": "2026-05-01",
            "source_window_end": "2026-05-24",
            "created_at": "2026-05-24T00:00:00+00:00",
        }
        for family in audit_scoring_strategy.METRIC_FAMILIES
    ]


def test_build_report_passes_when_coverage_benchmarks_and_explore_cache_are_ready():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 42,
                "avg_top5_lighthouse": 88,
                "top5_da_coverage": 0.8,
                "top5_lighthouse_coverage": 0.8,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[
            {
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 5,
            }
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=1,
    )

    assert report["status"] == "pass"
    assert report["overall"]["da_value_coverage"] == 1.0
    assert report["benchmark_cells"]["count"] == 1
    assert report["explore_visibility"]["visible_pairs"] == 1


def test_build_report_fails_low_coverage_missing_benchmarks_and_explore_gaps():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": None,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 0.0,
                "top5_lighthouse_coverage": 0.6,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[],
        explore_cells=[],
        threshold=0.9,
        min_benchmark_cells=1,
        min_benchmark_sample_size=1,
    )

    assert report["status"] == "fail"
    assert any("DA value coverage" in failure for failure in report["failures"])
    assert any("usable benchmark cell count" in failure for failure in report["failures"])
    assert any("missing Explore cache rows" in failure for failure in report["failures"])


def test_build_report_fails_when_measurement_coverage_is_low_despite_values():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 0.0,
                "top5_lighthouse_coverage": 0.2,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[
            {
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 5,
            }
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=1,
    )

    assert report["status"] == "fail"
    assert any("DA measurement coverage" in failure for failure in report["failures"])
    assert any("Lighthouse measurement coverage" in failure for failure in report["failures"])


def test_average_measurement_coverage_counts_nulls_as_zero():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            },
            {
                "cbsa_code": "22222",
                "niche_normalized": "roofing",
                "avg_top5_da": 42,
                "avg_top5_lighthouse": 82,
                "top5_da_coverage": None,
                "top5_lighthouse_coverage": None,
            },
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            },
            {
                "cbsa_code": "22222",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "population_class": "metro_1m_5m",
            },
        ],
        benchmarks=[
            {
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 5,
            }
        ],
        explore_cells=[
            {"cbsa_code": "11111", "niche_normalized": "roofing", "report_id": "report-1"},
            {"cbsa_code": "22222", "niche_normalized": "roofing", "report_id": "report-2"},
        ],
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=1,
    )

    assert report["overall"]["avg_top5_da_coverage"] == 0.5
    assert report["overall"]["avg_top5_lighthouse_coverage"] == 0.5
    assert any("DA measurement coverage" in failure for failure in report["failures"])


def test_build_report_fails_when_service_slice_has_low_coverage():
    complete_roofing_rows = [
        {
            "cbsa_code": str(10000 + index),
            "niche_normalized": "roofing",
            "avg_top5_da": 40 + index,
            "avg_top5_lighthouse": 80 + index,
            "top5_da_coverage": 1.0,
            "top5_lighthouse_coverage": 1.0,
        }
        for index in range(8)
    ]
    facts = [
        *complete_roofing_rows,
        {
            "cbsa_code": "20000",
            "niche_normalized": "plumbing",
            "avg_top5_da": None,
            "avg_top5_lighthouse": None,
            "top5_da_coverage": None,
            "top5_lighthouse_coverage": None,
        },
    ]
    metros = [
        {
            "cbsa_code": row["cbsa_code"],
            "cbsa_name": f"Metro {row['cbsa_code']}",
            "population_class": "metro_1m_5m",
        }
        for row in facts
    ]
    benchmarks = [
        {
            "niche_normalized": niche,
            "population_class": "metro_1m_5m",
            "sample_size_metros": 5,
        }
        for niche in ("roofing", "plumbing")
    ]
    explore_cells = [
        {
            "cbsa_code": row["cbsa_code"],
            "niche_normalized": row["niche_normalized"],
            "report_id": f"report-{row['cbsa_code']}",
        }
        for row in facts
    ]

    report = audit_signal_coverage.build_report(
        facts=facts,
        metros=metros,
        benchmarks=benchmarks,
        explore_cells=explore_cells,
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=1,
    )

    assert report["overall"]["da_value_coverage"] == 0.8889
    assert report["status"] == "fail"
    assert any("service niche_normalized=plumbing" in failure for failure in report["failures"])


def test_build_report_fails_when_benchmark_cell_sample_size_is_too_small():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[
            {
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 0,
            }
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=1,
    )

    assert report["status"] == "fail"
    assert any("below sample size" in failure for failure in report["failures"])
    assert report["benchmark_cells"]["undersampled_fact_cells"] == [
        {
            "niche_normalized": "roofing",
            "population_class": "metro_1m_5m",
            "sample_size_metros": 0,
        }
    ]


def test_usable_benchmark_count_excludes_undersampled_cells():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[
            {
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 8,
            },
            {
                "niche_normalized": "plumbing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 0,
            },
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        threshold=0.8,
        min_benchmark_cells=2,
        min_benchmark_sample_size=8,
    )

    assert report["status"] == "fail"
    assert report["benchmark_cells"]["count"] == 2
    assert report["benchmark_cells"]["usable_count"] == 1
    assert any("usable benchmark cell count" in failure for failure in report["failures"])


def test_metric_sufficiency_reports_family_statuses_and_canary_guidance():
    rows = metric_rows()
    for row in rows:
        if row["metric_family"] == "review_velocity":
            row["non_null_metros"] = 2
            row["non_null_observations"] = 4
            row["confidence_label"] = "low"
        if row["metric_family"] == "gbp_profile":
            row["non_null_metros"] = 0
            row["non_null_observations"] = 0
            row["confidence_label"] = "insufficient"

    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[
            {
                "benchmark_run_id": "run-1",
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 8,
            }
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        metric_sufficiency_rows=rows,
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=8,
    )

    families = report["metric_sufficiency"]["cells"][0]["families"]
    assert report["status"] == "fail"
    assert families["demand"]["status"] == "metric_ready"
    assert families["review_velocity"]["status"] == "metric_undersampled"
    assert families["gbp_profile"]["status"] == "metric_missing"
    assert report["strategy_readiness"]["strategy_totals"]["GBP Blitz"]["blocked"] == 1
    assert any(
        candidate["metric_family"] == "review_velocity"
        for candidate in report["canary_guidance"]["paid_collection_candidates"]
    )
    assert any("benchmark metric family sufficiency gap" in failure for failure in report["failures"])


def test_metric_sufficiency_ignores_orphan_rows_without_benchmark_cell():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        metric_sufficiency_rows=metric_rows(),
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=8,
    )

    families = report["metric_sufficiency"]["cells"][0]["families"]
    assert families["demand"]["status"] == "metric_missing"
    assert report["strategy_readiness"]["strategy_totals"]["Easy Win"]["blocked"] == 1
    assert any("lack benchmark cells" in failure for failure in report["failures"])


def test_metric_sufficiency_scopes_gaps_to_audited_fact_cells():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[
            {
                "benchmark_run_id": "run-1",
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 8,
            },
            {
                "benchmark_run_id": "run-2",
                "niche_normalized": "plumbing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 8,
            },
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        metric_sufficiency_rows=metric_rows(),
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=8,
    )

    cells = report["metric_sufficiency"]["cells"]
    assert report["status"] == "pass"
    assert [
        (cell["niche_normalized"], cell["population_class"])
        for cell in cells
    ] == [("roofing", "metro_1m_5m")]
    assert not any(
        "benchmark metric family sufficiency gap" in failure
        for failure in report["failures"]
    )


def test_metric_sufficiency_allows_legacy_fallback_when_benchmark_cell_has_no_run_id():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            }
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            }
        ],
        benchmarks=[
            {
                "benchmark_run_id": None,
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 8,
            }
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        metric_sufficiency_rows=metric_rows(),
        threshold=0.8,
        min_benchmark_cells=1,
        min_benchmark_sample_size=8,
    )

    families = report["metric_sufficiency"]["cells"][0]["families"]
    assert families["demand"]["status"] == "metric_ready"
    assert report["strategy_readiness"]["strategy_totals"]["Easy Win"]["ready"] == 1


def test_explore_visibility_slice_gets_coverage_gate():
    report = audit_signal_coverage.build_report(
        facts=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "avg_top5_da": 41,
                "avg_top5_lighthouse": 81,
                "top5_da_coverage": 1.0,
                "top5_lighthouse_coverage": 1.0,
            },
            {
                "cbsa_code": "22222",
                "niche_normalized": "roofing",
                "avg_top5_da": None,
                "avg_top5_lighthouse": None,
                "top5_da_coverage": None,
                "top5_lighthouse_coverage": None,
            },
        ],
        metros=[
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "population_class": "metro_1m_5m",
            },
            {
                "cbsa_code": "22222",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "population_class": "metro_1m_5m",
            },
        ],
        benchmarks=[
            {
                "niche_normalized": "roofing",
                "population_class": "metro_1m_5m",
                "sample_size_metros": 8,
            }
        ],
        explore_cells=[
            {
                "cbsa_code": "11111",
                "niche_normalized": "roofing",
                "report_id": "report-1",
            }
        ],
        threshold=0.4,
        min_benchmark_cells=1,
        min_benchmark_sample_size=8,
    )

    assert report["status"] == "fail"
    assert any(
        "explore_visibility explore_visible=False" in failure
        for failure in report["failures"]
    )


def test_audit_signal_coverage_fails_for_missing_required_schema_columns(monkeypatch):
    class FakePostgrestError(Exception):
        code = "42703"

    monkeypatch.setattr(
        audit_signal_coverage,
        "POSTGREST_API_ERROR_TYPES",
        (FakePostgrestError,),
    )
    supabase = FakeSupabase(
        rows_by_table={"seo_facts": []},
        failing_tables={"seo_facts": FakePostgrestError("column does not exist")},
    )

    with pytest.raises(RuntimeError, match="seo_facts missing required column"):
        audit_signal_coverage.audit_signal_coverage(
            supabase,
            threshold=0.8,
            min_benchmark_cells=1,
            min_benchmark_sample_size=1,
        )


def test_audit_signal_coverage_preserves_non_schema_errors(monkeypatch):
    class FakePostgrestError(Exception):
        code = "PGRST301"

    monkeypatch.setattr(
        audit_signal_coverage,
        "POSTGREST_API_ERROR_TYPES",
        (FakePostgrestError,),
    )
    supabase = FakeSupabase(
        rows_by_table={"seo_facts": []},
        failing_tables={"seo_facts": FakePostgrestError("JWT expired")},
    )

    with pytest.raises(FakePostgrestError, match="JWT expired"):
        audit_signal_coverage.audit_signal_coverage(
            supabase,
            threshold=0.8,
            min_benchmark_cells=1,
            min_benchmark_sample_size=1,
        )


def test_audit_signal_coverage_preserves_transport_errors():
    supabase = FakeSupabase(
        rows_by_table={"seo_facts": []},
        failing_tables={"seo_facts": TimeoutError("request timed out")},
    )

    with pytest.raises(TimeoutError, match="request timed out"):
        audit_signal_coverage.audit_signal_coverage(
            supabase,
            threshold=0.8,
            min_benchmark_cells=1,
            min_benchmark_sample_size=1,
        )


def test_expected_project_ref_guard_rejects_mismatched_url(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://abc123.supabase.co")

    with pytest.raises(RuntimeError, match="expected def456, got abc123"):
        audit_signal_coverage.validate_expected_project_ref("def456")


def test_expected_project_ref_guard_rejects_suffixed_supabase_host(monkeypatch):
    monkeypatch.setenv(
        "NEXT_PUBLIC_SUPABASE_URL",
        "https://abc123.supabase.co.evil.test",
    )

    with pytest.raises(RuntimeError, match="expected abc123, got <unknown>"):
        audit_signal_coverage.validate_expected_project_ref("abc123")


def test_parse_args_defaults_to_canonical_benchmark_sample_size():
    args = audit_signal_coverage.parse_args([])

    assert args.min_benchmark_sample_size == 8
