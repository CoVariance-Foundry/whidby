from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_ADMIN_EMAIL = "admin-test@widby.dev"
DEFAULT_USER_EMAIL = "user-test@widby.dev"
DEFAULT_HENOCK_EMAIL = "henock@covariance.studio"
DEFAULT_ANTWOINE_EMAIL = "antwoine@covariance.studio"
DEFAULT_LUKE_EMAIL = "lm13vand@gmail.com"


@dataclass(frozen=True)
class TestPersona:
    email: str
    password: str
    name: str
    member_role: str
    plan_key: str
    widby_role: str
    quota_exempt: bool


def build_headers(service_role_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
        "Content-Type": "application/json",
    }


def _metadata_from_existing(existing_user: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not existing_user:
        return {}
    metadata = existing_user.get(key)
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


def build_user_payload(
    persona: TestPersona,
    existing_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_metadata = _metadata_from_existing(existing_user, "user_metadata")
    user_metadata["name"] = persona.name

    app_metadata = _metadata_from_existing(existing_user, "app_metadata")
    app_metadata.update(
        {
            "provider": "email",
            "providers": ["email"],
            "widby_role": persona.widby_role,
        }
    )

    return {
        "email": persona.email.lower(),
        "password": persona.password,
        "email_confirm": True,
        "user_metadata": user_metadata,
        "app_metadata": app_metadata,
    }


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Any | None = None,
) -> Any:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_body = response.read()
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        detail = error_body.strip() or error.reason
        raise RuntimeError(
            f"{method} {url} failed with HTTP {error.code}: {detail}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"{method} {url} failed: {error.reason}") from error

    if not raw_body:
        return {}
    return json.loads(raw_body.decode("utf-8"))


def _base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _admin_users_url(base_url: str, email: str) -> str:
    query = urllib.parse.urlencode({"filter": email.lower()})
    return f"{_base_url(base_url)}/auth/v1/admin/users?{query}"


def _users_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("users"), list):
        return [user for user in payload["users"] if isinstance(user, dict)]
    if isinstance(payload, list):
        return [user for user in payload if isinstance(user, dict)]
    return []


def find_user_by_email(
    base_url: str,
    headers: dict[str, str],
    email: str,
) -> dict[str, Any] | None:
    target_email = email.lower()
    payload = request_json("GET", _admin_users_url(base_url, target_email), headers)
    for user in _users_from_payload(payload):
        user_email = user.get("email")
        if isinstance(user_email, str) and user_email.lower() == target_email:
            return user
    return None


def create_or_update_auth_user(
    base_url: str,
    headers: dict[str, str],
    persona: TestPersona,
) -> Any:
    existing_user = find_user_by_email(base_url, headers, persona.email)
    if existing_user:
        payload = build_user_payload(persona, existing_user)
        user_id = existing_user.get("id")
        if not isinstance(user_id, str) or not user_id:
            raise RuntimeError(f"existing user missing id for {persona.email.lower()}")
        url = f"{_base_url(base_url)}/auth/v1/admin/users/{urllib.parse.quote(user_id)}"
        return request_json("PUT", url, headers, payload)

    payload = build_user_payload(persona)
    url = f"{_base_url(base_url)}/auth/v1/admin/users"
    return request_json("POST", url, headers, payload)


def call_rpc(
    base_url: str,
    headers: dict[str, str],
    name: str,
    payload: dict[str, Any],
) -> Any:
    rpc_name = urllib.parse.quote(name)
    url = f"{_base_url(base_url)}/rest/v1/rpc/{rpc_name}"
    return request_json("POST", url, headers, payload)


def set_quota_exemption(
    base_url: str,
    headers: dict[str, str],
    user_id: str,
    exempt: bool,
    reason: str,
) -> Any:
    url = (
        f"{_base_url(base_url)}/rest/v1/internal_user_entitlements"
        "?on_conflict=user_id"
    )
    request_headers = dict(headers)
    request_headers["Prefer"] = "resolution=merge-duplicates"
    payload = {
        "user_id": user_id,
        "fresh_report_quota_exempt": exempt,
        "reason": reason,
        "expires_at": None,
    }
    return request_json("POST", url, request_headers, payload)


def load_dotenv(path: str | Path = ".env") -> None:
    dotenv_path = Path(path)
    if not dotenv_path.is_file():
        return

    for line in dotenv_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def build_personas_from_env() -> list[TestPersona]:
    return [
        TestPersona(
            email=os.environ.get("WHIDBY_TEST_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL),
            password=_required_env("WHIDBY_TEST_ADMIN_PASSWORD"),
            name=os.environ.get("WHIDBY_TEST_ADMIN_NAME", "Widby Admin Test"),
            member_role="admin",
            plan_key="free",
            widby_role="admin",
            quota_exempt=True,
        ),
        TestPersona(
            email=os.environ.get("WHIDBY_TEST_USER_EMAIL", DEFAULT_USER_EMAIL),
            password=_required_env("WHIDBY_TEST_USER_PASSWORD"),
            name=os.environ.get("WHIDBY_TEST_USER_NAME", "Widby User Test"),
            member_role="owner",
            plan_key="free",
            widby_role="user",
            quota_exempt=False,
        ),
        TestPersona(
            email=os.environ.get("WHIDBY_BETA_HENOCK_EMAIL", DEFAULT_HENOCK_EMAIL),
            password=_required_env("WHIDBY_BETA_HENOCK_PASSWORD"),
            name=os.environ.get("WHIDBY_BETA_HENOCK_NAME", "Henock"),
            member_role="admin",
            plan_key="free",
            widby_role="admin",
            quota_exempt=True,
        ),
        TestPersona(
            email=os.environ.get("WHIDBY_BETA_ANTWOINE_EMAIL", DEFAULT_ANTWOINE_EMAIL),
            password=_required_env("WHIDBY_BETA_ANTWOINE_PASSWORD"),
            name=os.environ.get("WHIDBY_BETA_ANTWOINE_NAME", "Antwoine"),
            member_role="admin",
            plan_key="free",
            widby_role="admin",
            quota_exempt=True,
        ),
        TestPersona(
            email=os.environ.get("WHIDBY_BETA_LUKE_EMAIL", DEFAULT_LUKE_EMAIL),
            password=_required_env("WHIDBY_BETA_LUKE_PASSWORD"),
            name=os.environ.get("WHIDBY_BETA_LUKE_NAME", "Luke"),
            member_role="owner",
            plan_key="pro",
            widby_role="user",
            quota_exempt=False,
        ),
    ]


def _auth_user_id(payload: Any) -> str:
    if isinstance(payload, dict):
        user_id = payload.get("id")
        if isinstance(user_id, str) and user_id:
            return user_id
        user = payload.get("user")
        if isinstance(user, dict):
            nested_id = user.get("id")
            if isinstance(nested_id, str) and nested_id:
                return nested_id
    raise RuntimeError("Auth Admin response did not include a user id")


def seed_persona(
    base_url: str,
    headers: dict[str, str],
    persona: TestPersona,
    reason: str,
) -> dict[str, Any]:
    auth_user = create_or_update_auth_user(base_url, headers, persona)
    user_id = _auth_user_id(auth_user)
    email = persona.email.lower()

    call_rpc(
        base_url,
        headers,
        "ensure_account_for_user_admin",
        {
            "p_user_id": user_id,
            "p_email": email,
            "p_member_role": persona.member_role,
            "p_plan_key": persona.plan_key,
            "p_overwrite_existing": True,
        },
    )
    set_quota_exemption(
        base_url,
        headers,
        user_id,
        persona.quota_exempt,
        reason,
    )

    return {
        "email": email,
        "user_id": user_id,
        "member_role": persona.member_role,
        "plan_key": persona.plan_key,
        "quota_exempt": persona.quota_exempt,
    }


def main() -> int:
    load_dotenv()
    base_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base_url:
        raise RuntimeError("missing required environment variable: SUPABASE_URL")
    if not service_role_key:
        raise RuntimeError(
            "missing required environment variable: SUPABASE_SERVICE_ROLE_KEY"
        )

    reason = os.environ.get(
        "WHIDBY_TEST_ACCOUNT_REASON",
        "seeded by scripts/supabase/seed_test_accounts.py",
    )
    headers = build_headers(service_role_key)
    summaries = [
        seed_persona(base_url, headers, persona, reason)
        for persona in build_personas_from_env()
    ]
    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"seed_test_accounts failed: {error}", file=sys.stderr)
        raise SystemExit(1)
