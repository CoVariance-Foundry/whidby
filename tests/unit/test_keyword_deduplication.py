"""Unit tests for M4 keyword deduplication."""

from src.pipeline.keyword_deduplication import dedupe_candidate_keywords, normalize_keyword


def test_normalize_keyword_trims_collapses_and_lowercases() -> None:
    assert normalize_keyword("  Emergency   Plumber!!!  ") == "emergency plumber"


def test_deduplication_merges_duplicate_sources() -> None:
    result = dedupe_candidate_keywords(
        [
            {"keyword": "Plumber Near Me", "source": "llm"},
            {"keyword": "plumber near me ", "source": "dataforseo_suggestions"},
            {"keyword": "EMERGENCY PLUMBER", "source": "llm"},
        ]
    )

    by_keyword = {item["keyword"]: item for item in result}
    assert len(result) == 2
    assert by_keyword["plumber near me"]["source"] == "merged"
    assert by_keyword["emergency plumber"]["source"] == "llm"
