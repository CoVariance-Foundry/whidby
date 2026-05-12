from scripts.sonar.build_slice_lite import (
    SLICE_LITE_WARNINGS,
    build_cell_record,
    build_metric_block,
    build_seo_rollup,
    compute_lite_score,
    compute_z_score_gap,
    persist_cell_record,
    shape_evidence_payload,
)


def test_build_metric_block_preserves_provenance():
    block = build_metric_block(
        value=2.9149,
        raw_inputs={"estab": 3793, "pop": 13012469},
        source="cbp_2023 + acs_2023_5yr",
        vintage="2023",
        suppression_flag=False,
        computed_at="2023-12-31T00:00:00Z",
    )

    assert block["value"] == 2.9149
    assert block["raw_inputs"] == {"estab": 3793, "pop": 13012469}
    assert block["source"] == "cbp_2023 + acs_2023_5yr"
    assert block["vintage"] == "2023"
    assert block["suppression_flag"] is False
    assert block["computed_at"] == "2023-12-31T00:00:00Z"
    assert block["evidence"]["source"] == "cbp_2023 + acs_2023_5yr"


def test_shape_evidence_payload_is_network_free_and_stable():
    evidence = shape_evidence_payload(
        raw_inputs={"rows": 4},
        source="seo_facts",
        vintage="2026-05-12",
        computed_at="2026-05-12T00:00:00Z",
    )

    assert evidence == {
        "raw_inputs": {"rows": 4},
        "source": "seo_facts",
        "vintage": "2026-05-12",
        "computed_at": "2026-05-12T00:00:00Z",
        "suppression_flag": False,
    }


def test_compute_z_score_gap_handles_spread_and_missing_values():
    gap = compute_z_score_gap(value=14.0, benchmark=10.0, spread=2.0)

    assert gap == {
        "value": 14.0,
        "benchmark": 10.0,
        "gap": 4.0,
        "z_score": 2.0,
    }
    assert compute_z_score_gap(value=14.0, benchmark=10.0, spread=0)["z_score"] is None
    assert compute_z_score_gap(value=None, benchmark=10.0, spread=2.0)["gap"] is None


def test_compute_lite_score_penalizes_serp_consolidation():
    score = compute_lite_score(
        searches_per_household=0.025716,
        establishments_per_10k_pop=2.9149,
        avg_cpc=35.27,
        commercial_intent_share=1.0,
        serp_consolidation_index=0.60,
    )

    easier_serp_score = compute_lite_score(
        searches_per_household=0.025716,
        establishments_per_10k_pop=2.9149,
        avg_cpc=35.27,
        commercial_intent_share=1.0,
        serp_consolidation_index=0.20,
    )

    assert 0 <= score <= 1
    assert easier_serp_score > score


def test_build_seo_rollup_aggregates_fact_rows():
    rollup = build_seo_rollup(
        [
            {
                "search_volume_monthly": 100,
                "cpc_usd": "20.00",
                "local_pack_present": True,
                "aggregator_count_top10": 3,
                "snapshot_date": "2026-05-11",
            },
            {
                "search_volume_monthly": 300,
                "cpc_usd": "40.00",
                "local_pack_present": False,
                "aggregator_count_top10": 5,
                "snapshot_date": "2026-05-12",
            },
        ]
    )

    assert rollup["keyword_rows"] == 2
    assert rollup["cluster_monthly_volume"] == 400
    assert rollup["avg_cpc_unweighted"] == 30.0
    assert rollup["avg_cpc_volume_weighted"] == 35.0
    assert rollup["serp_local_pack_rate"] == 0.5
    assert rollup["avg_aggregator_count_top10"] == 4.0
    assert rollup["fact_window_end"] == "2026-05-12"


def test_build_seo_rollup_excludes_missing_cpc_from_weighted_denominator():
    rollup = build_seo_rollup(
        [
            {"search_volume_monthly": 100, "cpc_usd": "20.00"},
            {"search_volume_monthly": 300, "cpc_usd": None},
        ]
    )

    assert rollup["cluster_monthly_volume"] == 400
    assert rollup["avg_cpc_volume_weighted"] == 20.0


def test_build_cell_record_shapes_deterministic_slice_lite_payload():
    record = build_cell_record(
        metro={
            "cbsa_code": "31080",
            "cbsa_name": "Los Angeles-Long Beach-Anaheim, CA",
            "population": 13012469,
            "households": 4689520,
            "owner_occupancy_rate": "0.4577",
            "median_household_income_usd": 88200,
            "acs_vintage": 2023,
        },
        cbp={
            "est": 3793,
            "emp": 25400,
            "ap": 1725000,
            "n50_99": 21,
            "n100_249": 8,
            "n250_499": 1,
            "n500_999": 0,
            "n1000": 0,
            "suppressed": False,
        },
        seo={
            "keyword_rows": 4,
            "cluster_monthly_volume": 120500,
            "commercial_transactional_volume": 120500,
            "avg_cpc_volume_weighted": 35.27,
            "avg_cpc_unweighted": 31.10,
            "serp_local_pack_rate": 1.0,
            "avg_aggregator_count_top10": 6.0,
            "fact_window_end": "2026-05-12",
        },
        benchmark={
            "p25_total_volume_per_capita": "0.004",
            "median_total_volume_per_capita": "0.008",
            "p75_total_volume_per_capita": "0.012",
            "p25_avg_cpc": "20.0",
            "median_avg_cpc": "30.0",
            "p75_avg_cpc": "40.0",
            "median_establishments_per_100k": "20.0",
            "confidence_label": "medium",
            "sample_size_metros": 12,
        },
        peer_count=73,
        year=2023,
    )

    assert record["cell_id"] == "238220__msa__31080__2023"
    assert record["extract_run_ts"] == "2026-05-12T00:00:00Z"
    assert record["score"]["score_version"] == "sonar-lite-0.1"
    assert record["score"]["opportunity_score"] == record["score"]["underserved_score"]
    assert record["data_quality"]["warnings"] == SLICE_LITE_WARNINGS
    assert record["data_quality"]["peer_count_238220"] == 73
    assert record["supply"]["establishments_per_10k_pop"]["evidence"]["source"].startswith(
        "cbp_2023"
    )
    assert record["benchmark_gaps"]["avg_cpc"]["gap"] == 5.27


def test_persist_cell_record_uses_public_rpc(monkeypatch):
    calls = []

    def fake_rpc(function_name, payload):
        calls.append((function_name, payload))
        return [{"run_id": "00000000-0000-0000-0000-000000000000"}]

    monkeypatch.setattr("scripts.sonar.build_slice_lite.postgrest_rpc", fake_rpc)

    record = {
        "cell_id": "238220__msa__31080__2023",
        "score": {"underserved_score": 0.72, "score_version": "sonar-lite-0.1"},
    }

    assert persist_cell_record(record) == [{"run_id": "00000000-0000-0000-0000-000000000000"}]
    assert calls == [("persist_sonar_slice_lite", {"p_record": record})]
