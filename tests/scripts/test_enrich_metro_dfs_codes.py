import csv

from scripts.explore import enrich_metro_dfs_codes as enrich


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.payload = None
        self.cbsa_code = None

    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, column, value):
        assert column == "cbsa_code"
        self.cbsa_code = value
        return self

    def execute(self):
        if self.supabase.fail_provenance_once and any(
            key in self.payload for key in enrich.PROVENANCE_COLUMNS
        ):
            self.supabase.fail_provenance_once = False
            raise Exception("column dataforseo_location_match_name does not exist")
        if self.supabase.zero_rows:
            return FakeResponse([])
        self.supabase.updates.append((self.cbsa_code, self.payload))
        return FakeResponse([{"cbsa_code": self.cbsa_code}])


class FakeSupabase:
    def __init__(self, fail_provenance_once=False, zero_rows=False):
        self.fail_provenance_once = fail_provenance_once
        self.zero_rows = zero_rows
        self.updates = []

    def table(self, table_name):
        assert table_name == "metros"
        return FakeQuery(self, table_name)


def match(
    status,
    *,
    cbsa_code,
    selected_location_code=None,
    existing_codes=(),
):
    return enrich.MetroDfsReadinessMatch(
        cbsa_code=cbsa_code,
        cbsa_name=f"Metro {cbsa_code}",
        state="TX",
        population=950_000,
        population_class="large_300k_1m",
        status=status,
        selected_location_code=selected_location_code,
        selected_location_name=(
            f"Location {selected_location_code}" if selected_location_code else None
        ),
        candidate_city="Metro",
        reason=f"{status} reason",
        existing_codes=tuple(existing_codes),
    )


def test_dry_run_exact_mode_selects_exact_rows_but_does_not_update(monkeypatch):
    supabase = FakeSupabase()
    matches = [
        match("exact", cbsa_code="10000", selected_location_code=1001),
        match("strong", cbsa_code="20000", selected_location_code=2002),
    ]
    monkeypatch.setattr(enrich, "fetch_metros", lambda _supabase: [{"id": 1}])
    monkeypatch.setattr(enrich, "match_metros", lambda _metros, _dfs: matches)

    report = enrich.build_report(
        supabase=supabase,
        dfs_locations=[],
        dry_run=True,
        confidence="exact",
        approved_strong_rows=set(),
        limit=None,
    )

    assert report["dry_run"] is True
    assert report["applied_count"] == 0
    assert report["candidate_count"] == 1
    assert report["candidate_rows"][0]["cbsa_code"] == "10000"
    assert supabase.updates == []


def test_apply_exact_mode_updates_only_exact_rows_and_dedupes_existing_codes(monkeypatch):
    supabase = FakeSupabase()
    matches = [
        match("exact", cbsa_code="10000", selected_location_code=1001, existing_codes=(7, 1001)),
        match("strong", cbsa_code="20000", selected_location_code=2002),
        match("already_ready", cbsa_code="30000", selected_location_code=3003),
    ]
    monkeypatch.setattr(enrich, "fetch_metros", lambda _supabase: [{"id": 1}])
    monkeypatch.setattr(enrich, "match_metros", lambda _metros, _dfs: matches)

    report = enrich.build_report(
        supabase=supabase,
        dfs_locations=[],
        dry_run=False,
        confidence="exact",
        approved_strong_rows=set(),
        limit=None,
    )

    assert report["applied_count"] == 1
    assert [cbsa_code for cbsa_code, _payload in supabase.updates] == ["10000"]
    assert supabase.updates[0][1]["dataforseo_location_codes"] == [1001, 7]
    assert supabase.updates[0][1]["dataforseo_location_match_confidence"] == "exact"


def test_strong_mode_requires_approved_csv():
    args = enrich.parse_args(["--confidence", "strong"])

    try:
        enrich.validate_args(args)
    except RuntimeError as exc:
        assert "--approved-csv is required" in str(exc)
    else:
        raise AssertionError("validate_args should reject strong mode without CSV")


def test_approved_csv_applies_only_matching_cbsa_and_location_code_strong_rows(
    monkeypatch,
    tmp_path,
):
    approved_path = tmp_path / "approved.csv"
    with approved_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["cbsa_code", "selected_location_code", "approved"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "cbsa_code": "20000",
                "selected_location_code": "2002",
                "approved": "true",
            }
        )
        writer.writerow(
            {
                "cbsa_code": "30000",
                "selected_location_code": "9999",
                "approved": "true",
            }
        )

    supabase = FakeSupabase()
    matches = [
        match("strong", cbsa_code="20000", selected_location_code=2002),
        match("strong", cbsa_code="30000", selected_location_code=3003),
    ]
    monkeypatch.setattr(enrich, "fetch_metros", lambda _supabase: [{"id": 1}])
    monkeypatch.setattr(enrich, "match_metros", lambda _metros, _dfs: matches)

    report = enrich.build_report(
        supabase=supabase,
        dfs_locations=[],
        dry_run=False,
        confidence="strong",
        approved_strong_rows=enrich.load_approved_strong_rows(approved_path),
        limit=None,
    )

    assert report["applied_count"] == 1
    assert [cbsa_code for cbsa_code, _payload in supabase.updates] == ["20000"]


def test_approved_csv_does_not_require_approved_column(tmp_path):
    approved_path = tmp_path / "approved.csv"
    with approved_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["cbsa_code", "selected_location_code"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "cbsa_code": "20000",
                "selected_location_code": "2002",
            }
        )

    assert enrich.load_approved_strong_rows(approved_path) == {("20000", 2002)}


def test_unsafe_statuses_never_update(monkeypatch):
    supabase = FakeSupabase()
    matches = [
        match("ambiguous", cbsa_code="10000", selected_location_code=None),
        match("no_match", cbsa_code="20000", selected_location_code=None),
        match("invalid_existing_code", cbsa_code="30000", selected_location_code=None),
        match("already_ready", cbsa_code="40000", selected_location_code=4004),
    ]
    monkeypatch.setattr(enrich, "fetch_metros", lambda _supabase: [{"id": 1}])
    monkeypatch.setattr(enrich, "match_metros", lambda _metros, _dfs: matches)

    report = enrich.build_report(
        supabase=supabase,
        dfs_locations=[],
        dry_run=False,
        confidence="strong",
        approved_strong_rows={("40000", 4004)},
        limit=None,
    )

    assert report["candidate_count"] == 0
    assert report["applied_count"] == 0
    assert supabase.updates == []


def test_provenance_column_failure_raises_and_does_not_apply_codes_only():
    supabase = FakeSupabase(fail_provenance_once=True)
    matches = [match("exact", cbsa_code="10000", selected_location_code=1001)]

    try:
        enrich.apply_candidates(supabase, matches)
    except RuntimeError as exc:
        assert "Provenance columns are missing" in str(exc)
    else:
        raise AssertionError("missing provenance columns should abort apply")

    assert supabase.updates == []


def test_zero_row_update_raises_and_is_not_reported_as_applied():
    supabase = FakeSupabase(zero_rows=True)
    matches = [match("exact", cbsa_code="10000", selected_location_code=1001)]

    try:
        enrich.apply_candidates(supabase, matches)
    except RuntimeError as exc:
        assert "expected exactly one metros row" in str(exc)
    else:
        raise AssertionError("zero-row update should fail closed")
    assert supabase.updates == []


def test_missing_provenance_column_error_detector_accepts_explicit_patterns():
    assert enrich._is_missing_provenance_column_error(
        Exception('column "dataforseo_location_match_name" does not exist')
    )
    assert enrich._is_missing_provenance_column_error(
        Exception(
            "Could not find the 'dataforseo_location_match_source' column "
            "of 'metros' in the schema cache"
        )
    )


def test_missing_provenance_column_error_detector_rejects_non_missing_failures():
    assert not enrich._is_missing_provenance_column_error(
        Exception(
            "permission denied updating dataforseo_location_match_name; "
            "policy exists but does not allow writes"
        )
    )


def test_non_missing_update_failure_mentioning_provenance_column_propagates():
    class FailingSupabase(FakeSupabase):
        def table(self, table_name):
            query = super().table(table_name)

            def fail_execute():
                raise Exception(
                    "permission denied updating dataforseo_location_match_name; "
                    "policy exists but does not allow writes"
                )

            query.execute = fail_execute
            return query

    matches = [match("exact", cbsa_code="10000", selected_location_code=1001)]

    try:
        enrich.apply_candidates(FailingSupabase(), matches)
    except Exception as exc:
        assert "permission denied" in str(exc)
    else:
        raise AssertionError("non-provenance failures should propagate")


def test_project_ref_guard_rejects_apply_without_expected_ref(monkeypatch):
    monkeypatch.setattr(enrich, "load_env", lambda: None)
    monkeypatch.setattr(enrich, "supabase_client", FakeSupabase)

    result = enrich.main(["--apply", "--stdout-only"])

    assert result == 1


def test_project_ref_guard_rejects_mismatch(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://abc123.supabase.co")
    args = enrich.parse_args(
        ["--apply", "--expected-project-ref", "def456", "--stdout-only"]
    )

    try:
        enrich.validate_args(args)
    except RuntimeError as exc:
        assert "expected def456, got abc123" in str(exc)
    else:
        raise AssertionError("validate_args should reject mismatched project ref")


def test_project_ref_guard_accepts_matching_supabase_url(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://abc123.supabase.co")
    args = enrich.parse_args(
        ["--apply", "--expected-project-ref", "abc123", "--stdout-only"]
    )

    enrich.validate_args(args)
