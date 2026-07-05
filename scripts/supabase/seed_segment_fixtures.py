"""Seed deterministic onboarding segment fixtures for local E2E coverage."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.supabase.seed_test_accounts import (
    TestPersona,
    _auth_user_id,
    build_headers,
    call_rpc,
    create_or_update_auth_user,
    load_dotenv,
    request_json,
    set_quota_exemption,
)


COMMON_PASSWORD_ENV = "WHIDBY_SEGMENT_FIXTURE_PASSWORD"
SEED_REASON = "seeded by scripts/supabase/seed_segment_fixtures.py"


@dataclass(frozen=True)
class SegmentFixtureDefaults:
    segment: str
    email_env: str
    default_email: str
    password_env: str
    name: str
    member_role: str
    plan_key: str
    widby_role: str
    quota_exempt: bool
    intent: str
    focus: str
    next_route: str
    profile_id: str
    target_id: str
    strategy_id: str
    available_strategy_ids: tuple[str, ...]
    niche_keyword: str
    city: str
    state: str
    seeded_data: str
    coach_or_agency: str | None = None
    report_id: str | None = None
    declaration_id: str | None = None


@dataclass(frozen=True)
class SegmentFixture:
    defaults: SegmentFixtureDefaults
    persona: TestPersona


FIXTURE_DEFAULTS: tuple[SegmentFixtureDefaults, ...] = (
    SegmentFixtureDefaults(
        segment="find_first",
        email_env="WHIDBY_SEGMENT_FIND_FIRST_EMAIL",
        default_email="segment-find-first@widby.dev",
        password_env="WHIDBY_SEGMENT_FIND_FIRST_PASSWORD",
        name="Widby Segment Find First",
        member_role="owner",
        plan_key="free",
        widby_role="user",
        quota_exempt=False,
        intent="find_first",
        focus="niche",
        next_route="/",
        profile_id="00000000-0000-4000-8000-000000010154",
        target_id="00000000-0000-4000-8000-000000020154",
        strategy_id="easy_win",
        available_strategy_ids=("easy_win", "gbp_blitz", "keyword_hijack"),
        niche_keyword="roofing contractor",
        city="Akron",
        state="OH",
        seeded_data="onboarding only; no report or ranked-site declaration",
    ),
    SegmentFixtureDefaults(
        segment="scale",
        email_env="WHIDBY_SEGMENT_SCALE_EMAIL",
        default_email="segment-scale@widby.dev",
        password_env="WHIDBY_SEGMENT_SCALE_PASSWORD",
        name="Widby Segment Scale",
        member_role="owner",
        plan_key="plus",
        widby_role="user",
        quota_exempt=False,
        intent="scale",
        focus="replicate",
        next_route="/strategies",
        profile_id="00000000-0000-4000-8000-000000030154",
        target_id="00000000-0000-4000-8000-000000040154",
        strategy_id="expand_conquer",
        available_strategy_ids=("expand_conquer", "easy_win", "gbp_blitz"),
        niche_keyword="tree service",
        city="Greenville",
        state="SC",
        seeded_data="account report history plus active ranked-site declaration",
        report_id="00000000-0000-4000-8000-000000000154",
        declaration_id="00000000-0000-4000-8000-000000001154",
    ),
    SegmentFixtureDefaults(
        segment="coach_agency",
        email_env="WHIDBY_SEGMENT_COACH_AGENCY_EMAIL",
        default_email="segment-coach-agency@widby.dev",
        password_env="WHIDBY_SEGMENT_COACH_AGENCY_PASSWORD",
        name="Widby Segment Coach Agency",
        member_role="admin",
        plan_key="pro",
        widby_role="admin",
        quota_exempt=False,
        intent="coach_agency",
        focus="agency",
        next_route="/agency",
        profile_id="00000000-0000-4000-8000-000000050154",
        target_id="00000000-0000-4000-8000-000000060154",
        strategy_id="easy_win",
        available_strategy_ids=(
            "easy_win",
            "gbp_blitz",
            "expand_conquer",
            "keyword_hijack",
            "portfolio_builder",
        ),
        niche_keyword="hvac",
        city="Phoenix",
        state="AZ",
        seeded_data="agency intent with admin-capable account membership",
        coach_or_agency="agency",
    ),
    SegmentFixtureDefaults(
        segment="researching",
        email_env="WHIDBY_SEGMENT_RESEARCHING_EMAIL",
        default_email="segment-researching@widby.dev",
        password_env="WHIDBY_SEGMENT_RESEARCHING_PASSWORD",
        name="Widby Segment Researching",
        member_role="owner",
        plan_key="free",
        widby_role="user",
        quota_exempt=False,
        intent="researching",
        focus="process",
        next_route="/explore",
        profile_id="00000000-0000-4000-8000-000000070154",
        target_id="00000000-0000-4000-8000-000000080154",
        strategy_id="easy_win",
        available_strategy_ids=("easy_win", "gbp_blitz", "keyword_hijack"),
        niche_keyword="plumbing",
        city="Pittsburgh",
        state="PA",
        seeded_data="cached Explore browse route with no fresh scan requirement",
    ),
)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def _password_for(defaults: SegmentFixtureDefaults, require_password: bool) -> str:
    password = os.environ.get(defaults.password_env) or os.environ.get(COMMON_PASSWORD_ENV)
    if password:
        return password
    if require_password:
        raise RuntimeError(
            "missing required password environment variable: "
            f"{defaults.password_env} or {COMMON_PASSWORD_ENV}"
        )
    return ""


def build_segment_fixtures(*, require_passwords: bool = True) -> list[SegmentFixture]:
    fixtures: list[SegmentFixture] = []
    for defaults in FIXTURE_DEFAULTS:
        persona = TestPersona(
            email=os.environ.get(defaults.email_env, defaults.default_email),
            password=_password_for(defaults, require_passwords),
            name=defaults.name,
            member_role=defaults.member_role,
            plan_key=defaults.plan_key,
            widby_role=defaults.widby_role,
            quota_exempt=defaults.quota_exempt,
        )
        fixtures.append(SegmentFixture(defaults=defaults, persona=persona))
    return fixtures


def fixture_manifest(fixtures: list[SegmentFixture]) -> list[dict[str, Any]]:
    return [
        {
            "segment": fixture.defaults.segment,
            "email": fixture.persona.email.lower(),
            "plan_key": fixture.persona.plan_key,
            "member_role": fixture.persona.member_role,
            "intent": fixture.defaults.intent,
            "focus": fixture.defaults.focus,
            "next_route": fixture.defaults.next_route,
            "profile_id": fixture.defaults.profile_id,
            "target_id": fixture.defaults.target_id,
            "report_id": fixture.defaults.report_id,
            "declaration_id": fixture.defaults.declaration_id,
            "seeded_data": fixture.defaults.seeded_data,
            "quota_exempt": fixture.persona.quota_exempt,
        }
        for fixture in fixtures
    ]


def onboarding_profile_payload(
    fixture: SegmentFixture,
    *,
    user_id: str,
    account_id: str,
) -> dict[str, Any]:
    defaults = fixture.defaults
    payload: dict[str, Any] = {
        "id": defaults.profile_id,
        "user_id": user_id,
        "account_id": account_id,
        "intent": defaults.intent,
        "focus": defaults.focus,
        "coach_or_agency": defaults.coach_or_agency,
        "referral_source": "segment_fixture",
        "recommended_strategy_id": defaults.strategy_id,
        "available_strategy_ids": list(defaults.available_strategy_ids),
        "next_route": defaults.next_route,
        "status": "strategy_recommended",
        "completed_at": "2026-07-05T00:00:00Z",
    }
    if defaults.intent == "researching":
        payload["status"] = "cached_route_selected"
    return payload


def onboarding_target_payload(fixture: SegmentFixture) -> dict[str, Any]:
    defaults = fixture.defaults
    return {
        "id": defaults.target_id,
        "onboarding_profile_id": defaults.profile_id,
        "strategy_id": defaults.strategy_id,
        "niche_keyword": defaults.niche_keyword,
        "service_category_id": defaults.niche_keyword.replace(" ", "_"),
        "geo_scope": "city",
        "city": defaults.city,
        "state": defaults.state,
        "cbsa_code": None,
        "place_id": None,
        "dataforseo_location_code": None,
        "resolved_label": f"{defaults.city}, {defaults.state} {defaults.niche_keyword}",
        "metadata_source": "typed",
    }


def report_payload(
    fixture: SegmentFixture,
    *,
    user_id: str,
    account_id: str,
) -> dict[str, Any] | None:
    defaults = fixture.defaults
    if not defaults.report_id:
        return None
    return {
        "id": defaults.report_id,
        "niche_keyword": defaults.niche_keyword,
        "geo_scope": "city",
        "geo_target": f"{defaults.city}, {defaults.state}",
        "report_depth": "segment_fixture",
        "strategy_profile": defaults.strategy_id,
        "resolved_weights": {},
        "keyword_expansion": {},
        "metros": [
            {
                "cbsa_code": "24860",
                "cbsa_name": "Greenville-Anderson-Greer, SC",
                "city": defaults.city,
                "state": defaults.state,
                "population": 975480,
                "serp_archetype": "FRAG_WEAK",
                "difficulty_tier": "MODERATE",
                "ai_exposure": "AI_MINIMAL",
                "scores": {
                    "demand": 72,
                    "organic_competition": 68,
                    "local_competition": 64,
                    "monetization": 76,
                    "ai_resilience": 82,
                    "opportunity": 74,
                    "confidence": {"score": 88},
                },
                "signals": {
                    "demand": {
                        "total_search_volume": 4200,
                        "avg_cpc": 9.8,
                    },
                    "organic_competition": {
                        "avg_top5_da": 24,
                    },
                    "local_competition": {
                        "top3_review_count_min": 18,
                    },
                    "monetization": {
                        "business_density": 42,
                    },
                    "ai_resilience": {
                        "aio_trigger_rate": 0.04,
                    },
                },
                "guidance": {
                    "summary": "Seeded scale fixture report for safe dashboard/report history rendering.",
                    "action_items": ["Use the ranked-site declaration to validate scale routing."],
                },
            }
        ],
        "meta": {
            "fixture": "whi154_segment_fixture",
            "segment": defaults.segment,
            "next_route": defaults.next_route,
        },
        "owner_account_id": account_id,
        "created_by_user_id": user_id,
        "access_scope": "account",
        "archived_at": None,
    }


def ranked_site_declaration_payload(
    fixture: SegmentFixture,
    *,
    user_id: str,
    account_id: str,
) -> dict[str, Any] | None:
    defaults = fixture.defaults
    if not defaults.declaration_id:
        return None
    return {
        "id": defaults.declaration_id,
        "account_id": account_id,
        "created_by_user_id": user_id,
        "updated_by_user_id": user_id,
        "site_name": "Segment Scale Fixture Site",
        "site_url": "https://segment-scale-fixture.example",
        "site_domain": "segment-scale-fixture.example",
        "city": defaults.city,
        "state": defaults.state,
        "cbsa_code": None,
        "niche_keyword": defaults.niche_keyword,
        "niche_normalized": defaults.niche_keyword.replace(" ", "_"),
        "proof_state": "declared",
        "active": True,
        "metadata": {
            "fixture": "whi154_segment_fixture",
            "segment": defaults.segment,
            "report_id": defaults.report_id,
        },
        "declared_at": "2026-07-05T00:00:00Z",
        "verified_at": None,
        "deactivated_at": None,
    }


def _upsert_rows(
    base_url: str,
    headers: dict[str, str],
    table: str,
    rows: list[dict[str, Any]],
) -> Any:
    if not rows:
        return {}
    request_headers = dict(headers)
    request_headers["Prefer"] = "resolution=merge-duplicates"
    url = f"{base_url.rstrip('/')}/rest/v1/{table}?on_conflict=id"
    return request_json("POST", url, request_headers, rows)


def _account_id_from_rpc(payload: Any) -> str:
    if isinstance(payload, str) and payload:
        return payload
    if isinstance(payload, dict):
        account_id = payload.get("account_id") or payload.get("id")
        if isinstance(account_id, str) and account_id:
            return account_id
    if isinstance(payload, list) and payload:
        return _account_id_from_rpc(payload[0])
    raise RuntimeError("ensure_account_for_user_admin response did not include an account id")


def seed_segment_fixture(
    base_url: str,
    headers: dict[str, str],
    fixture: SegmentFixture,
) -> dict[str, Any]:
    auth_user = create_or_update_auth_user(base_url, headers, fixture.persona)
    user_id = _auth_user_id(auth_user)
    account_id = _account_id_from_rpc(
        call_rpc(
            base_url,
            headers,
            "ensure_account_for_user_admin",
            {
                "p_user_id": user_id,
                "p_email": fixture.persona.email.lower(),
                "p_member_role": fixture.persona.member_role,
                "p_plan_key": fixture.persona.plan_key,
                "p_overwrite_existing": True,
            },
        )
    )
    set_quota_exemption(
        base_url,
        headers,
        user_id,
        fixture.persona.quota_exempt,
        SEED_REASON,
    )

    profile = onboarding_profile_payload(
        fixture,
        user_id=user_id,
        account_id=account_id,
    )
    target = onboarding_target_payload(fixture)
    report = report_payload(fixture, user_id=user_id, account_id=account_id)
    declaration = ranked_site_declaration_payload(
        fixture,
        user_id=user_id,
        account_id=account_id,
    )

    _upsert_rows(base_url, headers, "onboarding_profiles", [profile])
    _upsert_rows(base_url, headers, "onboarding_targets", [target])
    if report:
        _upsert_rows(base_url, headers, "reports", [report])
    if declaration:
        _upsert_rows(base_url, headers, "ranked_site_declarations", [declaration])

    return {
        "segment": fixture.defaults.segment,
        "email": fixture.persona.email.lower(),
        "user_id": user_id,
        "account_id": account_id,
        "plan_key": fixture.persona.plan_key,
        "next_route": fixture.defaults.next_route,
        "profile_id": fixture.defaults.profile_id,
        "target_id": fixture.defaults.target_id,
        "report_id": fixture.defaults.report_id,
        "declaration_id": fixture.defaults.declaration_id,
    }


def seed_segment_fixtures(
    base_url: str,
    service_role_key: str,
    fixtures: list[SegmentFixture],
) -> list[dict[str, Any]]:
    headers = build_headers(service_role_key)
    return [seed_segment_fixture(base_url, headers, fixture) for fixture in fixtures]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed deterministic Wave 2 onboarding segment fixtures."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print fixture manifest without requiring Supabase secrets.",
    )
    args = parser.parse_args(argv)

    load_dotenv()
    fixtures = build_segment_fixtures(require_passwords=not args.dry_run)

    if args.dry_run:
        print(json.dumps(fixture_manifest(fixtures), indent=2, sort_keys=True))
        return 0

    base_url = _required_env("SUPABASE_URL")
    service_role_key = _required_env("SUPABASE_SERVICE_ROLE_KEY")
    summaries = seed_segment_fixtures(base_url, service_role_key, fixtures)
    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"seed_segment_fixtures failed: {error}", file=sys.stderr)
        raise SystemExit(1)
