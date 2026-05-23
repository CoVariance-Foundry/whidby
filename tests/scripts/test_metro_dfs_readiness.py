import csv

from scripts.explore import audit_metro_dfs_readiness
from scripts.explore.metro_dfs_readiness import match_metro, summarize_matches


DFS_ROWS = [
    {
        "location_code": 1001,
        "location_name": "Phoenix,Arizona,United States",
        "country_iso_code": "US",
        "location_type": "City",
    },
    {
        "location_code": 1002,
        "location_name": "Newark,New Jersey,United States",
        "country_iso_code": "US",
        "location_type": "city",
    },
    {
        "location_code": 1003,
        "location_name": "Jersey City,New Jersey,United States",
        "country_iso_code": "US",
        "location_type": "city",
    },
    {
        "location_code": 1004,
        "location_name": "Greenville,South Carolina,United States",
        "country_iso_code": "US",
        "location_type": "city",
    },
    {
        "location_code": 1005,
        "location_name": "Salem,North Carolina,United States",
        "country_iso_code": "US",
        "location_type": "city",
    },
]


def metro(**overrides):
    base = {
        "cbsa_code": "38060",
        "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
        "state": "AZ",
        "population": 5_000_000,
        "population_class": "metro_1m_5m",
        "principal_cities": [],
        "dataforseo_location_codes": [],
    }
    base.update(overrides)
    return base


def test_exact_principal_city_match_is_exact():
    match = match_metro(
        metro(principal_cities=["Phoenix"]),
        DFS_ROWS,
    )

    assert match.status == "exact"
    assert match.selected_location_code == 1001
    assert match.candidate_city == "Phoenix"


def test_whole_cbsa_prefix_match_is_strong():
    match = match_metro(
        metro(
            cbsa_name="Greenville, SC",
            state="SC",
            population_class="large_300k_1m",
        ),
        DFS_ROWS,
    )

    assert match.status == "strong"
    assert match.selected_location_code == 1004
    assert match.candidate_city == "Greenville"


def test_multi_state_cbsa_accepts_listed_secondary_state():
    match = match_metro(
        metro(
            cbsa_name="New York-Newark-Jersey City, NY-NJ-PA",
            state="NY",
        ),
        DFS_ROWS,
    )

    assert match.status == "ambiguous"
    assert "different plausible DFS codes" in match.reason


def test_ambiguous_same_city_rows_are_ambiguous():
    rows = DFS_ROWS + [
        {
            "location_code": 2001,
            "location_name": "Phoenix,Arizona,United States",
            "country_iso_code": "US",
            "location_type": "city",
        }
    ]

    match = match_metro(metro(principal_cities=["Phoenix"]), rows)

    assert match.status == "ambiguous"
    assert "Multiple plausible DFS rows" in match.reason


def test_existing_invalid_dfs_code_is_invalid_existing_code():
    match = match_metro(
        metro(dataforseo_location_codes=[999999], principal_cities=["Phoenix"]),
        DFS_ROWS,
    )

    assert match.status == "invalid_existing_code"
    assert match.selected_location_code is None


def test_existing_valid_dfs_code_is_already_ready():
    match = match_metro(
        metro(dataforseo_location_codes=[1001], principal_cities=["Phoenix"]),
        DFS_ROWS,
    )

    assert match.status == "already_ready"
    assert match.selected_location_code == 1001


def test_existing_catalog_valid_code_for_wrong_city_is_invalid_existing_code():
    match = match_metro(
        metro(dataforseo_location_codes=[1004], principal_cities=["Phoenix"]),
        DFS_ROWS,
    )

    assert match.status == "invalid_existing_code"
    assert match.selected_location_code is None
    assert "incompatible" in match.reason


def test_hyphenated_city_name_split_token_does_not_auto_strong_match():
    match = match_metro(
        metro(
            cbsa_name="Winston-Salem, NC",
            state="NC",
            population_class="medium_100_300k",
        ),
        DFS_ROWS,
    )

    assert match.status == "ambiguous"
    assert match.selected_location_code is None
    assert "split CBSA-name city token" in match.reason


def test_summarize_matches_groups_by_status_and_population_class():
    matches = [
        match_metro(metro(principal_cities=["Phoenix"]), DFS_ROWS),
        match_metro(
            metro(
                cbsa_code="24860",
                cbsa_name="Greenville, SC",
                state="SC",
                population_class="large_300k_1m",
            ),
            DFS_ROWS,
        ),
        match_metro(
            metro(
                cbsa_code="99999",
                cbsa_name="Missing, OH",
                state="OH",
                population_class="medium_100_300k",
            ),
            DFS_ROWS,
        ),
    ]

    summary = summarize_matches(matches)

    assert summary["total"] == 3
    assert summary["by_status"] == {"exact": 1, "no_match": 1, "strong": 1}
    assert summary["by_population_class_status"]["metro_1m_5m"] == {"exact": 1}
    assert summary["by_population_class_status"]["large_300k_1m"] == {"strong": 1}
    assert summary["by_population_class_status"]["medium_100_300k"] == {"no_match": 1}
    assert summary["residual_review_classification"] == {
        "needs_alternate_target": 1
    }


def test_review_csv_includes_residual_classification_and_seed_policy(tmp_path):
    matches = [
        match_metro(
            metro(
                cbsa_code="99999",
                cbsa_name="Missing, OH",
                state="OH",
                population=80_000,
                population_class="small_50_100k",
            ),
            DFS_ROWS,
        )
    ]
    path = tmp_path / "review.csv"

    audit_metro_dfs_readiness._write_match_csv(path, matches)

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["population"] == "80000"
    assert rows[0]["residual_review_classification"] == "needs_alternate_target"
    assert rows[0]["production_seed_policy"] == "excluded_until_reviewed"
    assert rows[0]["approval_artifact_required"] == "yes"


async def test_fetch_dfs_locations_disables_persistent_cache(monkeypatch):
    class FakeResponse:
        status = "ok"
        error = None
        data = DFS_ROWS

    class FakeDataForSEOClient:
        kwargs = None

        def __init__(self, _login, _password, **kwargs):
            FakeDataForSEOClient.kwargs = kwargs

        async def locations(self):
            return FakeResponse()

    monkeypatch.setenv("DATAFORSEO_LOGIN", "login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "password")
    monkeypatch.setattr(
        audit_metro_dfs_readiness,
        "DataForSEOClient",
        FakeDataForSEOClient,
    )

    rows = await audit_metro_dfs_readiness.fetch_dfs_locations()

    assert rows == DFS_ROWS
    assert FakeDataForSEOClient.kwargs == {"persistent_cache": False}
