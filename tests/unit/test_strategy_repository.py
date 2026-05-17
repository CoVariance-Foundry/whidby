from src.clients.strategy_repository import StrategyRepository
from src.domain.lenses import EASY_WIN, EXPAND_CONQUER
from src.domain.queries import CityFilter, MarketQuery, ServiceFilter


class FakeError:
    message = "database write failed"


class FakeTable:
    def __init__(self, rows=None, error=None):
        self.calls = []
        self.rows = rows or []
        self.error = error
        self.filters = []
        self.limit_value = None

    def select(self, value):
        self.calls.append(("select", value))
        return self

    def eq(self, key, value):
        self.calls.append(("eq", key, value))
        self.filters.append((key, value))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        self.limit_value = value
        return self

    def order(self, key, **kwargs):
        self.calls.append(("order", key, kwargs))
        return self

    def insert(self, value):
        self.calls.append(("insert", value))
        return self

    def execute(self):
        rows = list(self.rows)
        for key, value in self.filters:
            rows = [row for row in rows if row.get(key) == value]
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return type("Response", (), {"data": rows, "error": self.error})()


class FakeClient:
    def __init__(self, rows_by_table=None, errors_by_table=None):
        self.tables = {}
        self.rows_by_table = rows_by_table or {}
        self.errors_by_table = errors_by_table or {}

    def table(self, name):
        self.tables[name] = FakeTable(self.rows_by_table.get(name), self.errors_by_table.get(name))
        return self.tables[name]


def test_fetch_cached_markets_reads_canonical_tables() -> None:
    client = FakeClient(
        rows_by_table={
            "metro_score_v2": [{"cbsa_code": "13820", "niche_normalized": "roofing"}]
        }
    )
    repo = StrategyRepository(client)
    rows = repo.fetch_cached_markets(niche_normalized="roofing", cbsa_code="13820", limit=25)
    assert "metro_score_v2" in client.tables
    calls = client.tables["metro_score_v2"].calls
    assert rows == [{"cbsa_code": "13820", "niche_normalized": "roofing"}]
    assert ("select", "*, metros(*)") in calls
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


def test_query_markets_maps_v2_rows_to_domain_markets() -> None:
    client = FakeClient(
        rows_by_table={
            "metro_score_v2": [
                {
                    "report_id": "report-1",
                    "cbsa_code": "13820",
                    "niche_normalized": "roofing",
                    "demand_strength": 140,
                    "organic_difficulty": 20,
                    "local_difficulty": 30,
                    "monetization_signal": 120,
                    "ai_resilience": 55,
                    "benchmark_confidence": "high",
                    "no_local_pack_detected": False,
                    "metros": {
                        "cbsa_code": "13820",
                        "cbsa_name": "Boise City, ID",
                        "state": "ID",
                        "population": 750000,
                    },
                }
            ]
        }
    )
    repo = StrategyRepository(client)

    markets = repo.query_markets(
        MarketQuery(
            lens=EASY_WIN,
            city_filters=[CityFilter("cbsa_code", "=", "13820")],
            service_filters=[ServiceFilter("name", "like", "roofing")],
            ai_resilience_filter=True,
        )
    )

    assert len(markets) == 1
    market = markets[0]
    assert market.city.name == "Boise City, ID"
    assert market.city.cbsa_code == "13820"
    assert market.service.name == "Roofing"
    assert market.report_id == "report-1"
    assert market.signals["demand"]["score"] == 140.0
    assert market.signals["strategy_row"]["local_pack_present"] is True
    calls = client.tables["metro_score_v2"].calls
    assert ("eq", "niche_normalized", "roofing") in calls
    assert ("eq", "cbsa_code", "13820") in calls


def test_query_markets_hydrates_expand_conquer_reference_inputs() -> None:
    client = FakeClient(
        rows_by_table={
            "metro_score_v2": [
                {
                    "cbsa_code": "13820",
                    "niche_normalized": "roofing",
                    "organic_difficulty": 25,
                    "local_difficulty": 30,
                    "demand_strength": 120,
                },
                {
                    "cbsa_code": "11111",
                    "niche_normalized": "roofing",
                    "organic_difficulty": 45,
                    "local_difficulty": 50,
                    "demand_strength": 120,
                },
            ],
            "metro_feature_vectors": [
                {
                    "cbsa_code": "13820",
                    "feature_version": "strategy_v1",
                    "feature_vector": [1.0, 0.0],
                },
                {
                    "cbsa_code": "11111",
                    "feature_version": "strategy_v1",
                    "feature_vector": [1.0, 0.0],
                },
            ],
        }
    )
    repo = StrategyRepository(client)

    markets = repo.query_markets(
        MarketQuery(
            lens=EXPAND_CONQUER,
            service_filters=[ServiceFilter("name", "like", "roofing")],
            reference_city_id="11111",
        )
    )

    candidate = next(m for m in markets if m.city.cbsa_code == "13820")
    row = candidate.signals["strategy_row"]
    assert row["similarity_score"] == 1.0
    assert row["reference_organic_difficulty"] == 45
    assert row["reference_local_difficulty"] == 50


def test_query_markets_maps_ai_exposure_to_aio_trigger_rate() -> None:
    client = FakeClient(
        rows_by_table={
            "metro_score_v2": [
                {
                    "cbsa_code": "13820",
                    "niche_normalized": "roofing",
                    "ai_exposure": "AI_EXPOSED",
                }
            ]
        }
    )
    repo = StrategyRepository(client)

    markets = repo.query_markets(MarketQuery(lens=EASY_WIN))

    assert markets[0].signals["strategy_row"]["aio_trigger_rate"] == 0.2


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
