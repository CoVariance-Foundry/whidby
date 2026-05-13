from src.domain.entities import City, Service, Market
from src.domain.lenses import EASY_WIN
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter


def test_empty_query_defaults():
    q = MarketQuery()
    assert q.lens.lens_id == "balanced"
    assert q.city_filters == []
    assert q.service_filters == []
    assert q.limit == 50


def test_city_filter_composition():
    q = MarketQuery(
        city_filters=[
            CityFilter("population", ">", 200_000),
            CityFilter("archetype", "=", "Growth Sunbelt"),
        ],
        lens=EASY_WIN,
    )
    assert q.has_city_filters()
    assert not q.has_service_filters()
    assert len(q.city_filters) == 2
    assert q.lens.lens_id == "easy_win"


def test_service_filter_composition():
    q = MarketQuery(
        service_filters=[
            ServiceFilter("fulfillment_type", "=", "physical"),
            ServiceFilter("acv_estimate", ">", 5000),
        ],
    )
    assert q.has_service_filters()
    assert not q.has_city_filters()


def test_portfolio_query():
    existing = Market(
        city=City(city_id="boise-id", name="Boise"),
        service=Service(service_id="plumbing", name="Plumbing"),
    )
    q = MarketQuery(portfolio_context=[existing])
    assert q.is_portfolio_query()
    assert not q.is_expansion_query()


def test_expansion_query():
    boise = City(city_id="boise-id", name="Boise", state="ID")
    q = MarketQuery(reference_city=boise)
    assert q.is_expansion_query()
    assert not q.is_portfolio_query()


def test_combined_filters_and_lens():
    q = MarketQuery(
        city_filters=[CityFilter("population", ">", 200_000)],
        service_filters=[ServiceFilter("fulfillment_type", "=", "physical")],
        lens=EASY_WIN,
        limit=25,
    )
    assert q.has_city_filters()
    assert q.has_service_filters()
    assert q.lens.lens_id == "easy_win"
    assert q.limit == 25
