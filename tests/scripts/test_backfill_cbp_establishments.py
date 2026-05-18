import json
import sys

import pytest

import scripts.explore.backfill_cbp_establishments as backfill_cbp
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


def test_build_cbp_payload_allows_cli_year_override() -> None:
    payload = build_cbp_payload(
        {
            "cbsa_code": "38060",
            "naics_code": "238160",
            "est": "123",
        },
        year_override=2022,
    )

    assert payload["year"] == 2022
    assert payload["est"] == 123


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


def test_build_cbp_payload_maps_repo_and_census_aliases() -> None:
    payload = build_cbp_payload(
        {
            "cbsa_code": 38060,
            "NAICS2022": 238160,
            "NAICS2022_LABEL": "Roofing contractors",
            "year": "2022",
            "establishments": "123",
            "employees": "900",
            "payroll_thousands": "12345",
        }
    )

    assert payload["cbsa_code"] == "38060"
    assert payload["naics_code"] == "238160"
    assert payload["naics_label"] == "Roofing contractors"
    assert payload["year"] == 2022
    assert payload["est"] == 123
    assert payload["emp"] == 900
    assert payload["ap"] == 12345


def test_build_cbp_payload_maps_raw_census_geography_alias() -> None:
    payload = build_cbp_payload(
        {
            "metropolitan statistical area/micropolitan statistical area": "38060",
            "NAICS2017": "238160",
            "year": "2022",
            "ESTAB": "123",
            "EMP": "900",
            "PAYANN": "12345",
        }
    )

    assert payload["cbsa_code"] == "38060"
    assert payload["naics_code"] == "238160"
    assert payload["est"] == 123
    assert payload["emp"] == 900
    assert payload["ap"] == 12345


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({"naics_code": "238160", "year": 2022}, "row 1 missing required cbsa_code"),
        ({"cbsa_code": "", "naics_code": "238160", "year": 2022}, "row 1 missing required cbsa_code"),
        ({"cbsa_code": "38060", "year": 2022}, "row 1 missing required naics_code"),
        ({"cbsa_code": "38060", "naics_code": "238160", "year": ""}, "row 1 missing required year"),
    ],
)
def test_build_cbp_payload_validates_required_keys(
    row: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_cbp_payload(row, row_number=1)


def test_main_defaults_to_preview_without_live_write(monkeypatch, tmp_path, capsys) -> None:
    input_path = tmp_path / "cbp.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "cbsa_code": "38060",
                    "naics_code": "238160",
                    "year": 2022,
                    "est": "123",
                }
            ]
        ),
        encoding="utf-8",
    )

    def fail_upsert(url, service_key, rows):  # noqa: ANN001
        raise AssertionError("default mode must not write to PostgREST")

    monkeypatch.setattr(
        sys,
        "argv",
        ["backfill_cbp_establishments.py", "--input", str(input_path)],
    )
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret-service-role")
    monkeypatch.setattr(backfill_cbp, "postgrest_upsert", fail_upsert)

    assert backfill_cbp.main() == 0

    output = capsys.readouterr().out
    assert "dry_run=true" in output
    assert "prepared_rows=1" in output
    assert "secret-service-role" not in output


def test_main_dry_run_accepts_year_for_rows_without_year(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    input_path = tmp_path / "cbp.csv"
    input_path.write_text(
        "cbsa_code,naics_code,est\n38060,238160,123\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "backfill_cbp_establishments.py",
            "--input",
            str(input_path),
            "--year",
            "2022",
            "--dry-run",
        ],
    )

    assert backfill_cbp.main() == 0

    output = capsys.readouterr().out
    assert '"year": 2022' in output
    assert "year=2022" in output
    assert "prepared_rows=1" in output


def test_main_apply_refuses_missing_env_without_live_write(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    input_path = tmp_path / "cbp.json"
    input_path.write_text(
        json.dumps([{"cbsa_code": "38060", "naics_code": "238160", "year": 2022}]),
        encoding="utf-8",
    )

    def fail_upsert(url, service_key, rows):  # noqa: ANN001
        raise AssertionError("missing env must not write to PostgREST")

    monkeypatch.setattr(
        sys,
        "argv",
        ["backfill_cbp_establishments.py", "--input", str(input_path), "--apply"],
    )
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(backfill_cbp, "postgrest_upsert", fail_upsert)

    assert backfill_cbp.main() == 2

    output = capsys.readouterr().out
    assert "Missing Supabase environment variable(s)" in output
    assert "SUPABASE_SERVICE_ROLE_KEY" in output
    assert "No live mutation ran." in output


def test_main_rejects_missing_required_keys_without_live_write(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    input_path = tmp_path / "cbp.json"
    input_path.write_text(
        json.dumps([{"cbsa_code": "38060", "naics_code": "238160", "year": ""}]),
        encoding="utf-8",
    )

    def fail_upsert(url, service_key, rows):  # noqa: ANN001
        raise AssertionError("invalid input must not write to PostgREST")

    monkeypatch.setattr(
        sys,
        "argv",
        ["backfill_cbp_establishments.py", "--input", str(input_path), "--apply"],
    )
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret-service-role")
    monkeypatch.setattr(backfill_cbp, "postgrest_upsert", fail_upsert)

    assert backfill_cbp.main() == 1

    output = capsys.readouterr().out
    assert "CBP input import failed: ValueError: row 1 missing required year" in output
    assert "No live mutation ran." in output
    assert "secret-service-role" not in output


def test_postgrest_upsert_uses_expected_endpoint_and_headers(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return b""

    def fake_urlopen(req, timeout):  # noqa: ANN001
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["data"] = req.data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(backfill_cbp.request, "urlopen", fake_urlopen)

    backfill_cbp.postgrest_upsert(
        "https://example.supabase.co/",
        "secret-service-role",
        [{"cbsa_code": "38060", "naics_code": "238160", "year": 2022}],
    )

    assert captured["url"] == (
        "https://example.supabase.co/rest/v1/census_cbp_establishments"
        "?on_conflict=cbsa_code,naics_code,year"
    )
    assert captured["headers"]["Prefer"] == "resolution=merge-duplicates,return=minimal"
    assert captured["headers"]["Content-type"] == "application/json"
    assert json.loads(captured["data"]) == [
        {"cbsa_code": "38060", "naics_code": "238160", "year": 2022}
    ]
    assert captured["timeout"] == 30
