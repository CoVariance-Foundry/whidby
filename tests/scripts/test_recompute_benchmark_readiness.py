from scripts.explore.recompute_benchmark_readiness import readiness_status


def test_readiness_status_requires_metros_and_facts() -> None:
    result = readiness_status(
        metros_with_population=0,
        seo_fact_count=10,
        cbp_count=10,
    )

    assert result["ready"] is False
    assert "metros_with_population" in result["blocking_checks"]


def test_readiness_status_passes_when_sources_exist() -> None:
    result = readiness_status(
        metros_with_population=60,
        seo_fact_count=500,
        cbp_count=1000,
    )

    assert result["ready"] is True
    assert result["blocking_checks"] == []
