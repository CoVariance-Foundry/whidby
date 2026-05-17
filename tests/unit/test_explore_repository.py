import pytest

from src.clients.explore_repository import SupabaseExploreRepository


class FakeError:
    message = "database read failed"


class FakeTable:
    def __init__(self, rows=None, error=None):
        self.calls = []
        self.rows = rows or []
        self.error = error
        self.filters = []
        self.in_filters = []
        self.orders = []
        self.limit_value = None
        self.range_value = None
        self.execute_exception = None

    def select(self, value):
        self.calls.append(("select", value))
        return self

    def eq(self, key, value):
        self.calls.append(("eq", key, value))
        self.filters.append(("eq", key, value))
        return self

    def in_(self, key, values):
        values = list(values)
        self.calls.append(("in_", key, values))
        self.in_filters.append((key, values))
        return self

    def gte(self, key, value):
        self.calls.append(("gte", key, value))
        self.filters.append(("gte", key, value))
        return self

    def lte(self, key, value):
        self.calls.append(("lte", key, value))
        self.filters.append(("lte", key, value))
        return self

    def gt(self, key, value):
        self.calls.append(("gt", key, value))
        self.filters.append(("gt", key, value))
        return self

    def order(self, key, **kwargs):
        if "ascending" in kwargs:
            raise AssertionError("FakeTable only supports PostgREST desc= ordering")
        self.calls.append(("order", key, kwargs))
        self.orders.append((key, kwargs))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        self.limit_value = value
        return self

    def range(self, start, end):
        self.calls.append(("range", start, end))
        self.range_value = (start, end)
        return self

    def execute(self):
        if self.execute_exception is not None:
            raise self.execute_exception
        rows = list(self.rows)
        for operator, key, value in self.filters:
            if operator == "eq":
                rows = [row for row in rows if row.get(key) == value]
            if operator == "gte":
                rows = [row for row in rows if row.get(key) >= value]
            if operator == "lte":
                rows = [row for row in rows if row.get(key) <= value]
            if operator == "gt":
                rows = [row for row in rows if row.get(key) > value]
        for key, values in self.in_filters:
            rows = [row for row in rows if row.get(key) in values]
        for key, kwargs in reversed(self.orders):
            desc = kwargs.get("desc", False)
            rows = sorted(
                rows,
                key=lambda row: (row.get(key) is None, row.get(key)),
                reverse=desc,
            )
        if self.range_value is not None:
            start, end = self.range_value
            rows = rows[start : end + 1]
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return type("Response", (), {"data": rows, "error": self.error})()


class FakeClient:
    def __init__(self, rows_by_table=None, errors_by_table=None):
        self.tables = {}
        self.rows_by_table = rows_by_table or {}
        self.errors_by_table = errors_by_table or {}
        self.execute_exceptions_by_table = {}

    def table(self, name):
        table = FakeTable(self.rows_by_table.get(name), self.errors_by_table.get(name))
        table.execute_exception = self.execute_exceptions_by_table.get(name)
        self.tables[name] = table
        return table


def test_list_city_rows_applies_service_demographic_and_state_filters() -> None:
    client = FakeClient()
    repo = SupabaseExploreRepository(client)

    repo.list_city_rows(
        service="Roofing Services",
        states=["AZ", "TX"],
        population_min=100_000,
        population_max=900_000,
        income_min=60_000,
        income_max=120_000,
        growing_only=True,
        sort="population",
        direction="asc",
        limit=25,
        cursor="25",
    )

    calls = client.tables["explore_market_cells"].calls
    assert ("select", "*") in calls
    assert ("eq", "niche_normalized", "roofing") in calls
    assert ("in_", "state", ["AZ", "TX"]) in calls
    assert ("gte", "population", 100_000) in calls
    assert ("lte", "population", 900_000) in calls
    assert ("gte", "median_household_income_usd", 60_000) in calls
    assert ("lte", "median_household_income_usd", 120_000) in calls
    assert ("gt", "establishment_growth_yoy", 0) in calls
    assert ("gt", "cbsa_code", "11111") not in calls
    assert ("order", "population", {"desc": False}) in calls
    assert ("order", "cbsa_code", {"desc": False}) in calls
    assert ("range", 25, 50) in calls


def test_list_city_rows_without_service_filters_representative_rows() -> None:
    client = FakeClient()
    repo = SupabaseExploreRepository(client)

    repo.list_city_rows(
        service=None,
        states=[],
        population_min=None,
        population_max=None,
        income_min=None,
        income_max=None,
        growing_only=False,
        sort="score",
        direction="desc",
        limit=10,
        cursor=None,
    )

    calls = client.tables["explore_market_cells"].calls
    assert ("eq", "representative_service_rank", 1) in calls
    assert ("order", "presentation_score", {"desc": True}) in calls
    assert ("range", 0, 10) in calls
    assert ("limit", 11) not in calls


def test_list_city_rows_uses_offset_cursor_for_any_sort() -> None:
    client = FakeClient()
    repo = SupabaseExploreRepository(client)

    repo.list_city_rows(
        service="roofing",
        states=[],
        population_min=None,
        population_max=None,
        income_min=None,
        income_max=None,
        growing_only=False,
        sort="business_density",
        direction="desc",
        limit=10,
        cursor="25",
    )

    calls = client.tables["explore_market_cells"].calls
    assert ("order", "business_density_per_1k", {"desc": True}) in calls
    assert ("order", "cbsa_code", {"desc": False}) in calls
    assert ("range", 25, 35) in calls
    assert not any(call[:2] == ("gt", "cbsa_code") for call in calls)


def test_list_city_rows_raises_on_supabase_errors() -> None:
    client = FakeClient(errors_by_table={"explore_market_cells": FakeError()})
    repo = SupabaseExploreRepository(client)

    with pytest.raises(RuntimeError, match="Supabase request failed: database read failed"):
        repo.list_city_rows(
            service=None,
            states=[],
            population_min=None,
            population_max=None,
            income_min=None,
            income_max=None,
            growing_only=False,
            sort="score",
            direction="desc",
            limit=10,
            cursor=None,
        )


def test_list_city_rows_wraps_execute_exceptions() -> None:
    client = FakeClient()
    client.execute_exceptions_by_table["explore_market_cells"] = ValueError("network down")
    repo = SupabaseExploreRepository(client)

    with pytest.raises(RuntimeError, match="Supabase request failed: network down"):
        repo.list_city_rows(
            service=None,
            states=[],
            population_min=None,
            population_max=None,
            income_min=None,
            income_max=None,
            growing_only=False,
            sort="score",
            direction="desc",
            limit=10,
            cursor=None,
        )


def test_load_city_detail_returns_city_with_cached_scores() -> None:
    rows = [
        {
            "cbsa_code": "38060",
            "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
            "state": "AZ",
            "population": 4_900_000,
            "population_class": "large_1m_plus",
            "median_household_income_usd": 82_000,
            "owner_occupancy_rate": 0.61,
            "median_age_years": 37.4,
            "niche_normalized": "roofing",
            "niche_keyword": "roofing",
            "presentation_score": 88,
            "score_system": "v2",
            "latest_scored_at": "2026-05-01T12:00:00Z",
        },
        {
            "cbsa_code": "38060",
            "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
            "state": "AZ",
            "population": 4_900_000,
            "population_class": "large_1m_plus",
            "median_household_income_usd": 82_000,
            "niche_normalized": "plumbing",
            "niche_keyword": "plumbing",
            "presentation_score": 72,
            "score_system": "legacy",
        },
    ]
    client = FakeClient(rows_by_table={"explore_market_cells": rows})
    repo = SupabaseExploreRepository(client)

    detail = repo.load_city_detail("38060")

    assert detail is not None
    assert detail["cbsa_code"] == "38060"
    assert detail["population"] == 4_900_000
    assert [score["niche_normalized"] for score in detail["cached_scores"]] == [
        "roofing",
        "plumbing",
    ]
    calls = client.tables["explore_market_cells"].calls
    assert ("eq", "cbsa_code", "38060") in calls
    assert ("order", "presentation_score", {"desc": True}) in calls


def test_load_city_detail_returns_none_when_no_rows() -> None:
    client = FakeClient(rows_by_table={"explore_market_cells": []})
    repo = SupabaseExploreRepository(client)

    assert repo.load_city_detail("00000") is None


def test_load_city_detail_filters_malformed_cached_score_rows() -> None:
    rows = [
        {
            "cbsa_code": "38060",
            "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
            "state": "AZ",
            "niche_normalized": "roofing",
            "presentation_score": 88,
        },
        {
            "cbsa_code": "38060",
            "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
            "state": "AZ",
            "niche_normalized": None,
            "presentation_score": None,
        },
    ]
    client = FakeClient(rows_by_table={"explore_market_cells": rows})
    repo = SupabaseExploreRepository(client)

    detail = repo.load_city_detail("38060")

    assert detail is not None
    assert [score["niche_normalized"] for score in detail["cached_scores"]] == [
        "roofing"
    ]


def test_load_city_detail_wraps_execute_exceptions() -> None:
    client = FakeClient()
    client.execute_exceptions_by_table["explore_market_cells"] = ValueError("timeout")
    repo = SupabaseExploreRepository(client)

    with pytest.raises(RuntimeError, match="Supabase request failed: timeout"):
        repo.load_city_detail("38060")
