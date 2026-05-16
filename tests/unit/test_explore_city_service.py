from src.domain.services.explore_city_service import ExploreCityService


class FakeExploreRepository:
    def load_metros(self) -> list[dict]:
        return [
            {
                "cbsa_code": "38060",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "state": "AZ",
                "population": 100_000,
                "population_class": "medium_100_300k",
                "median_household_income_usd": 82_000,
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
    service = ExploreCityService(FakeExploreRepository())

    summaries = service.list_cities(service_filter="roofing")

    assert len(summaries) == 1
    city = summaries[0]
    assert city["cbsa_code"] == "38060"
    assert city["population"] == 100_000
    assert city["median_household_income_usd"] == 82_000
    assert city["business_density_per_1k"] == 2.5
    assert city["establishment_growth_yoy"] == 0.25
    assert city["growth_available"] is True
    assert city["cached_services_count"] == 1
    assert city["best_score"] == 81
