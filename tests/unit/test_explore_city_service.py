from src.domain.services.explore_city_service import ExploreCityService


class FakeExploreRepository:
    metric_filter: str | None = None

    def load_metros(self) -> list[dict]:
        return [
            {
                "cbsa_code": "38060",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "state": "AZ",
                "population": 100_000,
                "population_class": "medium_100_300k",
                "median_household_income_usd": 82_000,
                "owner_occupancy_rate": 0.61,
                "median_age_years": 37.4,
            }
        ]

    def load_scores(self, cbsa_codes: list[str]) -> list[dict]:
        return [
            {
                "cbsa_code": "38060",
                "niche_normalized": "roofing",
                "niche_keyword": "roofing",
                "presentation_score": 81,
                "score_system": "legacy",
            }
        ]

    def load_metric_inputs(self, cbsa_codes: list[str], niche_normalized: str) -> dict:
        self.metric_filter = niche_normalized
        return {
            "weights_by_naics": {"238160": 1.0},
            "latest_year": 2022,
            "prior_year": 2021,
            "cbp_rows": {
                ("38060", 2022): [{"naics_code": "238160", "est": 250}],
                ("38060", 2021): [{"naics_code": "238160", "est": 200}],
            },
        }


def test_city_service_combines_demographics_scores_and_metrics() -> None:
    repository = FakeExploreRepository()
    service = ExploreCityService(repository)

    summaries = service.list_cities(service_filter="Roofing Services")

    assert len(summaries) == 1
    city = summaries[0]
    assert city["cbsa_code"] == "38060"
    assert city["population"] == 100_000
    assert city["median_household_income_usd"] == 82_000
    assert city["owner_occupancy_rate"] == 0.61
    assert city["median_age_years"] == 37.4
    assert city["business_density_per_1k"] == 2.5
    assert city["establishment_growth_yoy"] == 0.25
    assert city["growth_available"] is True
    assert city["cached_services_count"] == 1
    assert city["best_score"] == 81
    assert repository.metric_filter == "roofing"


def test_city_service_collapses_report_scores_to_latest_unique_services() -> None:
    class Repository(FakeExploreRepository):
        def load_scores(self, cbsa_codes: list[str]) -> list[dict]:
            return [
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "roofing",
                    "niche_keyword": "roofing",
                    "presentation_score": 92,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-01T12:00:00Z",
                },
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "roofing",
                    "niche_keyword": "roofing",
                    "presentation_score": 77,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-03T12:00:00Z",
                },
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "plumbing",
                    "niche_keyword": "plumbing",
                    "presentation_score": 83,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-02T12:00:00Z",
                },
            ]

    city = ExploreCityService(Repository()).list_cities()[0]

    assert city["cached_services_count"] == 2
    assert {score["niche_normalized"] for score in city["cached_scores"]} == {
        "roofing",
        "plumbing",
    }
    roofing = next(
        score for score in city["cached_scores"] if score["niche_normalized"] == "roofing"
    )
    assert roofing["presentation_score"] == 77
    assert roofing["last_scored_at"] == "2026-05-03T12:00:00Z"
    assert city["last_scored_at"] == "2026-05-03T12:00:00Z"


def test_city_service_summary_freshness_uses_latest_score_row() -> None:
    class Repository(FakeExploreRepository):
        def load_scores(self, cbsa_codes: list[str]) -> list[dict]:
            return [
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "roofing",
                    "niche_keyword": "roofing",
                    "presentation_score": 97,
                    "score_system": "legacy",
                    "last_scored_at": "2026-04-01T12:00:00Z",
                    "stale": True,
                },
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "plumbing",
                    "niche_keyword": "plumbing",
                    "presentation_score": 71,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-05T12:00:00Z",
                    "stale": False,
                },
            ]

    city = ExploreCityService(Repository()).list_cities()[0]

    assert city["best_score"] == 97
    assert city["last_scored_at"] == "2026-05-05T12:00:00Z"
    assert city["stale"] is False


def test_city_service_orders_equal_cached_scores_newest_first() -> None:
    class Repository(FakeExploreRepository):
        def load_scores(self, cbsa_codes: list[str]) -> list[dict]:
            return [
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "roofing",
                    "niche_keyword": "roofing",
                    "presentation_score": 88,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-01T12:00:00Z",
                },
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "plumbing",
                    "niche_keyword": "plumbing",
                    "presentation_score": 88,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-04T12:00:00Z",
                },
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "hvac",
                    "niche_keyword": "hvac",
                    "presentation_score": 82,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-06T12:00:00Z",
                },
            ]

    city = ExploreCityService(Repository()).list_cities()[0]

    assert [score["niche_normalized"] for score in city["cached_scores"]] == [
        "plumbing",
        "roofing",
        "hvac",
    ]


def test_city_service_prefers_v2_over_legacy_for_same_service() -> None:
    class Repository(FakeExploreRepository):
        def load_scores(self, cbsa_codes: list[str]) -> list[dict]:
            return [
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "roofing",
                    "niche_keyword": "roofing",
                    "presentation_score": 99,
                    "score_system": "legacy",
                    "last_scored_at": "2026-05-03T12:00:00Z",
                },
                {
                    "cbsa_code": "38060",
                    "niche_normalized": "roofing",
                    "niche_keyword": "roofing",
                    "presentation_score": 74,
                    "score_system": "v2",
                    "last_scored_at": "2026-05-02T12:00:00Z",
                },
            ]

    city = ExploreCityService(Repository()).list_cities(service_filter="roofing")[0]

    assert city["cached_services_count"] == 1
    assert city["best_score"] == 74
    assert city["score_system"] == "v2"
    assert city["cached_scores"][0]["score_system"] == "v2"


def test_city_service_preserves_city_freshness_fields() -> None:
    class Repository(FakeExploreRepository):
        def load_metros(self) -> list[dict]:
            metro = super().load_metros()[0]
            metro["last_scored_at"] = "2026-05-04T12:00:00Z"
            metro["stale"] = False
            return [metro]

    city = ExploreCityService(Repository()).list_cities(service_filter="roofing")[0]

    assert city["last_scored_at"] == "2026-05-04T12:00:00Z"
    assert city["stale"] is False
