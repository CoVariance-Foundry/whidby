from src.domain.entities import City, Service, Market, SeasonalityCurve, ScoredMarket


def test_city_minimal_creation():
    city = City(city_id="boise-id", name="Boise")
    assert city.city_id == "boise-id"
    assert city.name == "Boise"
    assert city.population is None
    assert city.demographics == {}


def test_city_is_frozen():
    city = City(city_id="boise-id", name="Boise")
    try:
        city.name = "Not Boise"
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass


def test_city_with_full_data():
    city = City(
        city_id="boise-id",
        name="Boise",
        state="ID",
        population=235_000,
        median_income=58_000,
        growth_rate=0.032,
        archetype="Growth Sunbelt",
        demographics={"pct_owner_occupied": 0.65},
    )
    assert city.population == 235_000
    assert city.archetype == "Growth Sunbelt"


def test_service_minimal_creation():
    svc = Service(service_id="plumbing", name="Plumbing")
    assert svc.fulfillment_type == "physical"
    assert svc.keyword_universe == []


def test_market_links_city_and_service():
    city = City(city_id="boise-id", name="Boise")
    svc = Service(service_id="plumbing", name="Plumbing")
    market = Market(city=city, service=svc)
    assert market.city.city_id == "boise-id"
    assert market.service.service_id == "plumbing"
    assert market.signals == {}
    assert market.scores is None


def test_seasonality_curve():
    curve = SeasonalityCurve(
        monthly_index={1: 0.3, 2: 0.4, 6: 1.0, 12: 0.2},
        peak_month=6,
        trough_month=12,
        amplitude=0.8,
    )
    assert curve.peak_month == 6
    assert curve.amplitude == 0.8


def test_scored_market():
    city = City(city_id="boise-id", name="Boise")
    svc = Service(service_id="plumbing", name="Plumbing")
    market = Market(city=city, service=svc)
    scored = ScoredMarket(
        market=market,
        opportunity_score=78.5,
        lens_id="easy_win",
        rank=1,
        score_breakdown={"demand": 20.0, "competition": 25.0},
    )
    assert scored.opportunity_score == 78.5
    assert scored.lens_id == "easy_win"
