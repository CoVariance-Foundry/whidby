"""Dedicated benchmark runner — pilot phase (200 reports).

Populates `seo_facts` with keyword-grain market observations across a
stratified sample of (niche, metro) pairs. Skips V1.1 scoring entirely —
no writes to reports/metro_signals/metro_scores.

Default pilot scope: 10 niches × 20 metros = 200 reports.
Full-sample scope: 10 niches × all metros in metros_sampled.json.
Per (niche, metro):
  1. Keyword expansion (cached per niche — one LLM call per niche total)
  2. DataForSEO keyword_volume (batched, one task per metro)
  3. DataForSEO SERP per top 2 keywords (extract AIO, local pack, aggregator,
     local biz, featured snippet, PAA, ads, LSA flags)
  4. Optional top-5 organic telemetry via backlinks summary + Lighthouse
  5. Optional top-3 local review velocity via Google Reviews
  6. Insert seo_facts rows via Supabase PostgREST

Usage:
  cd whidby
  python -m scripts.benchmarks.run_pilot

Reads credentials from .env in repo root.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib import error as urlerror
from urllib import request as urlreq
from uuid import uuid4

# Repo root + path injection so we can import src.* modules
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.clients.dataforseo import DataForSEOClient  # noqa: E402
from src.clients.llm.client import LLMClient  # noqa: E402
from src.clients.supabase_persistence import (  # noqa: E402
    build_seo_evidence_artifact_rows_from_cost_records,
    evidence_family_from_endpoint,
)
from src.config.constants import DFS_DEFAULT_LANGUAGE_CODE  # noqa: E402
from src.pipeline.keyword_expansion import expand_keywords  # noqa: E402
from src.pipeline.dfs_normalizers import normalize_gbp_info_rows  # noqa: E402
from src.pipeline.gbp_completeness import compute_gbp_completeness  # noqa: E402
from src.pipeline.review_velocity import compute_reviews_per_month  # noqa: E402
from scripts.utils.supabase_guard import supabase_project_ref  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("benchmark_runner")


# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
# Benchmark runs always go to STAGING. The .env's NEXT_PUBLIC_SUPABASE_URL
# points to prod; explicit benchmark overrides keep writes separated.
SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",  # staging
)
SUPABASE_KEY = (
    os.environ.get("BENCHMARK_SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)
DFS_LOGIN = os.environ.get("DATAFORSEO_LOGIN")
DFS_PASS = os.environ.get("DATAFORSEO_PASSWORD")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")

PILOT_NICHES = [
    "concrete contractor",
    "plumber",
    "roofing contractor",
    "landscaping",
    "pool builder",
    "auto repair",
    "junk removal",
    "dog grooming",
    "water damage restoration",
    "locksmith",
]

CORE_SERVICE_NICHES = [
    "roofing",
    "plumbing",
    "hvac",
    "tree service",
    "auto repair",
    "water damage restoration",
    "electrician",
    "locksmith",
]

SERVICE_KEY_ALIASES = {
    "plumber": "plumbing",
    "plumbing services": "plumbing",
    "roofing contractor": "roofing",
    "roofing contractors": "roofing",
    "roofing services": "roofing",
    "tree services": "tree service",
}

# Pilot picks 20 metros across pop classes (representative spread)
PILOT_METROS_PER_CLASS = {
    "mega_5m_plus": 2,
    "metro_1m_5m": 4,
    "large_300k_1m": 5,
    "medium_100_300k": 5,
    "small_50_100k": 3,
    "micro_under_50k": 1,
}

CONCURRENCY = 6  # how many (niche, metro) pairs to score in parallel
KNOWN_AGGREGATORS = {
    "yelp.com", "homeadvisor.com", "angi.com", "angieslist.com", "thumbtack.com",
    "bbb.org", "bark.com", "houzz.com", "expertise.com", "chamberofcommerce.com",
    "mapquest.com", "yellowpages.com", "superpages.com", "manta.com", "nextdoor.com",
    "porch.com", "networx.com", "topratedlocal.com", "buildzoom.com", "fixr.com",
}


@dataclass
class RunStats:
    reports_attempted: int = 0
    reports_succeeded: int = 0
    reports_failed: int = 0
    facts_inserted: int = 0
    failures: list[str] = field(default_factory=list)
    failure_reasons: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"reports: {self.reports_succeeded}/{self.reports_attempted} succeeded, "
            f"{self.reports_failed} failed; facts inserted: {self.facts_inserted}"
        )

    def record_failure(self, niche: str, cbsa_code: str, reason: str, detail: str = "") -> None:
        self.failure_reasons[reason] = self.failure_reasons.get(reason, 0) + 1
        suffix = f": {detail}" if detail else ""
        self.failures.append(f"{niche}@{cbsa_code}: {reason}{suffix}")


@dataclass(frozen=True)
class VolumeAttemptFailure:
    location_code: int
    reason: str
    detail: str


@dataclass(frozen=True)
class VolumeCollectionResult:
    volume_by_kw: dict[str, dict[str, Any]]
    valid_location_codes: list[int]
    failures: list[VolumeAttemptFailure]


@dataclass(frozen=True)
class OrganicTelemetryResult:
    fields: dict[str, Any]
    failures: list[str]


@dataclass(frozen=True)
class GbpProfileCollectionResult:
    rows: list[dict[str, Any]]
    failures: list[str]


BENCHMARK_PAID_POPULATION_CLASSES = {
    "mega_5m_plus",
    "metro_1m_5m",
    "large_300k_1m",
    "medium_100_300k",
}
LOW_SIGNAL_POPULATION_CLASSES = {"small_50_100k", "micro_under_50k"}
UNRESOLVED_DFS_MATCH_CONFIDENCE = {
    "ambiguous",
    "invalid_existing_code",
    "no_match",
}
CBSA_CODE_RE = re.compile(r"^\d{5}$")


def positive_int(value: str) -> int:
    """Parse a positive integer for optional batch-size controls."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect benchmark seo_facts for stratified (niche, metro) pairs."
    )
    parser.add_argument("--limit-pairs", type=positive_int, default=None)
    parser.add_argument(
        "--niche",
        action="append",
        default=None,
        help="Pilot niche to run. Repeat to run multiple niches in CLI order.",
    )
    parser.add_argument(
        "--population-class",
        action="append",
        default=None,
        help="Population class to include. Repeat to include multiple classes.",
    )
    parser.add_argument(
        "--cbsa-code",
        action="append",
        default=None,
        help=(
            "Fetch and run exact production metro CBSA code(s) from Supabase. "
            "Repeat to target a bounded telemetry batch."
        ),
    )
    parser.add_argument(
        "--sample-mode",
        choices=("pilot", "full"),
        default="pilot",
        help="Use pilot metro subset or every metro in metros_sampled.json.",
    )
    parser.add_argument(
        "--full-sample",
        action="store_const",
        const="full",
        dest="sample_mode",
        help="Shortcut for --sample-mode full.",
    )
    parser.add_argument(
        "--include-low-signal",
        action="store_true",
        help=(
            "Diagnostic escape hatch: include low-signal and borrowed-code metros "
            "that paid benchmark runs exclude by default."
        ),
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate keyword-volume coverage without SERP pulls or Supabase writes.",
    )
    parser.add_argument(
        "--collect-organic-telemetry",
        action="store_true",
        help=(
            "Opt in to paid top-5 organic DA/Lighthouse collection for benchmark "
            "facts. Uses SERP organic URLs, backlinks summary, and Lighthouse."
        ),
    )
    parser.add_argument(
        "--collect-review-velocity",
        action="store_true",
        help=(
            "Opt in to paid Google Reviews calls for top-3 local pack review "
            "velocity."
        ),
    )
    parser.add_argument(
        "--collect-gbp-profile",
        action="store_true",
        help=(
            "Opt in to paid Google My Business Info calls for top-3 local pack "
            "profile completeness."
        ),
    )
    parser.add_argument(
        "--organic-telemetry-limit",
        type=positive_int,
        default=5,
        help="Maximum non-aggregator organic result URLs to enrich per pair (default: 5).",
    )
    parser.add_argument(
        "--review-depth",
        type=positive_int,
        default=10,
        help="Google Reviews depth per top-3 local pack item (default: 10).",
    )
    parser.add_argument(
        "--require-dfs",
        action="store_true",
        help="Fail if selected metros are not paid-eligible native DataForSEO targets.",
    )
    parser.add_argument(
        "--require-v2-persistence",
        action="store_true",
        help=(
            "Require selected pairs to already have metro_score_v2 and seo_facts rows "
            "before running paid benchmark enrichment."
        ),
    )
    parser.add_argument(
        "--expected-project-ref",
        default=None,
        help=(
            "Optional Supabase project ref guard. When set, BENCHMARK_SUPABASE_URL "
            "must point at this project before any writes or paid collection run."
        ),
    )
    return parser.parse_args()


def fail_cli(message: str) -> None:
    print(f"run_pilot.py: error: {message}", file=sys.stderr)
    sys.exit(2)


def persistence_niche_key(niche: str) -> str:
    """Normalize pilot labels to the persisted scoring service key."""
    text = " ".join(niche.strip().lower().split())
    if text in SERVICE_KEY_ALIASES:
        return SERVICE_KEY_ALIASES[text]
    if text in CORE_SERVICE_NICHES:
        return text
    for suffix in (" services", " contractors", " contractor", " companies", " company"):
        if text.endswith(suffix):
            return text[: -len(suffix)].strip()
    if text.endswith(" service"):
        return text[: -len(" service")].strip()
    return text


def validate_expected_project_ref(expected_project_ref: str | None) -> None:
    """Fail fast when a caller pins an expected Supabase project ref."""
    if not expected_project_ref:
        return

    actual_project_ref = supabase_project_ref(SUPABASE_URL)
    if actual_project_ref != expected_project_ref:
        actual = actual_project_ref or "<unknown>"
        fail_cli(
            "Supabase project ref mismatch: "
            f"expected {expected_project_ref}, got {actual} from BENCHMARK_SUPABASE_URL"
        )


def validate_paid_targets(metros: list[dict[str, Any]], *, require_dfs: bool) -> None:
    """Reject paid canaries that would target borrowed-code or low-signal metros."""
    if not require_dfs:
        return

    ineligible = [
        (
            metro.get("cbsa_code") or "<unknown>",
            metro.get("cbsa_name") or "<unknown>",
            native_dfs_exclusion_reason(metro),
        )
        for metro in metros
        if native_dfs_exclusion_reason(metro) is not None
    ]
    if not ineligible:
        return

    examples = ", ".join(
        f"{name} ({cbsa_code}: {reason})"
        for cbsa_code, name, reason in ineligible[:5]
    )
    suffix = f"; {len(ineligible) - 5} more" if len(ineligible) > 5 else ""
    fail_cli(f"--require-dfs selected ineligible benchmark metros: {examples}{suffix}")


def native_dfs_exclusion_reason(metro: dict[str, Any]) -> str | None:
    """Return why a metro is not a native paid DataForSEO benchmark target."""
    population_class = metro.get("population_class")
    source = metro.get("_dfs_source") or "native"
    loc_codes = list(
        metro.get("keyword_volume_location_codes")
        or metro.get("dataforseo_location_codes")
        or []
    )
    if population_class in LOW_SIGNAL_POPULATION_CLASSES:
        return "population_too_small"
    if population_class not in BENCHMARK_PAID_POPULATION_CLASSES:
        return "population_too_small"
    if source != "native":
        return "no_native_dfs_code"
    if not loc_codes:
        return "no_native_dfs_code"
    if not metro.get("paid_eligible"):
        return metro.get("benchmark_exclusion_reason") or "not_paid_eligible"
    return None


def postgrest_has_row(table: str, filters: dict[str, str]) -> bool:
    """Return true if a PostgREST table has at least one row for exact filters."""
    if not SUPABASE_KEY:
        raise RuntimeError("BENCHMARK_SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY is required")

    query = {"select": "cbsa_code", "limit": "1"}
    query.update({key: f"eq.{value}" for key, value in filters.items()})
    url = f"{SUPABASE_URL}/rest/v1/{table}?{urlencode(query)}"
    req = urlreq.Request(
        url,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        method="GET",
    )
    try:
        with urlreq.urlopen(req, timeout=30) as response:
            return bool(json.loads(response.read().decode() or "[]"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode()[:200]
        raise RuntimeError(f"{table} lookup failed: status={exc.code} {detail}") from exc
    except (urlerror.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        detail = str(reason) if reason is not None else str(exc)
        raise RuntimeError(f"{table} lookup failed: {exc.__class__.__name__}: {detail}") from exc


def validate_v2_persistence(
    pairs: list[tuple[str, dict[str, Any]]],
    *,
    require_v2_persistence: bool,
) -> None:
    """Require canary targets to already be V2-scored and fact-backed."""
    if not require_v2_persistence:
        return

    missing: list[str] = []
    for niche, metro in pairs:
        cbsa_code = str(metro.get("cbsa_code") or "")
        service_key = persistence_niche_key(niche)
        filters = {"cbsa_code": cbsa_code, "niche_normalized": service_key}
        pair_label = f"{niche}@{cbsa_code}"
        try:
            if not postgrest_has_row("metro_score_v2", filters):
                missing.append(f"{pair_label}: metro_score_v2")
            if not postgrest_has_row("seo_facts", filters):
                missing.append(f"{pair_label}: seo_facts")
        except RuntimeError as exc:
            fail_cli(str(exc))

    if not missing:
        return

    examples = ", ".join(missing[:6])
    suffix = f"; {len(missing) - 6} more" if len(missing) > 6 else ""
    fail_cli(f"--require-v2-persistence missing prerequisite rows: {examples}{suffix}")


def select_niches(requested: list[str] | None) -> list[str]:
    if not requested:
        return PILOT_NICHES

    allowed_labels = set(PILOT_NICHES) | set(CORE_SERVICE_NICHES)
    allowed_keys = {persistence_niche_key(niche) for niche in allowed_labels}
    selected: list[str] = []
    seen_keys: set[str] = set()
    for niche in requested:
        normalized = " ".join(niche.strip().lower().split())
        service_key = persistence_niche_key(niche)
        if normalized not in allowed_labels and service_key not in allowed_keys:
            allowed = ", ".join(dict.fromkeys([*PILOT_NICHES, *CORE_SERVICE_NICHES]))
            fail_cli(f"unknown niche {niche!r}; expected one of: {allowed}")
        if service_key not in seen_keys:
            selected.append(service_key)
            seen_keys.add(service_key)

    return selected


# -------------------------------------------------------------------
# Sampling plan loader
# -------------------------------------------------------------------
def attach_state_dfs_fallback(metros: list[dict[str, Any]], full_sample: list[dict[str, Any]]) -> None:
    """Attach state-level DFS fallback codes to selected metros in place."""
    state_dfs: dict[str, list[int]] = {}
    for m in sorted(full_sample, key=lambda x: -(x.get("population") or 0)):
        codes = m.get("dataforseo_location_codes") or []
        if codes and m["state"] not in state_dfs:
            state_dfs[m["state"]] = codes

    for m in metros:
        if not m.get("dataforseo_location_codes"):
            fallback = state_dfs.get(m["state"], [])
            if fallback:
                m["dataforseo_location_codes"] = fallback
                m["_dfs_source"] = "state_borrow"
            else:
                m["_dfs_source"] = "none"
        else:
            m["_dfs_source"] = "native"


def mark_benchmark_eligibility(metro: dict[str, Any], *, include_low_signal: bool) -> None:
    """Annotate one metro with paid benchmark eligibility metadata."""
    population_class = metro.get("population_class")
    loc_codes = list(
        metro.get("keyword_volume_location_codes")
        or metro.get("dataforseo_location_codes")
        or []
    )
    source = metro.get("_dfs_source") or ("native" if loc_codes else "none")
    reason = None

    if population_class in LOW_SIGNAL_POPULATION_CLASSES and not include_low_signal:
        reason = "population_too_small"
    elif population_class not in BENCHMARK_PAID_POPULATION_CLASSES and not include_low_signal:
        reason = "population_too_small"
    elif str(metro.get("dataforseo_location_match_confidence") or "") in (
        UNRESOLVED_DFS_MATCH_CONFIDENCE
    ):
        reason = "no_native_dfs_code"
    elif source != "native" and not include_low_signal:
        reason = "no_native_dfs_code"
    elif not loc_codes:
        reason = "no_native_dfs_code"

    metro["keyword_volume_location_codes"] = loc_codes
    metro["paid_eligible"] = reason is None
    metro["benchmark_exclusion_reason"] = reason


def select_metros(
    full: list[dict[str, Any]],
    sample_mode: str,
    *,
    include_low_signal: bool = False,
) -> list[dict[str, Any]]:
    """Select pilot metros by default, or all sampled metros for full coverage runs."""
    if sample_mode == "full":
        selected = [dict(m) for m in full]
        for metro in selected:
            metro["_dfs_source"] = "native" if metro.get("dataforseo_location_codes") else "none"
        if include_low_signal:
            attach_state_dfs_fallback(selected, full)
        for metro in selected:
            mark_benchmark_eligibility(metro, include_low_signal=include_low_signal)
        return selected if include_low_signal else [m for m in selected if m["paid_eligible"]]

    by_class: dict[str, list[dict]] = {}
    for m in full:
        by_class.setdefault(m["population_class"], []).append(m)

    pilot: list[dict] = []
    for cls, n in PILOT_METROS_PER_CLASS.items():
        pool = by_class.get(cls, [])
        with_dfs = [m for m in pool if m.get("dataforseo_location_codes")]
        without_dfs = [m for m in pool if not m.get("dataforseo_location_codes")]
        ordered = with_dfs + without_dfs
        pilot.extend(dict(m) for m in ordered[:n])

    for metro in pilot:
        metro["_dfs_source"] = "native" if metro.get("dataforseo_location_codes") else "none"
    if include_low_signal:
        attach_state_dfs_fallback(pilot, full)
    for metro in pilot:
        mark_benchmark_eligibility(metro, include_low_signal=include_low_signal)
    return pilot if include_low_signal else [m for m in pilot if m["paid_eligible"]]


def load_full_sample(metros_path: Path) -> list[dict[str, Any]]:
    """Load the full sampled metro plan."""
    return json.loads(metros_path.read_text())


def fetch_metros_by_cbsa(
    cbsa_codes: list[str],
    *,
    include_low_signal: bool,
) -> list[dict[str, Any]]:
    """Fetch exact production metros for a bounded benchmark telemetry batch."""
    if not SUPABASE_KEY:
        fail_cli("BENCHMARK_SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY is required for --cbsa-code")

    requested = list(dict.fromkeys(code.strip() for code in cbsa_codes if code.strip()))
    if not requested:
        fail_cli("--cbsa-code did not include any non-empty CBSA codes")
    invalid_codes = [code for code in requested if not CBSA_CODE_RE.fullmatch(code)]
    if invalid_codes:
        fail_cli(
            "--cbsa-code must be a 5-digit numeric CBSA code: "
            + ", ".join(invalid_codes)
        )

    select_columns = (
        "cbsa_code,cbsa_name,state,population,population_class,"
        "dataforseo_location_codes,dataforseo_location_match_confidence"
    )
    query = urlencode({
        "select": select_columns,
        "cbsa_code": f"in.({','.join(requested)})",
    })
    req = urlreq.Request(
        f"{SUPABASE_URL}/rest/v1/metros?{query}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        method="GET",
    )
    try:
        with urlreq.urlopen(req, timeout=30) as response:
            rows = json.loads(response.read().decode() or "[]")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode()[:200]
        fail_cli(f"metros lookup failed: status={exc.code} {detail}")
    except (urlerror.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        detail = str(reason) if reason is not None else str(exc)
        fail_cli(f"metros lookup failed: {exc.__class__.__name__}: {detail}")

    by_code = {str(row.get("cbsa_code") or ""): dict(row) for row in rows}
    missing = [code for code in requested if code not in by_code]
    if missing:
        fail_cli("--cbsa-code not found in production metros: " + ", ".join(missing))

    selected = [by_code[code] for code in requested]
    for metro in selected:
        metro["_dfs_source"] = (
            "native" if metro.get("dataforseo_location_codes") else "none"
        )
        mark_benchmark_eligibility(metro, include_low_signal=include_low_signal)
    ineligible = [
        (
            f"{metro.get('cbsa_code')}:"
            f"{metro.get('benchmark_exclusion_reason') or 'not_paid_eligible'}"
        )
        for metro in selected
        if not metro.get("paid_eligible")
    ]
    if ineligible and not include_low_signal:
        fail_cli("--cbsa-code selected ineligible benchmark metros: " + ", ".join(ineligible))
    return selected


def validate_population_classes(
    requested: list[str] | None,
    full_sample: list[dict[str, Any]],
) -> None:
    if not requested:
        return

    known_classes = sorted(
        {
            metro.get("population_class")
            for metro in full_sample
            if metro.get("population_class")
        }
    )
    known_set = set(known_classes)
    for population_class in requested:
        if population_class not in known_set:
            allowed = ", ".join(known_classes)
            fail_cli(
                f"unknown population class {population_class!r}; expected one of: {allowed}"
            )


def build_pairs(niches: list[str], metros: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Build a metro-major pair order so limited multi-niche runs cover each niche."""
    return [(niche, metro) for metro in metros for niche in niches]


# -------------------------------------------------------------------
# DFS helpers
# -------------------------------------------------------------------
def extract_domain(url: str) -> str:
    from urllib.parse import urlparse
    try:
        h = urlparse(url).hostname or ""
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def parse_serp_items(serp_data: Any) -> dict[str, Any]:
    """Extract V2 SERP feature flags from DataForSEOClient.serp_organic().data.

    Note: client unwraps `tasks[0].result` for us, so `data` is a list of result
    objects, each with `items`. We use the first result.
    """
    flags = {
        "aio_present": False,
        "local_pack_present": False,
        "local_pack_position": None,
        "aggregator_count_top10": 0,
        "local_biz_count_top10": 0,
        "featured_snippet_present": False,
        "paa_count": 0,
        "ads_present": False,
        "lsa_present": False,
        "top_local_pack_items": [],
        "organic_targets": [],
        "top3_review_count_min": None,
        "top3_review_count_avg": None,
        "top3_review_velocity_avg": None,
        "top3_rating_avg": None,
    }
    if not serp_data:
        return flags
    # Client returns data = task.result (list); take first result
    if isinstance(serp_data, list):
        first = serp_data[0] if serp_data else {}
    elif isinstance(serp_data, dict):
        first = serp_data
    else:
        return flags
    items = first.get("items") or []
    org_position = 0
    for item in items:
        t = item.get("type", "")
        if t == "ai_overview":
            flags["aio_present"] = True
        elif t == "local_pack":
            flags["local_pack_present"] = True
            if flags["local_pack_position"] is None:
                flags["local_pack_position"] = item.get("rank_absolute")
            local_pack_items = (
                item.get("items") if item.get("items") is not None else [item]
            )
            for sub in local_pack_items:
                if len(flags["top_local_pack_items"]) >= 3:
                    break
                rating = sub.get("rating") or {}
                listing = {
                    "title": sub.get("title"),
                    "rating": rating.get("value"),
                    "rating_count": rating.get("votes_count"),
                    "place_id": sub.get("place_id"),
                    "cid": sub.get("cid") or sub.get("data_cid"),
                }
                if any(value is not None for value in listing.values()):
                    flags["top_local_pack_items"].append(listing)
        elif t == "featured_snippet":
            flags["featured_snippet_present"] = True
        elif t == "people_also_ask":
            flags["paa_count"] += 1
        elif t == "paid":
            flags["ads_present"] = True
        elif t == "local_services":
            flags["lsa_present"] = True
        elif t == "organic":
            org_position += 1
            url = item.get("url") or ""
            domain = extract_domain(url)
            if org_position <= 10:
                if not domain:
                    continue
                if domain in KNOWN_AGGREGATORS:
                    flags["aggregator_count_top10"] += 1
                else:
                    flags["local_biz_count_top10"] += 1
                    if url and domain and len(flags["organic_targets"]) < 10:
                        flags["organic_targets"].append({
                            "url": url,
                            "domain": domain,
                            "title": item.get("title"),
                            "rank_absolute": item.get("rank_absolute"),
                        })
    review_counts = [
        item["rating_count"]
        for item in flags["top_local_pack_items"][:3]
        if isinstance(item.get("rating_count"), (int, float))
    ]
    ratings = [
        item["rating"]
        for item in flags["top_local_pack_items"][:3]
        if isinstance(item.get("rating"), (int, float))
    ]
    if review_counts:
        flags["top3_review_count_min"] = int(min(review_counts))
        flags["top3_review_count_avg"] = int(round(sum(review_counts) / len(review_counts)))
    if ratings:
        flags["top3_rating_avg"] = round(sum(ratings) / len(ratings), 2)
    return flags


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_dicts(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_backlinks_domain_authority(data: Any) -> float | None:
    """Extract a DataForSEO rank-like authority value from backlinks summary data."""
    for key in ("domain_rank", "domain_from_rank", "page_from_rank"):
        for row in _walk_dicts(data):
            value = _numeric(row.get(key))
            if value is not None:
                return value
    for row in _walk_dicts(data):
        value = _numeric(row.get("rank"))
        if value is not None:
            return value
    return None


def parse_lighthouse_performance_score(data: Any) -> float | None:
    """Extract a 0-100 Lighthouse performance score from DataForSEO data."""
    for row in _walk_dicts(data):
        categories = row.get("categories")
        if isinstance(categories, dict):
            performance = categories.get("performance")
            if isinstance(performance, dict):
                score = _numeric(performance.get("score"))
                if score is not None:
                    return round(score * 100 if score <= 1 else score, 4)

        for key in ("performance_score", "performance"):
            score = _numeric(row.get(key))
            if score is not None:
                return round(score * 100 if score <= 1 else score, 4)
    return None


def top5_organic_confidence(da_coverage: float, lighthouse_coverage: float) -> str:
    if da_coverage >= 0.8 and lighthouse_coverage >= 0.8:
        return "high"
    if da_coverage >= 0.6 or lighthouse_coverage >= 0.6:
        return "medium"
    if da_coverage > 0 or lighthouse_coverage > 0:
        return "low"
    return "missing"


def propagate_head_feature(
    serp_features_by_kw: dict[str, dict[str, Any]],
    head_features: dict[str, Any],
    key: str,
    value: Any,
) -> None:
    """Apply a metro-level head SERP feature to every keyword fact row."""
    head_features[key] = value
    for features in serp_features_by_kw.values():
        features[key] = value


def first_local_pack_features(
    serp_features_by_kw: dict[str, dict[str, Any]],
    *,
    fallback_keyword: str,
    fallback_features: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Return the first queried head SERP with usable local-pack listings."""
    for keyword, features in serp_features_by_kw.items():
        if features.get("top_local_pack_items"):
            return keyword, features
    return fallback_keyword, fallback_features


async def collect_organic_telemetry(
    dfs: DataForSEOClient,
    organic_targets: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> OrganicTelemetryResult:
    """Collect paid top-5 DA/Lighthouse telemetry for one market pair."""
    selected = organic_targets[: min(limit, 5)]
    da_values: list[float] = []
    lighthouse_values: list[float] = []
    failures: list[str] = []

    for target in selected:
        domain = target.get("domain")
        url = target.get("url")
        if domain:
            response = await dfs.backlinks_summary(str(domain), rank_scale="one_hundred")
            if response.status == "ok":
                da = parse_backlinks_domain_authority(response.data)
                if da is not None:
                    da_values.append(da)
                else:
                    failures.append(f"{domain}:backlinks_missing_rank")
            else:
                failures.append(f"{domain}:backlinks_failed:{response.error or 'error'}")
        if url:
            response = await dfs.lighthouse(str(url))
            if response.status == "ok":
                score = parse_lighthouse_performance_score(response.data)
                if score is not None:
                    lighthouse_values.append(score)
                else:
                    failures.append(f"{url}:lighthouse_missing_performance")
            else:
                failures.append(f"{url}:lighthouse_failed:{response.error or 'error'}")

    da_coverage = len(da_values) / 5.0
    lighthouse_coverage = len(lighthouse_values) / 5.0
    fields = {
        "avg_top5_da": round(sum(da_values) / len(da_values), 2) if da_values else None,
        "avg_top5_lighthouse": (
            round(sum(lighthouse_values) / len(lighthouse_values), 2)
            if lighthouse_values
            else None
        ),
        "top5_da_coverage": round(da_coverage, 4),
        "top5_lighthouse_coverage": round(lighthouse_coverage, 4),
        "top5_organic_data_confidence": top5_organic_confidence(
            da_coverage,
            lighthouse_coverage,
        ),
    }
    return OrganicTelemetryResult(fields=fields, failures=failures)


def extract_review_timestamps(data: Any) -> list[str]:
    """Extract review timestamps from DataForSEO Google Reviews task results."""
    timestamps: list[str] = []
    for row in _walk_dicts(data):
        timestamp = row.get("timestamp")
        if timestamp and any(
            row.get(key) is not None
            for key in ("review_text", "review_id", "rating", "profile_name", "text")
        ):
            timestamps.append(str(timestamp))
    return timestamps


async def collect_top3_review_velocity(
    dfs: DataForSEOClient,
    local_pack_items: list[dict[str, Any]],
    *,
    location_code: int,
    depth: int = 10,
) -> float | None:
    """Collect review timestamps for local top-3 listings and return avg velocity."""
    velocities: list[float] = []
    for item in local_pack_items[:3]:
        title = item.get("title")
        keyword = str(title) if title else None
        cid = item.get("cid")
        place_id = item.get("place_id")
        if not any((keyword, cid, place_id)):
            continue
        response = await dfs.google_reviews(
            keyword=keyword,
            location_code=location_code,
            depth=depth,
            language_code=DFS_DEFAULT_LANGUAGE_CODE,
            cid=cid,
            place_id=place_id,
            sort_by="newest",
        )
        if response.status != "ok":
            continue
        timestamps = extract_review_timestamps(response.data)
        if timestamps:
            velocities.append(compute_reviews_per_month(timestamps))
    return round(sum(velocities) / len(velocities), 4) if velocities else None


async def collect_top3_gbp_profile_facts(
    dfs: DataForSEOClient,
    local_pack_items: list[dict[str, Any]],
    *,
    cbsa_code: str,
    niche_normalized: str,
    keyword: str,
    location_code: int,
    snapshot_date: str,
) -> GbpProfileCollectionResult:
    """Collect GBP completeness facts for local top-3 listings."""
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for rank, item in enumerate(local_pack_items[:3], start=1):
        title = str(item.get("title") or "").strip()
        if not title:
            failures.append(f"rank_{rank}:missing_title")
            continue
        response = await dfs.google_my_business_info(
            keyword=title,
            location_code=location_code,
        )
        if response.status != "ok" or not response.data:
            failures.append(f"{title}:response_{response.status}")
            continue
        raw_rows = response.data if isinstance(response.data, list) else [response.data]
        profiles = normalize_gbp_info_rows([row for row in raw_rows if isinstance(row, dict)])
        if not profiles:
            failures.append(f"{title}:empty_profile")
            continue
        profile = next(
            (candidate for candidate in profiles if _profile_matches_local_listing(candidate, title)),
            None,
        )
        if profile is None:
            failures.append(f"{title}:profile_title_mismatch")
            continue
        categories = [
            str(category)
            for category in profile.get("services", [])
            if category
        ]
        rows.append({
            "cbsa_code": cbsa_code,
            "niche_normalized": niche_normalized,
            "keyword": keyword,
            "listing_rank": rank,
            "business_name": title,
            "cid": item.get("cid"),
            "place_id": item.get("place_id"),
            "review_retrieval_mode": "title",
            "source_query": keyword,
            "dataforseo_location_code": location_code,
            "result_type": "local_pack",
            "exact_match_name": False,
            "review_count": item.get("rating_count"),
            "rating": item.get("rating"),
            "gbp_completeness": compute_gbp_completeness(profile),
            "photo_count": profile.get("photo_count"),
            "has_recent_post": profile.get("has_recent_post"),
            "categories": categories,
            "source": "dataforseo",
            "snapshot_date": snapshot_date,
        })
    return GbpProfileCollectionResult(rows=rows, failures=failures)


def classify_keyword_volume_failure(response: Any) -> str:
    """Map a DataForSEO keyword-volume response error to a benchmark failure bucket."""
    error_text = str(getattr(response, "error", "") or "").lower()
    if "invalid field" in error_text and "location_code" in error_text:
        return "invalid_keyword_volume_code"
    if "task in queue" in error_text or "queue timeout" in error_text:
        return "task_queue_timeout"
    return "keyword_volume_empty"


async def collect_keyword_volume(
    dfs: DataForSEOClient,
    keywords: list[str],
    location_codes: list[int],
) -> VolumeCollectionResult:
    """Collect keyword volume across candidate location codes."""
    volume_by_kw: dict[str, dict[str, Any]] = {}
    valid_location_codes: list[int] = []
    failures: list[VolumeAttemptFailure] = []

    for code in location_codes:
        vol_resp = await dfs.keyword_volume(keywords=keywords, location_code=code)
        if vol_resp.status != "ok":
            failures.append(
                VolumeAttemptFailure(
                    location_code=code,
                    reason=classify_keyword_volume_failure(vol_resp),
                    detail=vol_resp.error or "keyword_volume error",
                )
            )
            continue

        vol_items = vol_resp.data if isinstance(vol_resp.data, list) else [vol_resp.data]
        code_had_usable_rows = False
        for row in vol_items:
            if not isinstance(row, dict):
                continue
            kw_lower = (row.get("keyword") or "").lower()
            if not kw_lower:
                continue
            sv, cpc = row.get("search_volume"), row.get("cpc")
            if sv is None and cpc is None:
                continue

            code_had_usable_rows = True
            existing = volume_by_kw.get(kw_lower, {})
            existing_sv = existing.get("search_volume") or 0
            existing_cpc = existing.get("cpc")
            new_sv = max(sv or 0, existing_sv) if sv is not None else existing_sv
            new_cpc = max(cpc or 0, existing_cpc or 0) if (cpc or existing_cpc) else None
            volume_by_kw[kw_lower] = {"search_volume": new_sv or None, "cpc": new_cpc}

        if code_had_usable_rows:
            valid_location_codes.append(code)
        else:
            failures.append(
                VolumeAttemptFailure(
                    location_code=code,
                    reason="keyword_volume_empty",
                    detail="no usable keyword volume rows",
                )
            )

    return VolumeCollectionResult(
        volume_by_kw=volume_by_kw,
        valid_location_codes=valid_location_codes,
        failures=failures,
    )


# -------------------------------------------------------------------
# PostgREST upsert
# -------------------------------------------------------------------
def upsert_facts(rows: list[dict]) -> tuple[int, str]:
    if not rows:
        return 200, ""
    url = (
        f"{SUPABASE_URL}/rest/v1/seo_facts"
        f"?on_conflict=niche_normalized,cbsa_code,keyword,snapshot_date"
    )
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    body = json.dumps(rows).encode("utf-8")
    req = urlreq.Request(url, data=body, headers=headers, method="POST")
    try:
        with urlreq.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urlerror.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except (urlerror.URLError, TimeoutError, OSError) as e:
        return 599, str(e)[:500]


def upsert_evidence_artifacts(rows: list[dict]) -> tuple[int, str]:
    if not rows:
        return 200, ""
    url = (
        f"{SUPABASE_URL}/rest/v1/seo_evidence_artifacts"
        f"?on_conflict=provider,endpoint_path,request_hash"
    )
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }
    body = json.dumps(rows).encode("utf-8")
    req = urlreq.Request(url, data=body, headers=headers, method="POST")
    try:
        with urlreq.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urlerror.HTTPError as e:
        return e.code, e.read().decode()[:500]


def upsert_local_pack_listing_facts(rows: list[dict]) -> tuple[int, str]:
    if not rows:
        return 200, ""
    url = (
        f"{SUPABASE_URL}/rest/v1/local_pack_listing_facts"
        f"?on_conflict=cbsa_code,niche_normalized,keyword,listing_rank,snapshot_date"
    )
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    body = json.dumps(rows).encode("utf-8")
    req = urlreq.Request(url, data=body, headers=headers, method="POST")
    try:
        with urlreq.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urlerror.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except (urlerror.URLError, TimeoutError, OSError) as e:
        return 599, str(e)[:500]


def evidence_artifacts_from_dfs_cost_log(
    dfs: DataForSEOClient,
    *,
    start_index: int = 0,
    collection_context_id: str | None = None,
    niche: str | None = None,
    location_codes: list[int] | None = None,
    keywords: list[str] | None = None,
    serp_keywords: list[str] | None = None,
    local_pack_items: list[dict[str, Any]] | None = None,
    organic_targets: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    cost_records = (getattr(dfs, "cost_log", []) or [])[start_index:]
    if collection_context_id is not None:
        filtered_records = [
            record
            for record in cost_records
            if _record_field(record, "collection_context_id") == collection_context_id
        ]
        return build_seo_evidence_artifact_rows_from_cost_records(filtered_records)

    filtered_records = [
        record
        for record in cost_records
        if _cost_record_matches_pair(
            record,
            niche=niche,
            location_codes=location_codes,
            keywords=keywords,
            serp_keywords=serp_keywords,
            local_pack_items=local_pack_items,
            organic_targets=organic_targets,
        )
    ]
    return build_seo_evidence_artifact_rows_from_cost_records(filtered_records)


def _cost_record_matches_pair(
    record: Any,
    *,
    niche: str | None,
    location_codes: list[int] | None,
    keywords: list[str] | None,
    serp_keywords: list[str] | None,
    local_pack_items: list[dict[str, Any]] | None,
    organic_targets: list[dict[str, Any]] | None,
) -> bool:
    endpoint = _record_field(record, "endpoint")
    family = evidence_family_from_endpoint(str(endpoint or ""))
    if family is None:
        return False

    params = _record_field(record, "parameters")
    params = params if isinstance(params, dict) else {}
    location_set = {
        parsed
        for code in location_codes or []
        if (parsed := _int_param(code)) is not None
    }
    keyword_set = {_norm_text(keyword) for keyword in keywords or [] if _norm_text(keyword)}
    serp_keyword_set = {
        _norm_text(keyword) for keyword in serp_keywords or [] if _norm_text(keyword)
    }
    local_identifiers = _local_identifier_set(local_pack_items or [])
    organic_domains = {
        _norm_text(target.get("domain"))
        for target in organic_targets or []
        if _norm_text(target.get("domain"))
    }
    organic_urls = {
        _norm_text(target.get("url"))
        for target in organic_targets or []
        if _norm_text(target.get("url"))
    }

    location = _int_param(params.get("location_code"))
    if family == "keyword_volume":
        return (
            location in location_set
            and bool(keyword_set)
            and bool(keyword_set.intersection(_param_keywords(params)))
        )
    if family in {"serp", "maps"}:
        return (
            location in location_set
            and (
                not serp_keyword_set
                or _norm_text(params.get("keyword")) in serp_keyword_set
            )
        )
    if family == "reviews":
        if location not in location_set:
            return False
        candidates = {
            _norm_text(params.get("cid")),
            _norm_text(params.get("place_id")),
            _norm_text(params.get("keyword")),
        }
        return bool(local_identifiers.intersection(candidates))
    if family == "backlinks":
        return _norm_text(params.get("target")) in organic_domains
    if family == "lighthouse":
        return _norm_text(params.get("url")) in organic_urls
    if family == "keyword_overview":
        return _norm_text(params.get("keyword")) == _norm_text(niche)
    return False


def _record_field(record: Any, key: str) -> Any:
    if isinstance(record, dict):
        return record.get(key)
    return getattr(record, key, None)


def _dfs_capture_context(dfs: DataForSEOClient, context_id: str) -> Any:
    tracker = getattr(dfs, "cost_tracker", None)
    capture_context = getattr(tracker, "capture_context", None)
    if callable(capture_context):
        return capture_context(context_id)
    return nullcontext()


def _norm_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _int_param(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _param_keywords(params: dict[str, Any]) -> set[str]:
    raw_keywords = params.get("keywords")
    if isinstance(raw_keywords, list):
        return {_norm_text(keyword) for keyword in raw_keywords if _norm_text(keyword)}
    keyword = _norm_text(params.get("keyword"))
    return {keyword} if keyword else set()


def _local_identifier_set(items: list[dict[str, Any]]) -> set[str]:
    identifiers: set[str] = set()
    for item in items[:3]:
        for key in ("cid", "place_id", "title"):
            value = _norm_text(item.get(key))
            if value:
                identifiers.add(value)
    return identifiers


def _business_name_token_set(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) > 1 and token not in {"the", "and", "llc", "inc", "co", "company"}
    }


def _profile_matches_local_listing(profile: dict[str, Any], title: str) -> bool:
    profile_title = profile.get("title") or profile.get("business_name") or profile.get("name")
    listing_tokens = _business_name_token_set(title)
    profile_tokens = _business_name_token_set(profile_title)
    if not listing_tokens or not profile_tokens:
        return False
    overlap = listing_tokens & profile_tokens
    return len(overlap) >= min(2, len(listing_tokens), len(profile_tokens))


# -------------------------------------------------------------------
# Per-niche keyword expansion (cached)
# -------------------------------------------------------------------
class NicheExpansionCache:
    def __init__(self, llm: LLMClient, dfs: DataForSEOClient) -> None:
        self.llm = llm
        self.dfs = dfs
        self._cache: dict[str, dict] = {}
        self._inflight: dict[str, asyncio.Task[dict]] = {}
        self._lock = asyncio.Lock()

    async def get(self, niche: str) -> dict:
        async with self._lock:
            if niche in self._cache:
                return self._cache[niche]
            task = self._inflight.get(niche)
            if task is None:
                task = asyncio.create_task(self._expand(niche))
                self._inflight[niche] = task

        try:
            expanded = await task
        except Exception:
            async with self._lock:
                if self._inflight.get(niche) is task:
                    self._inflight.pop(niche, None)
            raise

        async with self._lock:
            self._cache[niche] = expanded
            if self._inflight.get(niche) is task:
                self._inflight.pop(niche, None)
        return expanded

    async def _expand(self, niche: str) -> dict:
        log.info(f"  [expansion] niche={niche!r}")
        return await expand_keywords(
            niche=niche,
            llm_client=self.llm,
            dataforseo_client=self.dfs,
            suggestions_limit=20,
        )


# -------------------------------------------------------------------
# Per (niche, metro) scoring
# -------------------------------------------------------------------
async def score_one(
    niche: str,
    metro: dict,
    expansion_cache: NicheExpansionCache,
    dfs: DataForSEOClient,
    stats: RunStats,
    *,
    preflight_only: bool = False,
    collect_organic: bool = False,
    collect_review_velocity_flag: bool = False,
    collect_gbp_profile_flag: bool = False,
    organic_telemetry_limit: int = 5,
    review_depth: int = 10,
) -> int:
    """Score one (niche, metro) pair → returns count of facts inserted."""
    cbsa = metro["cbsa_code"]
    name = metro["cbsa_name"]
    log.info(f"[start] {niche!r} × {name} ({cbsa})")
    stats.reports_attempted += 1
    pair_context_id = f"benchmark:{niche.lower()}:{cbsa}:{uuid4()}"

    with _dfs_capture_context(dfs, pair_context_id):
        try:
            expansion = await expansion_cache.get(niche)
            actionable = [
                kw for kw in expansion["expanded_keywords"]
                if kw["intent"] in ("transactional", "commercial") and kw.get("actionable")
            ]
            if not actionable:
                log.warning(f"  no actionable keywords for {niche!r}")
                stats.reports_failed += 1
                stats.record_failure(niche, cbsa, "no_actionable_keywords")
                return 0

            # Resolve all DFS location codes for this metro (city + fallback)
            loc_codes = (
                metro.get("keyword_volume_location_codes")
                or metro.get("dataforseo_location_codes")
                or []
            )
            if not loc_codes:
                log.info(f"  no DFS codes for {cbsa} (no state fallback); skipping")
                stats.reports_failed += 1
                stats.record_failure(niche, cbsa, "no_native_dfs_code")
                return 0

            # 1) Keyword volume — try each loc_code, take max volume per keyword
            # (multi-code metros: LA has [1013962, 1013849, 1013549] = LA, Long Beach,
            # Anaheim. Many keywords have data in only one of these. Max captures
            # the principal-city signal.)
            kw_strs = [k["keyword"] for k in actionable[:50]]
            volume_result = await collect_keyword_volume(dfs, kw_strs, loc_codes)
            for failure in volume_result.failures:
                stats.record_failure(
                    niche,
                    cbsa,
                    failure.reason,
                    f"location_code={failure.location_code}; {failure.detail}",
                )
            volume_by_kw = volume_result.volume_by_kw
            if volume_result.valid_location_codes:
                metro["keyword_volume_location_codes"] = volume_result.valid_location_codes

            if preflight_only:
                if volume_by_kw:
                    stats.reports_succeeded += 1
                    log.info(
                        "[preflight] %r × %s: %s keywords, valid volume codes=%s",
                        niche,
                        name,
                        len(volume_by_kw),
                        volume_result.valid_location_codes,
                    )
                    return 0
                stats.reports_failed += 1
                if not volume_result.failures:
                    stats.record_failure(niche, cbsa, "keyword_volume_empty", "no usable rows")
                return 0

            # 2) SERP — query the highest-population code (loc_codes[0] is the
            # principal city per seed ordering; it gives the cleanest SERP shape).
            loc_code_for_serp = (metro.get("dataforseo_location_codes") or loc_codes)[0]
            head_kws = [k for k in actionable if k["tier"] == 1][:2] or actionable[:2]
            serp_features_by_kw: dict[str, dict] = {}
            for k in head_kws:
                serp_resp = await dfs.serp_organic(
                    keyword=k["keyword"], location_code=loc_code_for_serp, depth=20,
                )
                if serp_resp.status == "ok" and serp_resp.data:
                    serp_features_by_kw[k["keyword"]] = parse_serp_items(serp_resp.data)

            # Use head SERP features as the "metro-level" SERP signal for all keywords
            # (actual SERP per long-tail keyword would 50x cost; head signal is the
            # competitive landscape proxy for benchmarking)
            head_feature_keyword = next(
                iter(serp_features_by_kw.keys()),
                head_kws[0]["keyword"] if head_kws else niche,
            )
            head_features = dict(
                serp_features_by_kw.get(head_feature_keyword, {})
            )
            local_pack_keyword, local_pack_features = first_local_pack_features(
                serp_features_by_kw,
                fallback_keyword=head_feature_keyword,
                fallback_features=head_features,
            )
            if collect_review_velocity_flag and local_pack_features.get("top_local_pack_items"):
                velocity = await collect_top3_review_velocity(
                    dfs,
                    list(local_pack_features.get("top_local_pack_items") or []),
                    location_code=loc_code_for_serp,
                    depth=review_depth,
                )
                if velocity is not None:
                    propagate_head_feature(
                        serp_features_by_kw,
                        head_features,
                        "top3_review_velocity_avg",
                        velocity,
                    )

            gbp_profile_rows: list[dict[str, Any]] = []
            snapshot = date.today().isoformat()
            service_key = persistence_niche_key(niche)
            if collect_gbp_profile_flag and local_pack_features.get("top_local_pack_items"):
                gbp_result = await collect_top3_gbp_profile_facts(
                    dfs,
                    list(local_pack_features.get("top_local_pack_items") or []),
                    cbsa_code=cbsa,
                    niche_normalized=service_key,
                    keyword=local_pack_keyword,
                    location_code=loc_code_for_serp,
                    snapshot_date=snapshot,
                )
                gbp_profile_rows = gbp_result.rows
                for failure in gbp_result.failures:
                    stats.record_failure(niche, cbsa, "gbp_profile_partial", failure)

            organic_telemetry: dict[str, Any] = {}
            if collect_organic:
                telemetry = await collect_organic_telemetry(
                    dfs,
                    list(head_features.get("organic_targets") or []),
                    limit=organic_telemetry_limit,
                )
                organic_telemetry = telemetry.fields
                for failure in telemetry.failures:
                    stats.record_failure(niche, cbsa, "organic_telemetry_partial", failure)

            # 3) Build seo_facts rows
            rows = []
            for kw in actionable:
                v = volume_by_kw.get(kw["keyword"].lower(), {})
                sv = v.get("search_volume")
                cpc = v.get("cpc")
                if sv is None and cpc is None:
                    # No volume data — skip (DFS returned nothing for this kw)
                    continue
                row_features = serp_features_by_kw.get(kw["keyword"], head_features)
                row = {
                    "niche_keyword": niche,
                    "niche_normalized": service_key,
                    "cbsa_code": cbsa,
                    "keyword": kw["keyword"],
                    "keyword_tier": kw["tier"],
                    "intent": kw["intent"],
                    "search_volume_monthly": sv,
                    "cpc_usd": float(cpc) if cpc is not None else None,
                    "aio_present": row_features.get("aio_present"),
                    "local_pack_present": row_features.get("local_pack_present"),
                    "local_pack_position": row_features.get("local_pack_position"),
                    "top3_review_count_min": row_features.get("top3_review_count_min"),
                    "top3_review_count_avg": row_features.get("top3_review_count_avg"),
                    "top3_review_velocity_avg": row_features.get("top3_review_velocity_avg"),
                    "top3_rating_avg": row_features.get("top3_rating_avg"),
                    "aggregator_count_top10": row_features.get("aggregator_count_top10"),
                    "local_biz_count_top10": row_features.get("local_biz_count_top10"),
                    "featured_snippet_present": row_features.get("featured_snippet_present"),
                    "paa_count": row_features.get("paa_count"),
                    "ads_present": row_features.get("ads_present"),
                    "lsa_present": row_features.get("lsa_present"),
                    "snapshot_date": snapshot,
                    "source": "orchestrator",
                }
                if organic_telemetry:
                    row.update(organic_telemetry)
                rows.append(row)

            # 4) Persist
            if rows:
                status, body = upsert_facts(rows)
                if status >= 300:
                    log.error(f"  upsert failed: {status} {body[:200]}")
                    stats.reports_failed += 1
                    stats.record_failure(niche, cbsa, "upsert_failed", f"status={status}")
                    return 0
                stats.facts_inserted += len(rows)
                if gbp_profile_rows:
                    try:
                        local_status, local_body = upsert_local_pack_listing_facts(
                            gbp_profile_rows
                        )
                    except Exception as exc:  # noqa: BLE001
                        log.warning(
                            "  local_pack_listing_facts upsert failed (non-fatal): %s",
                            exc,
                        )
                        stats.record_failure(
                            niche,
                            cbsa,
                            "gbp_profile_upsert_failed_non_fatal",
                            type(exc).__name__,
                        )
                    else:
                        if local_status >= 300:
                            log.warning(
                                "  local_pack_listing_facts upsert failed (non-fatal): %s %s",
                                local_status,
                                local_body[:200],
                            )
                            stats.record_failure(
                                niche,
                                cbsa,
                                "gbp_profile_upsert_failed_non_fatal",
                                f"status={local_status}",
                            )
                stats.reports_succeeded += 1
                try:
                    evidence_artifact_rows = evidence_artifacts_from_dfs_cost_log(
                        dfs,
                        collection_context_id=pair_context_id,
                    )
                    if evidence_artifact_rows:
                        evidence_status, evidence_body = upsert_evidence_artifacts(
                            evidence_artifact_rows
                        )
                        if evidence_status >= 300:
                            log.warning(
                                "  evidence artifact upsert failed (non-fatal): %s %s",
                                evidence_status,
                                evidence_body[:200],
                            )
                            stats.record_failure(
                                niche,
                                cbsa,
                                "evidence_upsert_failed_non_fatal",
                                f"status={evidence_status}",
                            )
                except Exception as exc:
                    log.warning(
                        "  evidence artifact upsert failed (non-fatal): %s",
                        exc,
                    )
                    stats.record_failure(
                        niche,
                        cbsa,
                        "evidence_upsert_failed_non_fatal",
                        type(exc).__name__,
                    )
                log.info(f"[done] {niche!r} × {name}: {len(rows)} facts")
                return len(rows)

            stats.reports_failed += 1
            stats.record_failure(niche, cbsa, "keyword_volume_empty", "no rows to persist")
            return 0

        except Exception as e:
            log.exception(f"failure on {niche} × {cbsa}")
            stats.reports_failed += 1
            stats.record_failure(niche, cbsa, type(e).__name__, str(e))
            return 0
# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
async def main():
    args = parse_args()
    validate_expected_project_ref(args.expected_project_ref)

    # Sampling plan lives next to this script
    metros_path = Path(__file__).parent / "metros_sampled.json"
    if not metros_path.exists():
        log.error(f"sampling plan missing: {metros_path}")
        sys.exit(1)

    full_sample = load_full_sample(metros_path)
    if args.cbsa_code:
        selected_metros = fetch_metros_by_cbsa(
            args.cbsa_code,
            include_low_signal=args.include_low_signal,
        )
        validate_population_classes(args.population_class, selected_metros)
    else:
        validate_population_classes(args.population_class, full_sample)
        selected_metros = select_metros(
            full_sample,
            args.sample_mode,
            include_low_signal=args.include_low_signal,
        )
    if args.population_class:
        allowed_classes = set(args.population_class)
        selected_metros = [
            metro
            for metro in selected_metros
            if metro.get("population_class") in allowed_classes
        ]
    niches = select_niches(args.niche)
    pairs = build_pairs(niches, selected_metros)
    if args.limit_pairs is not None:
        pairs = pairs[:args.limit_pairs]

    if not pairs:
        fail_cli("filters produced zero (niche, metro) pairs")
    validate_paid_targets([metro for _niche, metro in pairs], require_dfs=args.require_dfs)

    if not ((SUPABASE_KEY or args.preflight_only) and DFS_LOGIN and DFS_PASS and ANTHROPIC_KEY):
        log.error("missing env vars — check .env")
        sys.exit(1)
    if not args.preflight_only:
        validate_v2_persistence(
            pairs,
            require_v2_persistence=args.require_v2_persistence,
        )
    if args.preflight_only and (
        args.collect_organic_telemetry
        or args.collect_review_velocity
        or args.collect_gbp_profile
    ):
        log.info(
            "preflight-only skips organic telemetry, review velocity, and GBP profile collection"
        )

    log.info(
        "%s sample: %s niches × %s paid-eligible metros = %s reports%s%s%s%s",
        args.sample_mode,
        len(niches),
        len(selected_metros),
        len(pairs),
        " (preflight only)" if args.preflight_only else "",
        " + organic telemetry" if args.collect_organic_telemetry and not args.preflight_only else "",
        " + review velocity" if args.collect_review_velocity and not args.preflight_only else "",
        " + GBP profile" if args.collect_gbp_profile and not args.preflight_only else "",
    )

    # Disable persistent cache: it reads NEXT_PUBLIC_SUPABASE_URL (prod) but the
    # service key in .env is staging — they don't match and produce 401 spam.
    # In-memory cache is sufficient for a single pilot run.
    dfs = DataForSEOClient(login=DFS_LOGIN, password=DFS_PASS, persistent_cache=False)
    llm = LLMClient(api_key=ANTHROPIC_KEY)
    cache = NicheExpansionCache(llm=llm, dfs=dfs)
    stats = RunStats()

    sem = asyncio.Semaphore(CONCURRENCY)
    started = time.time()

    async def runner(pair):
        async with sem:
            return await score_one(
                pair[0],
                pair[1],
                cache,
                dfs,
                stats,
                preflight_only=args.preflight_only,
                collect_organic=args.collect_organic_telemetry and not args.preflight_only,
                collect_review_velocity_flag=(
                    args.collect_review_velocity and not args.preflight_only
                ),
                collect_gbp_profile_flag=(
                    args.collect_gbp_profile and not args.preflight_only
                ),
                organic_telemetry_limit=args.organic_telemetry_limit,
                review_depth=args.review_depth,
            )

    await asyncio.gather(*(runner(p) for p in pairs), return_exceptions=False)

    elapsed = time.time() - started
    log.info(f"DONE in {elapsed:.1f}s — {stats.summary()}")
    if stats.failure_reasons:
        log.warning("failure reasons: %s", stats.failure_reasons)
    if stats.failures:
        log.warning(f"first 5 failures: {stats.failures[:5]}")


if __name__ == "__main__":
    asyncio.run(main())
