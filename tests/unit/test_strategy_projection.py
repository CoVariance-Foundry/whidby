from src.domain.strategy_projection import (
    project_ai_resilience_warning,
    project_easy_win,
    project_expand_conquer,
    project_gbp_blitz,
    project_keyword_hijack,
)


def test_easy_win_rewards_demand_and_low_difficulty() -> None:
    row = {
        "demand_strength": 140,
        "organic_difficulty": 22,
        "local_difficulty": 35,
        "ai_resilience": 88,
        "benchmark_confidence": "high",
    }
    result = project_easy_win(row)
    assert result.score >= 80
    assert result.evidence["organic_difficulty"] == 22


def test_easy_win_treats_zero_organic_difficulty_as_strong() -> None:
    result = project_easy_win(
        {
            "demand_strength": 140,
            "organic_difficulty": 0,
            "local_difficulty": 0,
            "ai_resilience": 88,
        }
    )
    assert result.score >= 90
    assert result.evidence["organic_difficulty"] == 0


def test_gbp_blitz_rewards_low_review_barrier() -> None:
    result = project_gbp_blitz(
        {
            "demand_strength": 120,
            "local_pack_present": True,
            "top3_review_count_min": 12,
            "top3_review_velocity_avg": 0.8,
            "gbp_completeness_avg": 0.42,
        }
    )
    assert result.score >= 75
    assert result.evidence["top3_review_count_min"] == 12


def test_gbp_blitz_treats_zero_barriers_as_strong() -> None:
    result = project_gbp_blitz(
        {
            "demand_strength": 120,
            "local_pack_present": True,
            "top3_review_count_min": 0,
            "top3_review_velocity_avg": 0,
            "gbp_completeness_avg": 0,
        }
    )
    assert result.score >= 95
    assert result.evidence["top3_review_count_min"] == 0
    assert result.evidence["top3_review_velocity_avg"] == 0
    assert result.evidence["gbp_completeness_avg"] == 0


def test_keyword_hijack_requires_volume_pack_and_available_name() -> None:
    result = project_keyword_hijack(
        {
            "search_volume_monthly": 260,
            "cpc_usd": 38.5,
            "local_pack_present": True,
            "exact_match_name_taken": False,
            "commercial_intent_score": 0.9,
        }
    )
    assert result.score >= 80
    assert "exact_match_name_available" in result.evidence


def test_keyword_hijack_fails_closed_when_hard_gate_data_missing() -> None:
    result = project_keyword_hijack(
        {
            "cpc_usd": 38.5,
            "commercial_intent_score": 0.9,
        }
    )
    assert result.score == 0
    assert "primary_keyword_volume_missing" in result.warnings


def test_keyword_hijack_blocks_low_volume() -> None:
    result = project_keyword_hijack(
        {
            "search_volume_monthly": 90,
            "cpc_usd": 38.5,
            "local_pack_present": True,
            "exact_match_name_taken": False,
            "commercial_intent_score": 0.9,
        }
    )
    assert result.score == 0
    assert "primary_keyword_volume_below_200" in result.warnings


def test_keyword_hijack_does_not_default_zero_commercial_intent() -> None:
    result = project_keyword_hijack(
        {
            "search_volume_monthly": 260,
            "cpc_usd": 38.5,
            "local_pack_present": True,
            "exact_match_name_taken": False,
            "commercial_intent_score": 0,
        }
    )
    assert result.score < 70


def test_expand_conquer_rewards_similarity_with_lower_competition() -> None:
    result = project_expand_conquer(
        {
            "similarity_score": 0.92,
            "organic_difficulty": 30,
            "reference_organic_difficulty": 45,
            "local_difficulty": 25,
            "reference_local_difficulty": 35,
        }
    )
    assert result.score >= 70
    assert result.evidence["similarity_score"] == 0.92


def test_expand_conquer_blocks_higher_competition() -> None:
    result = project_expand_conquer(
        {
            "similarity_score": 0.92,
            "organic_difficulty": 55,
            "reference_organic_difficulty": 45,
            "local_difficulty": 25,
            "reference_local_difficulty": 35,
        }
    )
    assert result.score == 0
    assert "competition_higher_than_reference" in result.warnings


def test_expand_conquer_rejects_non_finite_similarity() -> None:
    try:
        project_expand_conquer(
            {
                "similarity_score": "nan",
                "organic_difficulty": 30,
                "reference_organic_difficulty": 45,
                "local_difficulty": 25,
                "reference_local_difficulty": 35,
            }
        )
    except ValueError as exc:
        assert "similarity_score must be finite" in str(exc)
    else:
        raise AssertionError("Expected non-finite similarity to raise ValueError")


def test_ai_resilience_warning_flags_not_hides() -> None:
    warning = project_ai_resilience_warning(
        {"aio_trigger_rate": 0.22, "ai_resilience": 52}
    )
    assert warning["code"] == "ai_resilience_risk"
    assert warning["severity"] == "warning"


def test_ai_resilience_warning_treats_zero_score_as_risk() -> None:
    warning = project_ai_resilience_warning({"aio_trigger_rate": 0, "ai_resilience": 0})
    assert warning is not None
    assert warning["code"] == "ai_resilience_risk"
