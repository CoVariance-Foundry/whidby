import asyncio
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

    def select(self, _columns):
        return self

    def range(self, start, end):
        self.ranges.append((start, end))
        self._range = (start, end)
        return self

    def execute(self):
        start, end = getattr(self, "_range", (0, len(self._rows) - 1))
        return FakeResponse(self._rows[start : end + 1])


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
        "fetch_top_metros",
        lambda _supabase, _limit: [
            {
                "cbsa_code": "11111",
                "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                "state": "TX",
                "population": 2_300_000,
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
    )

    with pytest.raises(RuntimeError, match="disk write failed"):
        asyncio.run(bulk_score.run_bulk_score(args))


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
