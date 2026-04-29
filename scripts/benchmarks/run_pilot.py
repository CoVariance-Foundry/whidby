"""Dedicated benchmark runner — pilot phase (200 reports).

Populates `seo_facts` with keyword-grain market observations across a
stratified sample of (niche, metro) pairs. Skips V1.1 scoring entirely —
no writes to reports/metro_signals/metro_scores.

Pilot scope: 10 niches × 20 metros = 200 reports.
Per (niche, metro):
  1. Keyword expansion (cached per niche — one LLM call per niche total)
  2. DataForSEO keyword_volume (batched, one task per metro)
  3. DataForSEO SERP per top 2 keywords (extract AIO, local pack, aggregator,
     local biz, featured snippet, PAA, ads, LSA flags)
  4. (Pilot skips GBP + reviews — added in full run)
  5. Insert seo_facts rows via Supabase PostgREST

Usage:
  cd whidby
  python -m scripts.benchmarks.run_pilot

Reads credentials from .env in repo root.
"""
from __future__ import annotations

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("benchmark_runner")


# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
# Benchmark runs always go to STAGING. The .env's NEXT_PUBLIC_SUPABASE_URL
# points to prod; explicit STAGING_SUPABASE_URL overrides for benchmarking.
SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",  # staging
)
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
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

    def summary(self) -> str:
        return (
            f"reports: {self.reports_succeeded}/{self.reports_attempted} succeeded, "
            f"{self.reports_failed} failed; facts inserted: {self.facts_inserted}"
        )


# -------------------------------------------------------------------
# Sampling plan loader
# -------------------------------------------------------------------
def load_sample(metros_path: Path) -> list[dict[str, Any]]:
    """Pick the pilot's 20 metros from the larger sample plan.

    Also builds a state→best-DFS-code index for the state-borrow fallback
    used when a metro has no native DFS codes.
    """
    full = json.loads(metros_path.read_text())
    by_class: dict[str, list[dict]] = {}
    for m in full:
        by_class.setdefault(m["population_class"], []).append(m)

    pilot: list[dict] = []
    for cls, n in PILOT_METROS_PER_CLASS.items():
        pool = by_class.get(cls, [])
        with_dfs = [m for m in pool if m.get("dataforseo_location_codes")]
        without_dfs = [m for m in pool if not m.get("dataforseo_location_codes")]
        ordered = with_dfs + without_dfs
        pilot.extend(ordered[:n])

    # Build state→DFS code map for state-level fallback (largest metro in state wins)
    state_dfs: dict[str, list[int]] = {}
    for m in sorted(full, key=lambda x: -(x.get("population") or 0)):
        codes = m.get("dataforseo_location_codes") or []
        if codes and m["state"] not in state_dfs:
            state_dfs[m["state"]] = codes

    # Stitch state fallback codes onto pilot metros that lack native codes
    for m in pilot:
        if not m.get("dataforseo_location_codes"):
            fallback = state_dfs.get(m["state"], [])
            if fallback:
                m["dataforseo_location_codes"] = fallback
                m["_dfs_source"] = "state_borrow"
            else:
                m["_dfs_source"] = "none"
        else:
            m["_dfs_source"] = "native"

    return pilot


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
            if org_position <= 10:
                domain = extract_domain(item.get("url", ""))
                if domain in KNOWN_AGGREGATORS:
                    flags["aggregator_count_top10"] += 1
                else:
                    flags["local_biz_count_top10"] += 1
    return flags


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
        self._lock = asyncio.Lock()

    async def get(self, niche: str) -> dict:
        async with self._lock:
            if niche in self._cache:
                return self._cache[niche]
        # outside the lock — expand can be slow
        log.info(f"  [expansion] niche={niche!r}")
        expanded = await expand_keywords(
            niche=niche,
            llm_client=self.llm,
            dataforseo_client=self.dfs,
            suggestions_limit=20,
        )
        async with self._lock:
            self._cache[niche] = expanded
        return expanded


# -------------------------------------------------------------------
# Per (niche, metro) scoring
# -------------------------------------------------------------------
async def score_one(
    niche: str,
    metro: dict,
    expansion_cache: NicheExpansionCache,
    dfs: DataForSEOClient,
    stats: RunStats,
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
            return 0

        # Resolve all DFS location codes for this metro (city + fallback)
        loc_codes = metro.get("dataforseo_location_codes") or []
        if not loc_codes:
            log.info(f"  no DFS codes for {cbsa} (no state fallback); skipping")
            stats.reports_failed += 1
            return 0

        # 1) Keyword volume — try each loc_code, take max volume per keyword
        # (multi-code metros: LA has [1013962, 1013849, 1013549] = LA, Long Beach,
        # Anaheim. Many keywords have data in only one of these. Max captures
        # the principal-city signal.)
        kw_strs = [k["keyword"] for k in actionable[:50]]
        volume_by_kw: dict[str, dict] = {}
        for code in loc_codes:
            vol_resp = await dfs.keyword_volume(keywords=kw_strs, location_code=code)
            if vol_resp.status != "ok" or not vol_resp.data:
                continue
            vol_items = vol_resp.data if isinstance(vol_resp.data, list) else [vol_resp.data]
            for r in vol_items:
                if not isinstance(r, dict):
                    continue
                kw_lower = (r.get("keyword") or "").lower()
                sv, cpc = r.get("search_volume"), r.get("cpc")
                existing = volume_by_kw.get(kw_lower, {})
                existing_sv = existing.get("search_volume") or 0
                existing_cpc = existing.get("cpc")
                # Take max search volume; CPC: take whichever is non-null,
                # prefer the higher one (more competitive signal).
                new_sv = max(sv or 0, existing_sv) if sv is not None else existing_sv
                new_cpc = max(cpc or 0, existing_cpc or 0) if (cpc or existing_cpc) else None
                volume_by_kw[kw_lower] = {"search_volume": new_sv or None, "cpc": new_cpc}

        # 2) SERP — query the highest-population code (loc_codes[0] is the
        # principal city per seed ordering; it gives the cleanest SERP shape).
        loc_code_for_serp = loc_codes[0]
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
        head_features = next(iter(serp_features_by_kw.values()), {}) if serp_features_by_kw else {}

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
            rows.append({
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
                "aggregator_count_top10": row_features.get("aggregator_count_top10"),
                "local_biz_count_top10": row_features.get("local_biz_count_top10"),
                "featured_snippet_present": row_features.get("featured_snippet_present"),
                "paa_count": row_features.get("paa_count"),
                "ads_present": row_features.get("ads_present"),
                "lsa_present": row_features.get("lsa_present"),
                "snapshot_date": snapshot,
                "source": "orchestrator",
            })

        # 4) Persist
        if rows:
            status, body = upsert_facts(rows)
            if status >= 300:
                log.error(f"  upsert failed: {status} {body[:200]}")
                stats.reports_failed += 1
                stats.failures.append(f"{niche}@{cbsa}: upsert {status}")
                return 0
            stats.facts_inserted += len(rows)
            stats.reports_succeeded += 1
            log.info(f"[done] {niche!r} × {name}: {len(rows)} facts")
            return len(rows)

        stats.reports_failed += 1
        return 0

    except Exception as e:
        log.exception(f"failure on {niche} × {cbsa}")
        stats.reports_failed += 1
        stats.failures.append(f"{niche}@{cbsa}: {type(e).__name__}: {e}")
        return 0


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
async def main():
    if not (SUPABASE_KEY and DFS_LOGIN and DFS_PASS and ANTHROPIC_KEY):
        log.error("missing env vars — check .env")
        sys.exit(1)

    # Sampling plan lives next to this script
    metros_path = Path(__file__).parent / "metros_sampled.json"
    if not metros_path.exists():
        log.error(f"sampling plan missing: {metros_path}")
        sys.exit(1)

    pilot_metros = load_sample(metros_path)
    pairs = [(n, m) for n in PILOT_NICHES for m in pilot_metros]
    log.info(f"pilot: {len(PILOT_NICHES)} niches × {len(pilot_metros)} metros = {len(pairs)} reports")

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
            return await score_one(pair[0], pair[1], cache, dfs, stats)

    await asyncio.gather(*(runner(p) for p in pairs), return_exceptions=False)

    elapsed = time.time() - started
    log.info(f"DONE in {elapsed:.1f}s — {stats.summary()}")
    if stats.failures:
        log.warning(f"first 5 failures: {stats.failures[:5]}")


if __name__ == "__main__":
    asyncio.run(main())
