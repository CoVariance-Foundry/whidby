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
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlreq

# Repo root + path injection so we can import src.* modules
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.clients.dataforseo import DataForSEOClient  # noqa: E402
from src.clients.llm.client import LLMClient  # noqa: E402
from src.pipeline.keyword_expansion import expand_keywords  # noqa: E402
from src.pipeline.review_velocity import compute_reviews_per_month  # noqa: E402

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


BENCHMARK_PAID_POPULATION_CLASSES = {
    "mega_5m_plus",
    "metro_1m_5m",
    "large_300k_1m",
    "medium_100_300k",
}
LOW_SIGNAL_POPULATION_CLASSES = {"small_50_100k", "micro_under_50k"}


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
    return parser.parse_args()


def fail_cli(message: str) -> None:
    print(f"run_pilot.py: error: {message}", file=sys.stderr)
    sys.exit(2)


def select_niches(requested: list[str] | None) -> list[str]:
    if not requested:
        return PILOT_NICHES

    for niche in requested:
        if niche not in PILOT_NICHES:
            allowed = ", ".join(PILOT_NICHES)
            fail_cli(f"unknown niche {niche!r}; expected one of: {allowed}")

    return requested


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
            flags["local_pack_position"] = item.get("rank_absolute") or flags["local_pack_position"]
            for sub in (item.get("items") or [])[:3]:
                flags["top_local_pack_items"].append({
                    "title": sub.get("title"),
                    "rating": (sub.get("rating") or {}).get("value"),
                    "rating_count": (sub.get("rating") or {}).get("votes_count"),
                    "place_id": sub.get("place_id"),
                    "cid": sub.get("cid"),
                })
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
    for row in _walk_dicts(data):
        for key in ("rank", "domain_rank", "domain_from_rank", "page_from_rank"):
            value = _numeric(row.get(key))
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
    organic_telemetry_limit: int = 5,
    review_depth: int = 10,
) -> int:
    """Score one (niche, metro) pair → returns count of facts inserted."""
    cbsa = metro["cbsa_code"]
    name = metro["cbsa_name"]
    log.info(f"[start] {niche!r} × {name} ({cbsa})")
    stats.reports_attempted += 1

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
        head_features = dict(next(iter(serp_features_by_kw.values()), {})) if serp_features_by_kw else {}
        if collect_review_velocity_flag and head_features.get("top_local_pack_items"):
            velocity = await collect_top3_review_velocity(
                dfs,
                list(head_features.get("top_local_pack_items") or []),
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
        snapshot = date.today().isoformat()
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
                "niche_normalized": niche.lower(),
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
            stats.reports_succeeded += 1
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

    # Sampling plan lives next to this script
    metros_path = Path(__file__).parent / "metros_sampled.json"
    if not metros_path.exists():
        log.error(f"sampling plan missing: {metros_path}")
        sys.exit(1)

    full_sample = load_full_sample(metros_path)
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

    if not ((SUPABASE_KEY or args.preflight_only) and DFS_LOGIN and DFS_PASS and ANTHROPIC_KEY):
        log.error("missing env vars — check .env")
        sys.exit(1)
    if args.preflight_only and (args.collect_organic_telemetry or args.collect_review_velocity):
        log.info("preflight-only skips organic telemetry and review velocity collection")

    log.info(
        "%s sample: %s niches × %s paid-eligible metros = %s reports%s%s%s",
        args.sample_mode,
        len(niches),
        len(selected_metros),
        len(pairs),
        " (preflight only)" if args.preflight_only else "",
        " + organic telemetry" if args.collect_organic_telemetry and not args.preflight_only else "",
        " + review velocity" if args.collect_review_velocity and not args.preflight_only else "",
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
