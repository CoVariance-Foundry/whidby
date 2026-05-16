from scripts.explore.backfill_cbp_establishments import build_cbp_payload


def test_build_cbp_payload_maps_census_fields() -> None:
    row = {
        "cbsa_code": "38060",
        "naics_code": "238160",
        "naics_label": "Roofing contractors",
        "year": 2022,
        "est": "123",
        "n1_4": "80",
        "emp": "900",
        "ap": "12345",
        "empflag": None,
    }

    payload = build_cbp_payload(row)

    assert payload["cbsa_code"] == "38060"
    assert payload["naics_code"] == "238160"
    assert payload["year"] == 2022
    assert payload["est"] == 123
    assert payload["n1_4"] == 80
    assert payload["emp"] == 900
    assert payload["ap"] == 12345
    assert payload["suppressed"] is False


def test_build_cbp_payload_marks_suppressed_establishments() -> None:
    payload = build_cbp_payload(
        {
            "cbsa_code": "38060",
            "naics_code": "238160",
            "year": 2022,
            "est": None,
            "empflag": "D",
        }
    )

    assert payload["est"] is None
    assert payload["suppressed"] is True
