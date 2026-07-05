import json
import os

from scripts.supabase import seed_segment_fixtures as seed


SEGMENT_ENV_PREFIX = "WHIDBY_SEGMENT_"


def _clear_segment_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith(SEGMENT_ENV_PREFIX):
            monkeypatch.delenv(key, raising=False)


def test_dry_run_manifest_includes_segment_routes_without_passwords(monkeypatch, capsys):
    _clear_segment_env(monkeypatch)

    result = seed.main(["--dry-run"])

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)
    assert [item["segment"] for item in manifest] == [
        "find_first",
        "scale",
        "coach_agency",
        "researching",
    ]
    assert [item["next_route"] for item in manifest] == [
        "/",
        "/strategies",
        "/agency",
        "/explore",
    ]
    assert "password" not in json.dumps(manifest).lower()


def test_build_segment_fixtures_uses_common_password_and_email_override(monkeypatch):
    _clear_segment_env(monkeypatch)
    monkeypatch.setenv("WHIDBY_SEGMENT_FIXTURE_PASSWORD", "common-password")
    monkeypatch.setenv("WHIDBY_SEGMENT_SCALE_EMAIL", "Scale-Override@Widby.Dev")

    fixtures = seed.build_segment_fixtures()
    by_segment = {fixture.defaults.segment: fixture for fixture in fixtures}

    assert by_segment["find_first"].persona.password == "common-password"
    assert by_segment["scale"].persona.email == "Scale-Override@Widby.Dev"
    assert by_segment["scale"].persona.password == "common-password"


def test_build_segment_fixtures_prefers_per_fixture_password(monkeypatch):
    _clear_segment_env(monkeypatch)
    monkeypatch.setenv("WHIDBY_SEGMENT_FIXTURE_PASSWORD", "common-password")
    monkeypatch.setenv("WHIDBY_SEGMENT_RESEARCHING_PASSWORD", "research-password")

    fixtures = seed.build_segment_fixtures()
    by_segment = {fixture.defaults.segment: fixture for fixture in fixtures}

    assert by_segment["researching"].persona.password == "research-password"
    assert by_segment["coach_agency"].persona.password == "common-password"


def test_build_segment_fixtures_requires_password_for_live_mode(monkeypatch):
    _clear_segment_env(monkeypatch)

    try:
        seed.build_segment_fixtures()
    except RuntimeError as error:
        assert "WHIDBY_SEGMENT_FIND_FIRST_PASSWORD" in str(error)
        assert "WHIDBY_SEGMENT_FIXTURE_PASSWORD" in str(error)
    else:
        raise AssertionError("expected missing password RuntimeError")


def test_coach_agency_onboarding_payload_is_admin_capable(monkeypatch):
    _clear_segment_env(monkeypatch)
    fixtures = seed.build_segment_fixtures(require_passwords=False)
    fixture = next(item for item in fixtures if item.defaults.segment == "coach_agency")

    payload = seed.onboarding_profile_payload(
        fixture,
        user_id="user-123",
        account_id="account-123",
    )

    assert fixture.persona.member_role == "admin"
    assert fixture.persona.plan_key == "pro"
    assert fixture.persona.widby_role == "admin"
    assert payload == {
        "id": "00000000-0000-4000-8000-000000050154",
        "user_id": "user-123",
        "account_id": "account-123",
        "intent": "coach_agency",
        "focus": "agency",
        "coach_or_agency": "agency",
        "referral_source": "segment_fixture",
        "recommended_strategy_id": "easy_win",
        "available_strategy_ids": [
            "easy_win",
            "gbp_blitz",
            "expand_conquer",
            "keyword_hijack",
            "portfolio_builder",
        ],
        "next_route": "/agency",
        "status": "strategy_recommended",
        "completed_at": "2026-07-05T00:00:00Z",
    }


def test_scale_report_and_ranked_site_declaration_payloads(monkeypatch):
    _clear_segment_env(monkeypatch)
    fixtures = seed.build_segment_fixtures(require_passwords=False)
    fixture = next(item for item in fixtures if item.defaults.segment == "scale")

    report = seed.report_payload(
        fixture,
        user_id="user-123",
        account_id="account-123",
    )
    declaration = seed.ranked_site_declaration_payload(
        fixture,
        user_id="user-123",
        account_id="account-123",
    )

    assert report is not None
    assert report["id"] == "00000000-0000-4000-8000-000000000154"
    assert report["owner_account_id"] == "account-123"
    assert report["created_by_user_id"] == "user-123"
    assert report["access_scope"] == "account"
    assert report["strategy_profile"] == "expand_conquer"
    assert report["meta"]["segment"] == "scale"
    assert report["metros"][0]["cbsa_code"] == "24860"
    assert report["metros"][0]["cbsa_name"] == "Greenville-Anderson-Greer, SC"
    assert report["metros"][0]["scores"]["opportunity"] == 74
    assert report["metros"][0]["signals"]["demand"]["total_search_volume"] == 4200

    assert declaration is not None
    assert declaration["id"] == "00000000-0000-4000-8000-000000001154"
    assert declaration["account_id"] == "account-123"
    assert declaration["created_by_user_id"] == "user-123"
    assert declaration["site_domain"] == "segment-scale-fixture.example"
    assert declaration["proof_state"] == "declared"
    assert declaration["active"] is True
    assert declaration["metadata"]["report_id"] == report["id"]


def test_seed_segment_fixture_upserts_tables_in_required_order(monkeypatch):
    fixture = seed.SegmentFixture(
        defaults=seed.SegmentFixtureDefaults(
            segment="scale",
            email_env="EMAIL_ENV",
            default_email="segment-scale@widby.dev",
            password_env="PASSWORD_ENV",
            name="Scale",
            member_role="owner",
            plan_key="plus",
            widby_role="user",
            quota_exempt=False,
            intent="scale",
            focus="replicate",
            next_route="/strategies",
            profile_id="profile-id",
            target_id="target-id",
            strategy_id="expand_conquer",
            available_strategy_ids=("expand_conquer",),
            niche_keyword="tree service",
            city="Greenville",
            state="SC",
            seeded_data="history",
            report_id="report-id",
            declaration_id="declaration-id",
        ),
        persona=seed.TestPersona(
            email="Segment-Scale@Widby.Dev",
            password="password",
            name="Scale",
            member_role="owner",
            plan_key="plus",
            widby_role="user",
            quota_exempt=False,
        ),
    )
    upserted_tables = []

    monkeypatch.setattr(
        seed,
        "create_or_update_auth_user",
        lambda *_args: {"id": "user-123"},
    )
    monkeypatch.setattr(seed, "call_rpc", lambda *_args, **_kwargs: "account-123")
    monkeypatch.setattr(seed, "set_quota_exemption", lambda *_args, **_kwargs: {})

    def fake_request_json(method, url, headers, payload=None):
        assert method == "POST"
        assert headers["Prefer"] == "resolution=merge-duplicates"
        table = url.split("/rest/v1/", maxsplit=1)[1].split("?", maxsplit=1)[0]
        upserted_tables.append((table, payload))
        return {}

    monkeypatch.setattr(seed, "request_json", fake_request_json)

    summary = seed.seed_segment_fixture(
        "https://example.supabase.co",
        {"Authorization": "Bearer service-role-secret"},
        fixture,
    )

    assert [table for table, _payload in upserted_tables] == [
        "onboarding_profiles",
        "onboarding_targets",
        "reports",
        "ranked_site_declarations",
    ]
    assert upserted_tables[0][1][0]["id"] == "profile-id"
    assert upserted_tables[1][1][0]["id"] == "target-id"
    assert upserted_tables[2][1][0]["id"] == "report-id"
    assert upserted_tables[3][1][0]["id"] == "declaration-id"
    assert summary["email"] == "segment-scale@widby.dev"
    assert summary["account_id"] == "account-123"
