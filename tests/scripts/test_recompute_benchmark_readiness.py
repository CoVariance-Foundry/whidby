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
    assert result["minimums"]["metros_with_population"] == 1
    assert result["minimums"]["seo_fact_count"] == 1
    assert result["minimums"]["cbp_count"] == 1


def test_optional_acceptance_counts_do_not_block_without_minimums() -> None:
    result = readiness_status(
        metros_with_population=60,
        seo_fact_count=500,
        cbp_count=1000,
        usable_benchmark_cells=5,
        metric_ready_cells=4,
        explore_v2_rows=3,
    )

    assert result["ready"] is True
    assert result["blocking_checks"] == []


def test_readiness_status_blocks_when_usable_benchmark_cells_below_gate() -> None:
    result = readiness_status(
        metros_with_population=60,
        seo_fact_count=500,
        cbp_count=1000,
        usable_benchmark_cells=19,
        min_benchmark_cells=48,
    )

    assert result["ready"] is False
    assert "usable_benchmark_cells" in result["blocking_checks"]


def test_readiness_status_blocks_when_metric_ready_cells_below_gate() -> None:
    result = readiness_status(
        metros_with_population=60,
        seo_fact_count=500,
        cbp_count=1000,
        metric_ready_cells=17,
        min_metric_ready_cells=48,
    )

    assert result["ready"] is False
    assert "metric_ready_cells" in result["blocking_checks"]


def test_readiness_status_blocks_when_explore_v2_rows_below_gate() -> None:
    result = readiness_status(
        metros_with_population=60,
        seo_fact_count=500,
        cbp_count=1000,
        explore_v2_rows=12,
        min_explore_v2_rows=48,
    )

    assert result["ready"] is False
    assert "explore_v2_rows" in result["blocking_checks"]


def test_readiness_status_passes_when_acceptance_gates_are_met() -> None:
    result = readiness_status(
        metros_with_population=60,
        seo_fact_count=500,
        cbp_count=1000,
        usable_benchmark_cells=48,
        min_benchmark_cells=48,
        metric_ready_cells=48,
        min_metric_ready_cells=48,
        explore_v2_rows=96,
        min_explore_v2_rows=48,
    )

    assert result["ready"] is True
    assert result["blocking_checks"] == []
