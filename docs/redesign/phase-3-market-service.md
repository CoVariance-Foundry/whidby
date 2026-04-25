# Phase 3: Create MarketService

**Objective:** Extract all business logic from the `niches_score` API handler in `api.py` into `src/domain/services/market_service.py`. The handler becomes a thin HTTP wrapper. Create infrastructure adapters wrapping existing clients to implement domain ports.

**Risk:** Medium — biggest single change. Validate with existing E2E suite. API contract must not change.
**Depends on:** Phase 1 (entities, ports), Phase 2 (GeoResolver).
**Blocks:** Phase 4, 5.

---

## Agent Instructions

### Step 0: Read and map the existing handler

Before writing anything, thoroughly read these files:

```bash
# The main handler — this is what we're extracting from
cat src/research_agent/api.py

# The pipeline orchestrator — MarketService will call this
cat src/pipeline/orchestrator.py

# Persistence layer — needs an adapter
cat src/clients/supabase_persistence.py

# KB persistence — needs an adapter
cat src/clients/kb_persistence.py

# DataForSEO client — needs an adapter
cat src/clients/dataforseo/client.py

# LLM client — needs an adapter
cat src/clients/llm/client.py
```

**Map every operation in the `niches_score` handler.** Create a checklist:

| Operation | Line(s) | Moves to |
|-----------|---------|----------|
| Parse request parameters | ? | Stays in handler |
| Resolve canonical keys | ? | GeoResolver (Phase 2) |
| Construct DataForSEO client | ? | Startup wiring (app lifespan) |
| Construct LLM client | ? | Startup wiring (app lifespan) |
| Run M4→M9 pipeline | ? | MarketService |
| Persist report | ? | MarketService → MarketStore |
| Flush cost logs | ? | MarketService → CostLogger |
| Upsert KB entity | ? | MarketService → KnowledgeStore |
| Create snapshot | ? | MarketService → KnowledgeStore |
| Store evidence artifacts | ? | MarketService → KnowledgeStore |
| Log feedback | ? | MarketService |
| Build response | ? | Stays in handler |

### Step 1: Create infrastructure adapters

Create thin adapters that wrap existing clients and implement domain ports.

**`src/clients/dataforseo/adapter.py`:**

```python
"""
Adapter wrapping DataForSEOClient to implement SERPDataProvider protocol.

This adapter does NOT change the client — it just maps its interface
to the domain port. The client continues to handle caching, retries, etc.
"""
from __future__ import annotations

from typing import Any

from src.clients.dataforseo.client import DataForSEOClient


class DataForSEOAdapter:
    """Implements SERPDataProvider using the existing DataForSEO client."""

    def __init__(self, client: DataForSEOClient):
        self._client = client

    async def fetch_keyword_volume(
        self, keywords: list[str], location_code: int
    ) -> list[dict[str, Any]]:
        """
        Map to the client's keyword volume method.
        Read client.py to find the exact method name and signature.
        """
        # return await self._client.get_keyword_data(keywords, location_code)
        raise NotImplementedError("Map to actual client method")

    async def fetch_serp_organic(
        self, keyword: str, location_code: int
    ) -> dict[str, Any]:
        """
        Map to the client's SERP organic method.
        Read client.py to find the exact method name and signature.
        """
        # return await self._client.get_serp_results(keyword, location_code)
        raise NotImplementedError("Map to actual client method")
```

**`src/clients/llm/adapter.py`:**

```python
"""Adapter wrapping LLMClient to implement KeywordExpander protocol."""
from __future__ import annotations

from typing import Any

from src.clients.llm.client import LLMClient


class LLMKeywordExpander:
    """Implements KeywordExpander using the existing LLM client."""

    def __init__(self, client: LLMClient):
        self._client = client

    async def expand(self, niche: str) -> dict[str, Any]:
        """
        Map to the client's keyword expansion method.
        Read client.py and orchestrator.py to find which method does expansion.
        """
        # return await self._client.expand_keywords(niche)
        raise NotImplementedError("Map to actual client method")
```

**`src/clients/supabase_adapter.py`:**

```python
"""Adapter wrapping Supabase persistence to implement MarketStore protocol."""
from __future__ import annotations

from typing import Any

from src.domain.entities import Market
from src.domain.queries import MarketQuery


class SupabaseMarketStore:
    """Implements MarketStore using existing Supabase persistence."""

    def __init__(self, persistence):
        """
        Accept the existing persistence instance.
        Read supabase_persistence.py to determine:
        - The class name
        - Constructor parameters
        - Available methods
        """
        self._persistence = persistence

    def persist_report(self, report: dict[str, Any]) -> str:
        """
        Map to _persist_report or equivalent.
        Must return the report ID.
        """
        # return self._persistence.persist_report(report)
        raise NotImplementedError("Map to actual persistence method")

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        """
        Map to _read_report_by_id or equivalent.
        Note: the redesign doc says supabase_persistence.py
        may not have a read method yet — add one if needed.
        """
        raise NotImplementedError("Map to actual persistence method")

    def query_markets(self, query: MarketQuery) -> list[Market]:
        """
        Phase 5 implements this fully. For now, return empty list.
        This method will query the reports table with filters from MarketQuery.
        """
        return []
```

**`src/clients/kb_adapter.py`:**

```python
"""Adapter wrapping KB persistence to implement KnowledgeStore protocol."""
from __future__ import annotations

from typing import Any

from src.clients.kb_persistence import KBPersistence


class KBKnowledgeStore:
    """Implements KnowledgeStore using existing KB persistence."""

    def __init__(self, kb: KBPersistence):
        self._kb = kb

    def upsert_entity(self, key: Any) -> str:
        """Map to kb.upsert_entity or equivalent."""
        raise NotImplementedError("Map to actual KB method")

    def create_snapshot(self, entity_id: str, **kwargs: Any) -> str:
        """Map to kb.create_snapshot or equivalent."""
        raise NotImplementedError("Map to actual KB method")

    def store_evidence(
        self, snapshot_id: str, artifact_type: str, payload: Any
    ) -> None:
        """Map to kb.store_evidence or equivalent."""
        raise NotImplementedError("Map to actual KB method")
```

### Step 2: Create MarketService

**`src/domain/services/market_service.py`:**

```python
"""
MarketService — single-market scoring orchestration.

Extracted from the niches_score handler in api.py.
This service coordinates: geo resolution → pipeline execution → persistence → KB update.

It does NOT:
- Parse HTTP requests (handler's job)
- Construct infrastructure clients (startup wiring's job)
- Shape HTTP responses (handler's job)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from src.domain.entities import City, Service, Market, ScoredMarket
from src.domain.lenses import ScoringLens, BALANCED
from src.domain.ports import (
    SERPDataProvider,
    KeywordExpander,
    MarketStore,
    KnowledgeStore,
    CostLogger,
)
from src.domain.services.geo_resolver import GeoResolver, ResolvedTarget

logger = logging.getLogger(__name__)


@dataclass
class ScoreRequest:
    """Input for scoring a single market. Maps from API request params."""
    niche_keyword: str
    city: str
    state: str | None = None
    strategy_profile: str = "balanced"
    dry_run: bool = False
    force_refresh: bool = False


@dataclass
class ScoreResult:
    """Output of scoring a single market. Handler maps this to API response."""
    report_id: str | None
    niche_keyword: str
    geo_target: str
    strategy_profile: str
    scores: dict[str, Any]
    metros: list[dict[str, Any]]
    keyword_expansion: dict[str, Any]
    timing: dict[str, float]
    dry_run: bool

    def to_api_response(self) -> dict[str, Any]:
        """Shape into the existing API response format for backward compat."""
        return {
            "report_id": self.report_id,
            "niche_keyword": self.niche_keyword,
            "geo_target": self.geo_target,
            "strategy_profile": self.strategy_profile,
            "scores": self.scores,
            "metros": self.metros,
            "keyword_expansion": self.keyword_expansion,
            "timing": self.timing,
            "dry_run": self.dry_run,
        }


class MarketService:
    """
    Scores a single market: resolve geo → run pipeline → persist → update KB.

    All infrastructure is injected through ports — no direct client construction.
    """

    def __init__(
        self,
        geo_resolver: GeoResolver,
        serp_provider: SERPDataProvider,
        keyword_expander: KeywordExpander,
        market_store: MarketStore,
        knowledge_store: KnowledgeStore,
        cost_logger: CostLogger | None = None,
    ):
        self._geo = geo_resolver
        self._serp = serp_provider
        self._expander = keyword_expander
        self._store = market_store
        self._kb = knowledge_store
        self._costs = cost_logger

    async def score(
        self,
        request: ScoreRequest,
        lens: ScoringLens | None = None,
    ) -> ScoreResult:
        """
        Score a single niche × city market.

        This method should contain the EXACT business logic currently in
        the niches_score handler, reorganized into this flow:

        1. Resolve geo target
        2. Run M4→M9 pipeline (via orchestrator.score_niche_for_metro)
        3. Persist report (unless dry_run)
        4. Update KB entities (unless dry_run)
        5. Flush cost logs
        6. Return ScoreResult

        The agent should read api.py's niches_score handler and transplant
        each operation into the appropriate step above.
        """
        lens = lens or BALANCED
        t_start = time.time()
        timing = {}

        # --- Step 1: Resolve geo ---
        t = time.time()
        target = self._geo.resolve(request.city, request.state)
        timing["geo_resolution"] = time.time() - t

        # --- Step 2: Run pipeline ---
        # Call orchestrator.score_niche_for_metro with the resolved target
        # IMPORTANT: The orchestrator currently takes raw clients as params.
        # Pass the adapter-wrapped versions.
        t = time.time()
        # pipeline_result = await score_niche_for_metro(
        #     niche_keyword=request.niche_keyword,
        #     metro=target,
        #     dataforseo_client=self._serp,
        #     llm_client=self._expander,
        #     strategy_profile=lens.lens_id,
        #     dry_run=request.dry_run,
        #     force_refresh=request.force_refresh,
        # )
        timing["pipeline"] = time.time() - t

        # --- Step 3: Persist report ---
        report_id = None
        if not request.dry_run:
            t = time.time()
            # report_id = self._store.persist_report(pipeline_result)
            timing["persist"] = time.time() - t

        # --- Step 4: Update KB ---
        if not request.dry_run:
            t = time.time()
            # entity_id = self._kb.upsert_entity(...)
            # snapshot_id = self._kb.create_snapshot(entity_id, ...)
            # self._kb.store_evidence(snapshot_id, ...)
            timing["kb_update"] = time.time() - t

        # --- Step 5: Flush costs ---
        if self._costs:
            pass  # self._costs.log(...)

        timing["total"] = time.time() - t_start

        # --- Build result ---
        # return ScoreResult(
        #     report_id=report_id,
        #     niche_keyword=request.niche_keyword,
        #     geo_target=target.canonical_key,
        #     strategy_profile=lens.lens_id,
        #     scores=pipeline_result["scores"],
        #     metros=pipeline_result["metros"],
        #     keyword_expansion=pipeline_result["keyword_expansion"],
        #     timing=timing,
        #     dry_run=request.dry_run,
        # )
        raise NotImplementedError("Complete after reading api.py")
```

### Step 3: Refactor the API handler

**In `src/research_agent/api.py`:**

The `niches_score` handler should become ~15 lines:

```python
@app.post("/api/niches/score")
async def niches_score(req: NicheScoreRequest) -> dict[str, Any]:
    """Single market scoring — backward compatible."""
    from src.domain.lenses import get_lens

    score_request = ScoreRequest(
        niche_keyword=req.niche_keyword,
        city=req.city,
        state=req.state,
        strategy_profile=req.strategy_profile or "balanced",
        dry_run=req.dry_run or False,
        force_refresh=req.force_refresh or False,
    )
    lens = get_lens(score_request.strategy_profile)
    result = await market_service.score(score_request, lens=lens)
    return result.to_api_response()
```

**Startup wiring (in app lifespan or startup event):**

```python
# Construct real clients once at startup
from src.clients.dataforseo.adapter import DataForSEOAdapter
from src.clients.llm.adapter import LLMKeywordExpander
from src.clients.supabase_adapter import SupabaseMarketStore
from src.clients.kb_adapter import KBKnowledgeStore
from src.data.metro_db_adapter import MetroDBGeoLookup
from src.domain.services.geo_resolver import GeoResolver
from src.domain.services.market_service import MarketService

# Build infrastructure
dfs_client = DataForSEOClient(...)  # from env vars, as before
llm_client = LLMClient(...)
supabase_client = create_supabase_client(...)
kb_client = KBPersistence(...)
metro_db = MetroDB(...)

# Wrap in adapters
serp_provider = DataForSEOAdapter(dfs_client)
keyword_expander = LLMKeywordExpander(llm_client)
market_store = SupabaseMarketStore(supabase_client)
knowledge_store = KBKnowledgeStore(kb_client)
geo_lookup = MetroDBGeoLookup(metro_db)
geo_resolver = GeoResolver(geo_lookup)

# Wire up domain service
market_service = MarketService(
    geo_resolver=geo_resolver,
    serp_provider=serp_provider,
    keyword_expander=keyword_expander,
    market_store=market_store,
    knowledge_store=knowledge_store,
)
```

### Step 4: Write tests

**`tests/domain/services/test_market_service.py`:**

```python
"""Tests for MarketService — scoring orchestration without infrastructure."""
import asyncio
import pytest
from src.domain.entities import City
from src.domain.lenses import BALANCED, EASY_WIN
from src.domain.services.market_service import MarketService, ScoreRequest, ScoreResult
from src.domain.services.geo_resolver import GeoResolver, ResolvedTarget


# --- Fakes ---

class FakeGeoLookup:
    def find_by_city(self, city, state=None):
        return City(city_id=f"{city.lower()}-{state.lower()}" if state else city.lower(), name=city, state=state)
    def all_metros(self):
        return []


class FakeSERPProvider:
    def __init__(self):
        self.calls = []

    async def fetch_keyword_volume(self, keywords, location_code):
        self.calls.append(("volume", keywords, location_code))
        return [{"keyword": kw, "volume": 1000} for kw in keywords]

    async def fetch_serp_organic(self, keyword, location_code):
        self.calls.append(("serp", keyword, location_code))
        return {"results": []}


class FakeKeywordExpander:
    async def expand(self, niche):
        return {"primary": niche, "variations": [f"{niche} near me"]}


class FakeMarketStore:
    def __init__(self):
        self.reports = {}

    def persist_report(self, report):
        rid = f"report-{len(self.reports) + 1}"
        self.reports[rid] = report
        return rid

    def read_report(self, report_id):
        return self.reports.get(report_id)

    def query_markets(self, query):
        return []


class FakeKnowledgeStore:
    def __init__(self):
        self.entities = {}
        self.snapshots = {}
        self.evidence = []

    def upsert_entity(self, key):
        eid = f"entity-{len(self.entities) + 1}"
        self.entities[eid] = key
        return eid

    def create_snapshot(self, entity_id, **kwargs):
        sid = f"snapshot-{len(self.snapshots) + 1}"
        self.snapshots[sid] = {"entity_id": entity_id, **kwargs}
        return sid

    def store_evidence(self, snapshot_id, artifact_type, payload):
        self.evidence.append((snapshot_id, artifact_type, payload))


class FakeCostLogger:
    def __init__(self):
        self.logs = []

    def log(self, provider, operation, cost):
        self.logs.append((provider, operation, cost))


@pytest.fixture
def market_service():
    geo = GeoResolver(FakeGeoLookup())
    return MarketService(
        geo_resolver=geo,
        serp_provider=FakeSERPProvider(),
        keyword_expander=FakeKeywordExpander(),
        market_store=FakeMarketStore(),
        knowledge_store=FakeKnowledgeStore(),
    )


def test_score_returns_result(market_service):
    """Scoring returns a ScoreResult with all fields."""
    req = ScoreRequest(niche_keyword="plumbing", city="Boise", state="ID")
    result = asyncio.run(market_service.score(req))
    assert isinstance(result, ScoreResult)
    assert result.niche_keyword == "plumbing"
    assert result.geo_target is not None


def test_score_persists_report(market_service):
    """Non-dry-run scoring persists a report."""
    req = ScoreRequest(niche_keyword="plumbing", city="Boise", state="ID")
    result = asyncio.run(market_service.score(req))
    assert result.report_id is not None
    assert market_service._store.reports  # has entries


def test_dry_run_skips_persistence(market_service):
    """Dry run does not persist or update KB."""
    req = ScoreRequest(niche_keyword="plumbing", city="Boise", state="ID", dry_run=True)
    result = asyncio.run(market_service.score(req))
    assert result.report_id is None
    assert result.dry_run is True


def test_score_with_lens(market_service):
    """Scoring with a specific lens uses that lens's ID."""
    req = ScoreRequest(niche_keyword="plumbing", city="Boise", state="ID")
    result = asyncio.run(market_service.score(req, lens=EASY_WIN))
    assert result.strategy_profile == "easy_win"


def test_to_api_response_format():
    """ScoreResult.to_api_response matches existing API contract."""
    result = ScoreResult(
        report_id="r-123",
        niche_keyword="plumbing",
        geo_target="boise-id",
        strategy_profile="balanced",
        scores={"opportunity": 75},
        metros=[{"name": "Boise"}],
        keyword_expansion={"primary": "plumbing"},
        timing={"total": 1.5},
        dry_run=False,
    )
    resp = result.to_api_response()
    assert resp["report_id"] == "r-123"
    assert resp["niche_keyword"] == "plumbing"
    assert "scores" in resp
    assert "timing" in resp
```

### Step 5: Validate

```bash
# Run new unit tests
python -m pytest tests/domain/services/test_market_service.py -v

# Run the FULL existing test suite — no regressions
python -m pytest tests/ -v

# Hit the API endpoint (if possible) and compare response shape
# The response JSON should be identical before/after this change
curl -X POST http://localhost:8000/api/niches/score \
  -H "Content-Type: application/json" \
  -d '{"niche_keyword":"plumbing","city":"Boise","state":"ID"}' \
  | python -m json.tool

# Verify handler is now thin
wc -l src/research_agent/api.py  # should be significantly shorter

# Verify domain import rules
grep -r "from src.clients" src/domain/ && echo "FAIL" || echo "PASS"
grep -r "import os" src/domain/services/ && echo "FAIL: env vars in domain" || echo "PASS"
```

**Done criteria:**
- `api.py`'s `niches_score` handler is ≤20 lines (validate, call service, return)
- All business logic lives in `MarketService.score()`
- Infrastructure is injected via adapters, not constructed in the handler
- Existing API contract is unchanged (same request/response shape)
- All existing tests pass
- New unit tests pass with in-memory fakes
- No `os.environ` or `os.getenv` calls in `src/domain/`
- Client construction happens once at startup, not per-request
