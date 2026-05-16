from src.clients.strategy_repository import StrategyRepository


class FakeTable:
    def __init__(self, rows=None):
        self.calls = []
        self.rows = rows or []

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

    def execute(self):
        return type("Response", (), {"data": self.rows})()


class FakeClient:
    def __init__(self, rows_by_table=None):
        self.tables = {}
        self.rows_by_table = rows_by_table or {}

    def table(self, name):
        self.tables[name] = FakeTable(self.rows_by_table.get(name))
        return self.tables[name]


def test_fetch_cached_markets_reads_canonical_tables() -> None:
    client = FakeClient(rows_by_table={"metro_score_v2": [{"cbsa_code": "13820"}]})
    repo = StrategyRepository(client)
    rows = repo.fetch_cached_markets(
        niche_normalized="roofing", cbsa_code="13820", limit=25
    )
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
