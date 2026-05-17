import os

from scripts.supabase import seed_test_accounts as seed


def test_build_headers_sets_service_role_json_headers():
    headers = seed.build_headers("service-role-secret")

    assert headers == {
        "Authorization": "Bearer service-role-secret",
        "apikey": "service-role-secret",
        "Content-Type": "application/json",
    }


def test_build_user_payload_admin_lowercases_email_and_sets_metadata():
    persona = seed.TestPersona(
        email="ADMIN-Test@Widby.Dev",
        password="admin-password",
        name="Admin Test",
        member_role="admin",
        plan_key="free",
        widby_role="admin",
        quota_exempt=True,
    )

    payload = seed.build_user_payload(persona)

    assert payload["email"] == "admin-test@widby.dev"
    assert payload["password"] == "admin-password"
    assert payload["email_confirm"] is True
    assert payload["user_metadata"]["name"] == "Admin Test"
    assert payload["app_metadata"]["widby_role"] == "admin"


def test_build_user_payload_normal_user_marks_widby_role_user():
    persona = seed.TestPersona(
        email="user-test@widby.dev",
        password="user-password",
        name="Normal User",
        member_role="owner",
        plan_key="free",
        widby_role="user",
        quota_exempt=False,
    )

    payload = seed.build_user_payload(persona)

    assert payload["app_metadata"]["widby_role"] == "user"


def test_build_user_payload_merges_existing_metadata_for_update():
    persona = seed.TestPersona(
        email="admin-test@widby.dev",
        password="admin-password",
        name="Updated Name",
        member_role="admin",
        plan_key="free",
        widby_role="admin",
        quota_exempt=True,
    )
    existing_user = {
        "user_metadata": {
            "name": "Old Name",
            "theme": "dark",
        },
        "app_metadata": {
            "provider": "phone",
            "providers": ["phone"],
            "widby_role": "user",
            "custom_claim": "keep-me",
        },
    }

    payload = seed.build_user_payload(persona, existing_user)

    assert payload["user_metadata"] == {
        "name": "Updated Name",
        "theme": "dark",
    }
    assert payload["app_metadata"] == {
        "provider": "email",
        "providers": ["email"],
        "widby_role": "admin",
        "custom_claim": "keep-me",
    }


def test_find_user_by_email_uses_encoded_email_filter_and_case_check(monkeypatch):
    calls = []

    def fake_request_json(method, url, headers, payload=None):
        calls.append((method, url, headers, payload))
        return {
            "users": [
                {"id": "wrong-user", "email": "other@widby.dev"},
                {"id": "user-123", "email": "USER-Test@Widby.Dev"},
            ]
        }

    monkeypatch.setattr(seed, "request_json", fake_request_json)

    user = seed.find_user_by_email(
        "https://example.supabase.co/",
        {"Authorization": "Bearer service-role-secret"},
        "user-test@widby.dev",
    )

    assert user == {"id": "user-123", "email": "USER-Test@Widby.Dev"}
    assert calls == [
        (
            "GET",
            "https://example.supabase.co/auth/v1/admin/users?filter=user-test%40widby.dev",
            {"Authorization": "Bearer service-role-secret"},
            None,
        )
    ]


def test_create_or_update_auth_user_updates_existing_user_with_merged_metadata(
    monkeypatch,
):
    persona = seed.TestPersona(
        email="User-Test@Widby.Dev",
        password="new-password",
        name="Updated User",
        member_role="owner",
        plan_key="pro",
        widby_role="user",
        quota_exempt=False,
    )
    calls = []
    existing_user = {
        "id": "user-123",
        "email": "user-test@widby.dev",
        "user_metadata": {"locale": "en-US", "name": "Old User"},
        "app_metadata": {"custom_claim": "keep-me", "widby_role": "admin"},
    }

    monkeypatch.setattr(seed, "find_user_by_email", lambda *_args: existing_user)

    def fake_request_json(method, url, headers, payload=None):
        calls.append((method, url, headers, payload))
        return {"id": "user-123"}

    monkeypatch.setattr(seed, "request_json", fake_request_json)

    result = seed.create_or_update_auth_user(
        "https://example.supabase.co/",
        {"Authorization": "Bearer service-role-secret"},
        persona,
    )

    assert result == {"id": "user-123"}
    assert calls == [
        (
            "PUT",
            "https://example.supabase.co/auth/v1/admin/users/user-123",
            {"Authorization": "Bearer service-role-secret"},
            {
                "email": "user-test@widby.dev",
                "password": "new-password",
                "email_confirm": True,
                "user_metadata": {"locale": "en-US", "name": "Updated User"},
                "app_metadata": {
                    "custom_claim": "keep-me",
                    "provider": "email",
                    "providers": ["email"],
                    "widby_role": "user",
                },
            },
        )
    ]


def test_create_or_update_auth_user_creates_missing_user(monkeypatch):
    persona = seed.TestPersona(
        email="New-User@Widby.Dev",
        password="new-password",
        name="New User",
        member_role="owner",
        plan_key="free",
        widby_role="user",
        quota_exempt=False,
    )
    calls = []

    monkeypatch.setattr(seed, "find_user_by_email", lambda *_args: None)

    def fake_request_json(method, url, headers, payload=None):
        calls.append((method, url, headers, payload))
        return {"id": "new-user-123"}

    monkeypatch.setattr(seed, "request_json", fake_request_json)

    result = seed.create_or_update_auth_user(
        "https://example.supabase.co/",
        {"Authorization": "Bearer service-role-secret"},
        persona,
    )

    assert result == {"id": "new-user-123"}
    assert calls == [
        (
            "POST",
            "https://example.supabase.co/auth/v1/admin/users",
            {"Authorization": "Bearer service-role-secret"},
            {
                "email": "new-user@widby.dev",
                "password": "new-password",
                "email_confirm": True,
                "user_metadata": {"name": "New User"},
                "app_metadata": {
                    "provider": "email",
                    "providers": ["email"],
                    "widby_role": "user",
                },
            },
        )
    ]


def test_build_personas_from_env_includes_default_and_beta_role_rules(monkeypatch):
    for key in list(os.environ):
        if key.startswith("WHIDBY_TEST_") or key.startswith("WHIDBY_BETA_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("WHIDBY_TEST_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("WHIDBY_TEST_USER_PASSWORD", "user-password")
    monkeypatch.setenv("WHIDBY_BETA_HENOCK_PASSWORD", "henock-password")
    monkeypatch.setenv("WHIDBY_BETA_ANTWOINE_PASSWORD", "antwoine-password")
    monkeypatch.setenv("WHIDBY_BETA_LUKE_PASSWORD", "luke-password")

    personas = seed.build_personas_from_env()

    assert personas == [
        seed.TestPersona(
            email="admin-test@widby.dev",
            password="admin-password",
            name="Widby Admin Test",
            member_role="admin",
            plan_key="free",
            widby_role="admin",
            quota_exempt=True,
        ),
        seed.TestPersona(
            email="user-test@widby.dev",
            password="user-password",
            name="Widby User Test",
            member_role="owner",
            plan_key="free",
            widby_role="user",
            quota_exempt=False,
        ),
        seed.TestPersona(
            email="henock@covariance.studio",
            password="henock-password",
            name="Henock",
            member_role="admin",
            plan_key="free",
            widby_role="admin",
            quota_exempt=True,
        ),
        seed.TestPersona(
            email="antwoine@covariance.studio",
            password="antwoine-password",
            name="Antwoine",
            member_role="admin",
            plan_key="free",
            widby_role="admin",
            quota_exempt=True,
        ),
        seed.TestPersona(
            email="lm13vand@gmail.com",
            password="luke-password",
            name="Luke",
            member_role="owner",
            plan_key="pro",
            widby_role="user",
            quota_exempt=False,
        ),
    ]


def test_seed_persona_composes_account_rpc_and_entitlement_without_password(
    monkeypatch,
):
    persona = seed.TestPersona(
        email="User-Test@Widby.Dev",
        password="do-not-return",
        name="Normal User",
        member_role="owner",
        plan_key="pro",
        widby_role="user",
        quota_exempt=False,
    )
    rpc_calls = []
    entitlement_calls = []

    def fake_create_or_update_auth_user(base_url, headers, actual_persona):
        assert base_url == "https://example.supabase.co"
        assert headers == {"Authorization": "Bearer service-role-secret"}
        assert actual_persona == persona
        return {"user": {"id": "user-123"}}

    def fake_call_rpc(base_url, headers, name, payload):
        rpc_calls.append((base_url, headers, name, payload))
        return {"ok": True}

    def fake_set_quota_exemption(base_url, headers, user_id, exempt, reason):
        entitlement_calls.append((base_url, headers, user_id, exempt, reason))
        return [{"user_id": user_id}]

    monkeypatch.setattr(
        seed,
        "create_or_update_auth_user",
        fake_create_or_update_auth_user,
    )
    monkeypatch.setattr(seed, "call_rpc", fake_call_rpc)
    monkeypatch.setattr(seed, "set_quota_exemption", fake_set_quota_exemption)

    summary = seed.seed_persona(
        "https://example.supabase.co",
        {"Authorization": "Bearer service-role-secret"},
        persona,
        "staging beta assignment",
    )

    assert rpc_calls == [
        (
            "https://example.supabase.co",
            {"Authorization": "Bearer service-role-secret"},
            "ensure_account_for_user_admin",
            {
                "p_user_id": "user-123",
                "p_email": "user-test@widby.dev",
                "p_member_role": "owner",
                "p_plan_key": "pro",
                "p_overwrite_existing": True,
            },
        )
    ]
    assert entitlement_calls == [
        (
            "https://example.supabase.co",
            {"Authorization": "Bearer service-role-secret"},
            "user-123",
            False,
            "staging beta assignment",
        )
    ]
    assert summary == {
        "email": "user-test@widby.dev",
        "user_id": "user-123",
        "member_role": "owner",
        "plan_key": "pro",
        "quota_exempt": False,
    }
    assert "password" not in summary


def test_set_quota_exemption_upserts_expected_payload(monkeypatch):
    calls = []

    def fake_request_json(method, url, headers, payload=None):
        calls.append((method, url, headers, payload))
        return [{"user_id": "user-123"}]

    monkeypatch.setattr(seed, "request_json", fake_request_json)

    result = seed.set_quota_exemption(
        "https://example.supabase.co/",
        {"Authorization": "Bearer service-role-secret"},
        "user-123",
        True,
        "seeded for staging",
    )

    assert result == [{"user_id": "user-123"}]
    assert calls == [
        (
            "POST",
            "https://example.supabase.co/rest/v1/internal_user_entitlements?on_conflict=user_id",
            {
                "Authorization": "Bearer service-role-secret",
                "Prefer": "resolution=merge-duplicates",
            },
            {
                "user_id": "user-123",
                "fresh_report_quota_exempt": True,
                "reason": "seeded for staging",
                "expires_at": None,
            },
        )
    ]


def test_load_dotenv_does_not_override_and_parses_simple_quoted_values(
    tmp_path,
    monkeypatch,
):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "# local secrets",
                "EXISTING=from-file",
                "PLAIN=value",
                'DOUBLE_QUOTED="two words"',
                "SINGLE_QUOTED='three words'",
                "",
            ]
        )
    )
    monkeypatch.setenv("EXISTING", "from-env")
    monkeypatch.delenv("PLAIN", raising=False)
    monkeypatch.delenv("DOUBLE_QUOTED", raising=False)
    monkeypatch.delenv("SINGLE_QUOTED", raising=False)

    seed.load_dotenv(dotenv)

    assert os.environ["EXISTING"] == "from-env"
    assert os.environ["PLAIN"] == "value"
    assert os.environ["DOUBLE_QUOTED"] == "two words"
    assert os.environ["SINGLE_QUOTED"] == "three words"
