"""1-pair smoke test before running the pilot.

Runs ONE (niche, metro) combo end-to-end:
  - LLM keyword expansion
  - DataForSEO keyword_volume
  - DataForSEO SERP
  - seo_facts upsert

Cost: ~$0.12. Validates the full pipeline before we spend $25 on the pilot.

Usage:
  cd whidby
  python -m scripts.benchmarks.smoke_test
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from urllib import request as urlreq

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmarks.run_pilot import (  # noqa: E402
    NicheExpansionCache, RunStats, score_one,
)
from src.clients.dataforseo import DataForSEOClient  # noqa: E402
from src.clients.llm.client import LLMClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("smoke")

SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL", "https://wuybidpvqhhgkukpyyhq.supabase.co"
)
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]


async def main():
    if not (SUPABASE_KEY and os.environ.get("DATAFORSEO_LOGIN")
            and os.environ.get("DATAFORSEO_PASSWORD") and os.environ.get("ANTHROPIC_API_KEY")):
        log.error("missing env vars")
        sys.exit(1)

    # Fixed test pair: concrete contractor × Phoenix (DFS-coded, well-known)
    niche = "concrete contractor"
    metro = {
        "cbsa_code": "38060",
        "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
        "state": "AZ",
        "population": 4941206,
        "population_class": "metro_1m_5m",
        "dataforseo_location_codes": [1012873],
    }

    dfs = DataForSEOClient(
        login=os.environ["DATAFORSEO_LOGIN"],
        password=os.environ["DATAFORSEO_PASSWORD"],
    )
    llm = LLMClient(api_key=os.environ["ANTHROPIC_API_KEY"])
    cache = NicheExpansionCache(llm=llm, dfs=dfs)
    stats = RunStats()

    log.info(f"smoke test: {niche} × {metro['cbsa_name']}")
    inserted = await score_one(niche, metro, cache, dfs, stats)
    log.info(f"inserted {inserted} facts")
    log.info(f"DFS cost so far: ${dfs.total_cost:.4f}")
    log.info(stats.summary())
    if stats.failures:
        log.error(f"failures: {stats.failures}")
        sys.exit(1)

    # Verify by reading from Supabase
    url = (
        f"{SUPABASE_URL}/rest/v1/seo_facts"
        f"?niche_normalized=eq.concrete%20contractor"
        f"&cbsa_code=eq.38060"
        f"&select=keyword,intent,search_volume_monthly,cpc_usd,aio_present,local_pack_present,aggregator_count_top10"
    )
    req = urlreq.Request(url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    with urlreq.urlopen(req, timeout=30) as r:
        rows = json.loads(r.read())
    log.info(f"Supabase has {len(rows)} seo_facts rows for this pair")
    if rows:
        log.info(f"sample row: {rows[0]}")


if __name__ == "__main__":
    asyncio.run(main())
