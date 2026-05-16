from src.clients.strategy_repository import StrategyRepository


class FakeError:
    message = "database write failed"


class FakeTable:
    def __init__(self, rows=None, error=None):
        self.calls = []
        self.rows = rows or []
        self.error = error

    def select(self, value):
        self.calls.append(("select", value))
        return self

    def eq(self, key, value):
        self.calls.append(("eq", key, value))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def order(self, key, **kwargs):
        self.calls.append(("order", key, kwargs))
        return self

    def insert(self, value):
        self.calls.append(("insert", value))
        return self

    def execute(self):
        return type("Response", (), {"data": self.rows, "error": self.error})()


class FakeClient:
    def __init__(self, rows_by_table=None, errors_by_table=None):
        self.tables = {}
        self.rows_by_table = rows_by_table or {}
        self.errors_by_table = errors_by_table or {}

    def table(self, name):
        self.tables[name] = FakeTable(self.rows_by_table.get(name), self.errors_by_table.get(name))
        return self.tables[name]


def test_fetch_cached_markets_reads_canonical_tables() -> None:
    client = FakeClient(rows_by_table={"metro_score_v2": [{"cbsa_code": "13820"}]})
    repo = StrategyRepository(client)
    rows = repo.fetch_cached_markets(niche_normalized="roofing", cbsa_code="13820", limit=25)
    assert "metro_score_v2" in client.tables
    calls = client.tables["metro_score_v2"].calls
    assert rows == [{"cbsa_code": "13820"}]
    assert ("select", "*") in calls
    assert ("eq", "niche_normalized", "roofing") in calls
    assert ("eq", "cbsa_code", "13820") in calls
    assert ("limit", 25) in calls


def test_fetch_local_pack_facts_filters_keyword_and_niche() -> None:
    client = FakeClient()
    repo = StrategyRepository(client)
    repo.fetch_local_pack_facts(
        cbsa_code="13820", niche_normalized="roofing", keyword="boise roofing"
    )
    calls = client.tables["local_pack_listing_facts"].calls
    assert ("eq", "cbsa_code", "13820") in calls
    assert ("eq", "niche_normalized", "roofing") in calls
    assert ("eq", "keyword", "boise roofing") in calls
    assert ("order", "snapshot_date", {"desc": True}) in calls
    assert ("order", "listing_rank", {}) in calls


def test_create_run_inserts_strategy_run_payload() -> None:
    payload = {
        "id": "run-1",
        "strategy_id": "easy_win",
        "mode": "fresh",
        "status": "queued",
    }
    client = FakeClient(rows_by_table={"strategy_runs": [payload]})
    repo = StrategyRepository(client)

    row = repo.create_run(payload)

    assert row == payload
    assert client.tables["strategy_runs"].calls == [("insert", payload)]


def test_create_run_raises_on_supabase_error() -> None:
    client = FakeClient(errors_by_table={"strategy_runs": FakeError()})
    repo = StrategyRepository(client)

    try:
        repo.create_run({"id": "run-1"})
    except RuntimeError as exc:
        assert "database write failed" in str(exc)
    else:
        raise AssertionError("Expected create_run to raise on Supabase error")


def test_create_run_requires_returned_run_id() -> None:
    client = FakeClient(rows_by_table={"strategy_runs": [{}]})
    repo = StrategyRepository(client)

    try:
        repo.create_run({"id": "run-1"})
    except RuntimeError as exc:
        assert "no run id" in str(exc)
    else:
        raise AssertionError("Expected create_run to require a returned run id")


def test_insert_run_items_inserts_rows_and_skips_empty_batch() -> None:
    rows = [
        {
            "run_id": "run-1",
            "rank": 1,
            "strategy_id": "easy_win",
            "cbsa_code": "13820",
            "niche_normalized": "roofing",
            "niche_keyword": "roof repair",
            "score": 87.5,
        }
    ]
    client = FakeClient(rows_by_table={"strategy_run_items": rows})
    repo = StrategyRepository(client)

    assert repo.insert_run_items([]) == []
    inserted = repo.insert_run_items(rows)

    assert inserted == rows
    assert client.tables["strategy_run_items"].calls == [("insert", rows)]


def test_insert_run_items_raises_on_supabase_error() -> None:
    rows = [{"run_id": "run-1", "rank": 1}]
    client = FakeClient(errors_by_table={"strategy_run_items": FakeError()})
    repo = StrategyRepository(client)

    try:
        repo.insert_run_items(rows)
    except RuntimeError as exc:
        assert "database write failed" in str(exc)
    else:
        raise AssertionError("Expected insert_run_items to raise on Supabase error")


def test_insert_run_items_requires_returned_rows() -> None:
    rows = [{"run_id": "run-1", "rank": 1}]
    client = FakeClient(rows_by_table={"strategy_run_items": []})
    repo = StrategyRepository(client)

    try:
        repo.insert_run_items(rows)
    except RuntimeError as exc:
        assert "returned no rows" in str(exc)
    else:
        raise AssertionError("Expected insert_run_items to require returned rows")
