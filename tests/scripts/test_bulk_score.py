import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts.explore import bulk_score


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self.ranges: list[tuple[int, int]] = []
        self.filters: list[tuple[str, str, object]] = []
        self._limit: int | None = None

    @property
    def not_(self):
        self._negate_next = True
        return self

    def select(self, _columns, **_kwargs):
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def in_(self, column, value):
        self.filters.append(("in", column, value))
        return self

    def gte(self, column, value):
        self.filters.append(("gte", column, value))
        return self

    def lte(self, column, value):
        self.filters.append(("lte", column, value))
        return self

    def is_(self, column, value):
        op = "not_is" if getattr(self, "_negate_next", False) else "is"
        self.filters.append((op, column, value))
        self._negate_next = False
        return self

    def order(self, column, desc=False):
        self._rows = sorted(
            self._rows,
            key=lambda row: row.get(column) or 0,
            reverse=desc,
        )
        return self

    def limit(self, value):
        self._limit = value
        return self

    def range(self, start, end):
        self.ranges.append((start, end))
        self._range = (start, end)
        return self

    def execute(self):
        rows = [row for row in self._rows if self._matches(row)]
        if self._limit is not None:
            rows = rows[: self._limit]
        start, end = getattr(self, "_range", (0, len(self._rows) - 1))
        return FakeResponse(rows[start : end + 1])

    def _matches(self, row):
        for op, column, value in self.filters:
            row_value = row.get(column)
            if op == "eq" and row_value != value:
                return False
            if op == "in" and row_value not in value:
                return False
            if op == "gte" and row_value < value:
                return False
            if op == "lte" and row_value > value:
                return False
            if op == "is" and value == "null" and row_value is not None:
                return False
            if op == "not_is" and value == "null" and row_value is None:
                return False
        return True


class FakeSupabase:
    def __init__(self, rows_by_table):
        self.rows_by_table = rows_by_table
        self.queries: dict[str, list[FakeQuery]] = {}

    def table(self, table_name):
        query = FakeQuery(self.rows_by_table.get(table_name, []))
        self.queries.setdefault(table_name, []).append(query)
        return query


def test_api_url_defaults_to_local_fastapi_port(monkeypatch):
    monkeypatch.delenv("NEXT_PUBLIC_API_URL", raising=False)

    assert bulk_score._api_url(SimpleNamespace(api_url=None)) == "http://localhost:8000"


def test_fetch_metros_prioritizes_rank_and_rent_classes_and_caps_mega():
    supabase = FakeSupabase(
        rows_by_table={
            "metros": [
                {
                    "cbsa_code": "10000",
                    "cbsa_name": "New York-Newark-Jersey City, NY-NJ-PA",
                    "state": "NY",
                    "population": 19_000_000,
                    "population_class": "mega_5m_plus",
                    "dataforseo_location_codes": [1],
                },
                {
                    "cbsa_code": "20000",
                    "cbsa_name": "Los Angeles-Long Beach-Anaheim, CA",
                    "state": "CA",
                    "population": 12_000_000,
                    "population_class": "mega_5m_plus",
                    "dataforseo_location_codes": [2],
                },
                {
                    "cbsa_code": "30000",
                    "cbsa_name": "Greenville-Anderson, SC",
                    "state": "SC",
                    "population": 950_000,
                    "population_class": "large_300k_1m",
                    "dataforseo_location_codes": [3],
                },
                {
                    "cbsa_code": "40000",
                    "cbsa_name": "Waco, TX",
                    "state": "TX",
                    "population": 280_000,
                    "population_class": "medium_100_300k",
                    "dataforseo_location_codes": [4],
                },
                {
                    "cbsa_code": "50000",
                    "cbsa_name": "No DFS, OH",
                    "state": "OH",
                    "population": 800_000,
                    "population_class": "large_300k_1m",
                    "dataforseo_location_codes": [],
                },
            ]
        }
    )

    metros = bulk_score.fetch_metros(
        supabase,
        limit=4,
        strategy="rank-and-rent",
        population_classes=None,
        min_population=None,
        max_population=None,
        require_dfs=True,
        mega_cap=1,
    )

    assert [metro["cbsa_code"] for metro in metros] == ["30000", "40000", "10000"]


def test_fetch_metros_supports_population_class_filters():
    supabase = FakeSupabase(
        rows_by_table={
            "metros": [
                {
                    "cbsa_code": "30000",
                    "cbsa_name": "Greenville-Anderson, SC",
                    "state": "SC",
                    "population": 950_000,
                    "population_class": "large_300k_1m",
                    "dataforseo_location_codes": [3],
                },
                {
                    "cbsa_code": "40000",
                    "cbsa_name": "Waco, TX",
                    "state": "TX",
                    "population": 280_000,
                    "population_class": "medium_100_300k",
                    "dataforseo_location_codes": [4],
                },
            ]
        }
    )

    metros = bulk_score.fetch_metros(
        supabase,
        limit=5,
        strategy="rank-and-rent",
        population_classes=["medium_100_300k"],
        min_population=100_000,
        max_population=300_000,
        require_dfs=True,
        mega_cap=5,
    )

    assert [metro["cbsa_code"] for metro in metros] == ["40000"]


def test_fetch_metros_top_population_uses_true_top_n_without_mega_cap():
    supabase = FakeSupabase(
        rows_by_table={
            "metros": [
                {
                    "cbsa_code": "10000",
                    "cbsa_name": "New York-Newark-Jersey City, NY-NJ-PA",
                    "state": "NY",
                    "population": 19_000_000,
                    "population_class": "mega_5m_plus",
                    "dataforseo_location_codes": [1],
                },
                {
                    "cbsa_code": "20000",
                    "cbsa_name": "Los Angeles-Long Beach-Anaheim, CA",
                    "state": "CA",
                    "population": 12_000_000,
                    "population_class": "mega_5m_plus",
                    "dataforseo_location_codes": [2],
                },
                {
                    "cbsa_code": "30000",
                    "cbsa_name": "Greenville-Anderson, SC",
                    "state": "SC",
                    "population": 950_000,
                    "population_class": "large_300k_1m",
                    "dataforseo_location_codes": [3],
                },
            ]
        }
    )

    metros = bulk_score.fetch_metros(
        supabase,
        limit=2,
        strategy="top-population",
        population_classes=None,
        min_population=None,
        max_population=None,
        require_dfs=True,
        mega_cap=1,
    )

    assert [metro["cbsa_code"] for metro in metros] == ["10000", "20000"]


def test_normalize_service_key_preserves_catalog_service_names():
    assert bulk_score.normalize_service_key("tree service") == "tree service"
    assert bulk_score.normalize_service_key("Tree   Service") == "tree service"
    assert bulk_score.normalize_service_key("Roofing Service") == "roofing"
    assert bulk_score.normalize_service_key("Roofing Services") == "roofing"
    assert bulk_score.normalize_service_key("roofing contractors") == "roofing"


def test_fetch_scored_pairs_paginates_scores_and_reports():
    metro_scores = [
        {"cbsa_code": f"{index:05d}", "report_id": f"report-{index}"}
        for index in range(1005)
    ]
    reports = [
        {"id": f"report-{index}", "niche_keyword": f"Service {index}"}
        for index in range(1005)
    ]
    supabase = FakeSupabase(
        rows_by_table={"metro_scores": metro_scores, "reports": reports}
    )

    pairs = bulk_score.fetch_scored_pairs(supabase)

    assert ("01004", "service 1004") in pairs
    assert len(pairs) == 1005
    assert [query.ranges[0] for query in supabase.queries["metro_scores"]] == [
        (0, 999),
        (1000, 1999),
    ]
    assert [query.ranges[0] for query in supabase.queries["reports"]] == [
        (0, 999),
        (1000, 1999),
    ]


def test_fetch_scored_pairs_merges_explore_market_cells_and_legacy_reports():
    supabase = FakeSupabase(
        rows_by_table={
            "explore_market_cells": [
                {
                    "cbsa_code": "11111",
                    "niche_normalized": "Roofing Services",
                    "report_id": "report-1",
                },
                {
                    "cbsa_code": "22222",
                    "niche_normalized": "plumbing",
                    "report_id": None,
                },
            ],
            "metro_scores": [
                {"cbsa_code": "33333", "report_id": "legacy-report"}
            ],
            "reports": [
                {"id": "legacy-report", "niche_keyword": "legacy"}
            ],
        }
    )

    assert bulk_score.fetch_scored_pairs(supabase) == {
        ("11111", "roofing"),
        ("33333", "legacy"),
    }


def test_verify_persistence_requires_v2_rows_when_enabled():
    supabase = FakeSupabase(
        rows_by_table={
            "reports": [{"id": "report-1"}],
            "metro_scores": [{"report_id": "report-1", "cbsa_code": "11111"}],
            "metro_score_v2": [],
            "seo_facts": [],
        }
    )

    result = bulk_score.verify_persistence(
        supabase,
        report_id="report-1",
        cbsa_code="11111",
        require_v2=True,
    )

    assert result["ok"] is False
    assert result["missing"] == ["metro_score_v2", "seo_facts"]


def test_status_treats_persist_warning_as_partial_failure():
    persistence = {
        "ok": True,
        "report_exists": True,
        "metro_scores_count": 1,
        "metro_score_v2_count": 1,
        "seo_facts_count": 3,
        "missing": [],
    }

    assert (
        bulk_score._status_for_result(
            {"report_id": "report-1", "persist_warning": "save failed"},
            persistence,
        )
        == "partial_failure"
    )


def test_persistence_verification_error_records_query_failures():
    result = bulk_score.persistence_verification_error(RuntimeError("network failed"))

    assert result == {
        "ok": False,
        "report_exists": False,
        "metro_scores_count": 0,
        "metro_score_v2_count": 0,
        "seo_facts_count": 0,
        "missing": ["persistence_verification"],
        "error": "network failed",
    }


def test_error_for_status_distinguishes_api_and_persistence_failures():
    assert (
        bulk_score._error_for_status("failed", None, {})
        == "Scoring API request failed before returning a response."
    )
    assert (
        bulk_score._error_for_status("failed", {"foo": "bar"}, {})
        == "Scoring API returned a response without report_id."
    )
    assert (
        bulk_score._error_for_status(
            "partial_failure",
            {"report_id": "report-1", "persist_warning": "save failed"},
            {"missing": ["seo_facts"], "error": "query timed out"},
        )
        == "save failed; persistence verification failed: query timed out; missing seo_facts"
    )
    assert bulk_score._error_for_status("success", {"report_id": "report-1"}, {}) is None


def test_audit_record_omits_full_report_body_and_keeps_recovery_fields():
    record = bulk_score.build_audit_record(
        status="success",
        metro={
            "cbsa_code": "11111",
            "cbsa_name": "Austin-Round Rock-Georgetown, TX",
            "state": "TX",
            "population": 2_300_000,
            "population_class": "metro_1m_5m",
        },
        city_name="Austin",
        service="Roofing Services",
        api_url="http://localhost:8000",
        started_at=bulk_score.datetime(2026, 5, 21, tzinfo=bulk_score.timezone.utc),
        elapsed_ms=1200,
        result={
            "report_id": "report-1",
            "opportunity_score": 72,
            "classification_label": "Medium",
            "report": {"metros": [{"v2_scores": {"demand_strength": 100}}]},
        },
        persistence={
            "ok": True,
            "report_exists": True,
            "metro_scores_count": 1,
            "metro_score_v2_count": 1,
            "seo_facts_count": 3,
            "missing": [],
        },
    )

    assert "report" not in record
    assert record["request"]["niche_normalized"] == "roofing"
    assert record["score"]["score_system"] == "v2"
    assert record["persistence"]["seo_facts_count"] == 3


class FakeHealthResponse:
    status_code = 200


class FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, *_args, **_kwargs):
        return FakeHealthResponse()


def test_run_bulk_score_propagates_unexpected_worker_exceptions(monkeypatch):
    monkeypatch.setattr(bulk_score, "_load_env", lambda: None)
    monkeypatch.setattr(bulk_score, "_supabase_client", lambda: object())
    monkeypatch.setattr(
        bulk_score,
        "fetch_metros",
        lambda *_args, **_kwargs: [
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "state": "TX",
                "population": 2_300_000,
                "population_class": "metro_1m_5m",
            }
        ],
    )
    monkeypatch.setattr(bulk_score.httpx, "AsyncClient", lambda: FakeAsyncClient())

    async def fail_score(*_args, **_kwargs):
        raise RuntimeError("disk write failed")

    monkeypatch.setattr(bulk_score, "score_one", fail_score)
    args = SimpleNamespace(
        api_url=None,
        cities=1,
        services=1,
        resume=False,
        preview=False,
        concurrency=1,
        strategy="rank-and-rent",
        population_classes=None,
        min_population=None,
        max_population=None,
        require_dfs=True,
        mega_cap=5,
        require_v2_persistence=True,
    )

    with pytest.raises(RuntimeError, match="disk write failed"):
        asyncio.run(bulk_score.run_bulk_score(args))


def test_run_bulk_score_records_persistence_verification_errors(
    monkeypatch, tmp_path
):
    result_dir = tmp_path / "scripts" / "explore"
    result_dir.mkdir(parents=True)
    monkeypatch.setattr(bulk_score, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(bulk_score, "_load_env", lambda: None)
    monkeypatch.setattr(bulk_score, "_supabase_client", object)
    monkeypatch.setattr(
        bulk_score,
        "fetch_metros",
        lambda *_args, **_kwargs: [
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "state": "TX",
                "population": 2_300_000,
                "population_class": "metro_1m_5m",
            }
        ],
    )
    monkeypatch.setattr(bulk_score, "SERVICES", ["roofing"])
    monkeypatch.setattr(bulk_score.httpx, "AsyncClient", FakeAsyncClient)

    async def score_success(*_args, **_kwargs):
        return {"report_id": "report-1", "opportunity_score": 72}

    def fail_verify(*_args, **_kwargs):
        raise RuntimeError("query timed out")

    to_thread_calls = []

    async def fake_to_thread(func, *args, **kwargs):
        to_thread_calls.append(func)
        return func(*args, **kwargs)

    monkeypatch.setattr(bulk_score, "score_one", score_success)
    monkeypatch.setattr(bulk_score, "verify_persistence", fail_verify)
    monkeypatch.setattr(bulk_score.asyncio, "to_thread", fake_to_thread)
    args = SimpleNamespace(
        api_url=None,
        cities=1,
        services=1,
        resume=False,
        preview=False,
        concurrency=1,
        strategy="rank-and-rent",
        population_classes=None,
        min_population=None,
        max_population=None,
        require_dfs=True,
        mega_cap=5,
        require_v2_persistence=True,
    )

    asyncio.run(bulk_score.run_bulk_score(args))

    records = [
        json.loads(line)
        for line in (result_dir / "bulk_score_results.jsonl").read_text().splitlines()
    ]
    assert to_thread_calls == [fail_verify]
    assert records[0]["status"] == "partial_failure"
    assert records[0]["persistence"]["missing"] == ["persistence_verification"]
    assert records[0]["error"] == (
        "persistence verification failed: query timed out; "
        "missing persistence_verification"
    )


class FakeRpcCall:
    def __init__(self, error=None):
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return FakeResponse([])


class FakePostgrest:
    def auth(self, _key):
        return None


class FakeRpcSupabase:
    def __init__(self, errors_by_rpc=None):
        self.errors_by_rpc = errors_by_rpc or {}
        self.rpc_names: list[str] = []
        self.postgrest = FakePostgrest()

    def rpc(self, name, _args):
        self.rpc_names.append(name)
        return FakeRpcCall(self.errors_by_rpc.get(name))


def test_refresh_matview_fallback_runs_only_for_missing_rpc(monkeypatch):
    monkeypatch.setattr(bulk_score, "_load_env", lambda: None)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    missing_rpc = RuntimeError(
        "Could not find the function public._refresh_explore_market_cells in the schema cache"
    )
    supabase = FakeRpcSupabase(
        errors_by_rpc={"_refresh_explore_market_cells": missing_rpc}
    )
    monkeypatch.setattr(bulk_score, "_supabase_client", lambda: supabase)

    bulk_score.refresh_matview_sql()

    assert supabase.rpc_names == ["_refresh_explore_market_cells", "exec_sql"]


def test_refresh_matview_raises_non_missing_rpc_errors(monkeypatch):
    monkeypatch.setattr(bulk_score, "_load_env", lambda: None)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    supabase = FakeRpcSupabase(
        errors_by_rpc={"_refresh_explore_market_cells": RuntimeError("network failed")}
    )
    monkeypatch.setattr(bulk_score, "_supabase_client", lambda: supabase)

    with pytest.raises(RuntimeError, match="network failed"):
        bulk_score.refresh_matview_sql()

    assert supabase.rpc_names == ["_refresh_explore_market_cells"]
