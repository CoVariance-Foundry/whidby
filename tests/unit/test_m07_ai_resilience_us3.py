"""US3 tests for AI resilience niche-type split behavior."""

from src.scoring.ai_resilience_score import compute_ai_resilience_score
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_local_service_niche_scores_higher_than_informational_with_same_exposure() -> None:
    shared = {
        "aio_trigger_rate": 0.18,
        "transactional_keyword_ratio": 0.50,
        "local_fulfillment_required": 1.0,
        "paa_density": 2.0,
    }
    local_service = compute_ai_resilience_score(metro_signal(niche_type="local_service", **shared))
    informational = compute_ai_resilience_score(metro_signal(niche_type="informational", **shared))
    assert local_service > informational


def test_high_aio_in_informational_niche_stays_low() -> None:
    score = compute_ai_resilience_score(
        metro_signal(
            niche_type="informational",
            aio_trigger_rate=0.45,
            transactional_keyword_ratio=0.10,
            paa_density=6.0,
            local_fulfillment_required=0.0,
        )
    )
    assert score < 40.0

