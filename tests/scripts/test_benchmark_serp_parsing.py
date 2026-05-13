from scripts.benchmarks.run_pilot import parse_serp_items


def test_parse_serp_items_extracts_top3_review_floor_and_rating():
    serp = [{
        "items": [{
            "type": "local_pack",
            "rank_absolute": 1,
            "items": [
                {"title": "A", "rating": {"value": 4.8, "votes_count": 120}},
                {"title": "B", "rating": {"value": 4.5, "votes_count": 80}},
                {"title": "C", "rating": {"value": 4.1, "votes_count": 40}},
            ],
        }]
    }]

    parsed = parse_serp_items(serp)

    assert parsed["local_pack_present"] is True
    assert parsed["top3_review_count_min"] == 40
    assert parsed["top3_review_count_avg"] == 80
    assert parsed["top3_rating_avg"] == 4.47
