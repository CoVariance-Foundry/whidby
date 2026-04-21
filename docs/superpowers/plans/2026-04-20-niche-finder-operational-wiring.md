# Niche Finder Operational Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hash-based stub on the niche-scoring surface with a real end-to-end path — user enters `city + service`, the Python M4→M9 pipeline runs with live DataForSEO/Claude calls, the report is persisted to Supabase, and the dashboard renders the stored result.

**Architecture:** Add a single Python orchestrator (`src/pipeline/orchestrator.py`) that sequences the already-working modules M4 (keyword expansion) → M5 (collection) → M6 (signals) → M7 (scoring) → M8 (classification) → M9 (report). Expose it through two new FastAPI routes on the existing bridge in `src/research_agent/api.py`. Persist reports via a thin Supabase adapter (the schema in `supabase/migrations/001_core_schema.sql` already exists). Rewire the two stubbed Next.js routes (`/api/agent/scoring`, `/api/agent/exploration`) to proxy the FastAPI routes instead of computing a hash, and update the UI to handle the real latency (~30–60s) with loading + error states. A `dry_run` flag loads from existing M5/M6/M7 fixtures so frontend work doesn't burn live-API credits.

**Tech Stack:** Python 3.11 + pytest + httpx + Anthropic SDK + supabase-py, FastAPI on uvicorn, Next.js 16 App Router, Supabase (Postgres + auth), Playwright for E2E.

**Pre-existing state (do not re-implement):**
- M0 DataForSEO client at `src/clients/dataforseo/client.py` — real
- M1 metro DB at `src/data/metro_db.py` — `MetroDB.from_seed()` + `.expand_scope(...)` returns `list[Metro]` dataclasses with fields `cbsa_code`, `cbsa_name`, `state`, `population`, `principal_cities: list[str]`, `dataforseo_location_codes: list[int]`
- M3 LLM client at `src/clients/llm/client.py` — real
- M4 `expand_keywords(niche, *, llm_client, dataforseo_client, location_name, suggestions_limit)` at `src/pipeline/keyword_expansion.py:104` — async, real
- M5 `collect_data(keywords, metros, strategy_profile, client)` at `src/pipeline/data_collection.py:14` — async, real
- M6 `extract_signals(raw_metro_bundle, keyword_expansion, cross_metro_domain_stats, total_metros)` at `src/pipeline/signal_extraction.py:29` — sync, real
- M7 `compute_scores(*, metro_signals, all_metro_signals, strategy_profile)` at `src/scoring/engine.py:18` — sync, real
- M8 classifiers in `src/classification/` — `classify_ai_exposure`, `classify_serp_archetype`, `compute_difficulty_tier`, `classify_and_generate_guidance` — real
- M9 `generate_report(run_input, *, spec_version="1.1")` at `src/pipeline/report_generator.py:19` — sync, real
- Report input contract `REQUIRED_REPORT_INPUT_PATHS` at `src/pipeline/types.py:197` and metro entry paths at line 207
- Supabase schema: `reports`, `report_keywords`, `metro_signals`, `metro_scores` in `supabase/migrations/001_core_schema.sql`
- FastAPI app at `src/research_agent/api.py` with existing routes (`/health`, `/api/sessions`, `/api/chat`, `/api/exploration/followup`, `/api/graph`, `/api/experiments/{run_id}`)
- Next.js scoring stub at `apps/app/src/lib/niche-finder/response-adapter.ts:85` (to be deleted)

---

## Phase 0 — Observability: stop swallowing agent errors

The exploration assistant currently returns a generic "could not complete" string on any non-200 from FastAPI, so "the agent isn't working" has no actionable signal. Fix that first — every later phase depends on being able to see real errors.

### Task 1: Surface upstream errors in the exploration-chat proxy

**Files:**
- Modify: `apps/app/src/app/api/agent/exploration-chat/route.ts`
- Test: `apps/app/src/app/api/agent/exploration-chat/route.test.ts`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/app/api/agent/exploration-chat/route.test.ts`:

```ts
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { POST } from "./route";

describe("POST /api/agent/exploration-chat", () => {
  const originalFetch = global.fetch;
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { global.fetch = originalFetch; });

  it("returns upstream_status and upstream_body when FastAPI returns 500", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "agent crashed" }), { status: 500 }),
    );
    const req = new Request("http://localhost/api/agent/exploration-chat", {
      method: "POST",
      body: JSON.stringify({
        query_context: { city: "Phoenix", service: "roofing" },
        question: "why",
        session_id: "s1",
      }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unsupported");
    expect(body.upstream_status).toBe(500);
    expect(body.upstream_body).toContain("agent crashed");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/app && npx vitest run src/app/api/agent/exploration-chat/route.test.ts`
Expected: FAIL — response lacks `upstream_status`.

- [ ] **Step 3: Update the route to pass upstream details through**

Edit `apps/app/src/app/api/agent/exploration-chat/route.ts`, replacing the block at lines 32–45:

```ts
    if (!res.ok) {
      const upstreamBody = await res.text();
      return NextResponse.json(
        {
          response_id: crypto.randomUUID(),
          session_id: body.session_id ?? "",
          query_context: ctx,
          answer:
            "The exploration assistant could not complete this request. Try narrowing the question.",
          evidence_references: [],
          status: "unsupported",
          upstream_status: res.status,
          upstream_body: upstreamBody.slice(0, 2000),
        },
        { status: 502 }
      );
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/app && npx vitest run src/app/api/agent/exploration-chat/route.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/app/api/agent/exploration-chat/route.ts \
        apps/app/src/app/api/agent/exploration-chat/route.test.ts
git commit -m "fix(app): surface FastAPI upstream error body in exploration-chat proxy"
```

### Task 2: Add `/api/agent/health` Next.js route proxying FastAPI `/health`

**Files:**
- Create: `apps/app/src/app/api/agent/health/route.ts`
- Create: `apps/app/src/app/api/agent/health/route.test.ts`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/app/api/agent/health/route.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { GET } from "./route";

describe("GET /api/agent/health", () => {
  it("returns ok when FastAPI /health returns ok", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
    expect(body.upstream).toBe("ok");
  });

  it("returns unavailable with upstream_status when FastAPI is down", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("ECONNREFUSED"));
    const res = await GET();
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.error).toContain("ECONNREFUSED");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/app && npx vitest run src/app/api/agent/health/route.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the route**

Create `apps/app/src/app/api/agent/health/route.ts`:

```ts
import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    const text = await res.text();
    return NextResponse.json(
      {
        status: res.ok ? "ok" : "unavailable",
        upstream: res.ok ? "ok" : "error",
        upstream_status: res.status,
        upstream_body: text.slice(0, 500),
        api_base: API_BASE,
      },
      { status: res.ok ? 200 : 502 },
    );
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        upstream: "unreachable",
        error: err instanceof Error ? err.message : String(err),
        api_base: API_BASE,
      },
      { status: 502 },
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/app && npx vitest run src/app/api/agent/health/route.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/app/api/agent/health/route.ts \
        apps/app/src/app/api/agent/health/route.test.ts
git commit -m "feat(app): add /api/agent/health proxy for FastAPI bridge diagnostics"
```

---

## Phase 1 — Python end-to-end orchestrator

Currently there is no single function that runs a niche through the full pipeline. Callers have to wire M4 → M5 → M6 → M7 → M8 → M9 by hand. Build one.

### Task 3: Define the orchestrator contract (TDD — tests first)

**Files:**
- Create: `tests/unit/test_pipeline_orchestrator.py`
- Create: (Task 4) `src/pipeline/orchestrator.py`

- [ ] **Step 1: Write the failing unit test with fake clients**

Create `tests/unit/test_pipeline_orchestrator.py`:

```python
"""Unit tests for the end-to-end niche-scoring orchestrator.

Patches each M4-M9 entrypoint at the module level so this test validates
composition and data flow only. Real M4-M9 behavior is covered by each
module's own tests and by the live integration smoke in Task 6.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.pipeline.orchestrator import ScoreNicheResult, score_niche_for_metro


_FAKE_KEYWORD_EXPANSION = {
    "niche": "roofing",
    "keywords": [
        {"keyword": "roofing near me", "tier": 1, "intent": "transactional",
         "source": "llm", "aio_risk": "low", "search_volume": 2000, "cpc": 12.5},
    ],
}

_FAKE_RAW_COLLECTION = {
    "run_id": "run-abc",
    "metros": {
        "38060": {  # Phoenix CBSA code
            "serp_organic": [], "serp_maps": [], "keyword_volume": [],
            "backlinks": [], "lighthouse": [], "google_reviews": [],
            "gbp_info": [], "business_listings": [],
        }
    },
    "total_api_calls": 8,
    "total_cost_usd": 0.12,
}

_FAKE_SIGNALS = {
    "demand": {"tier_1_volume_effective": 4200},
    "organic_competition": {"median_top10_dr": 45},
    "local_competition": {"gbp_saturation": 0.6},
    "ai_resilience": {"aio_rate": 0.1},
    "monetization": {"median_cpc": 12.5},
}

_FAKE_SCORES = {
    "demand": 70, "organic_competition": 40, "local_competition": 55,
    "monetization": 65, "ai_resilience": 80, "opportunity": 72,
    "confidence": 0.82, "resolved_weights": {"organic": 0.6, "local": 0.4},
}


def test_score_niche_for_metro_composes_pipeline_and_returns_result() -> None:
    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data",
               new=AsyncMock(return_value=_FAKE_RAW_COLLECTION)), \
         patch("src.pipeline.orchestrator.extract_signals",
               return_value=_FAKE_SIGNALS), \
         patch("src.pipeline.orchestrator.compute_scores",
               return_value=_FAKE_SCORES), \
         patch("src.pipeline.orchestrator.classify_ai_exposure", return_value="low"), \
         patch("src.pipeline.orchestrator.classify_serp_archetype",
               return_value="local_first"), \
         patch("src.pipeline.orchestrator.compute_difficulty_tier", return_value="T2"), \
         patch("src.pipeline.orchestrator.classify_and_generate_guidance",
               return_value={"strategy": "lead local"}):
        result = asyncio.run(
            score_niche_for_metro(
                niche="roofing",
                city="Phoenix",
                state="AZ",
                strategy_profile="balanced",
                llm_client=object(),
                dataforseo_client=object(),
            )
        )

    assert isinstance(result, ScoreNicheResult)
    assert result.report["spec_version"] == "1.1"
    assert result.report["input"]["niche_keyword"] == "roofing"
    assert result.report["input"]["geo_target"] == "Phoenix, AZ"
    assert len(result.report["metros"]) == 1
    metro = result.report["metros"][0]
    assert metro["cbsa_code"] == "38060"
    assert metro["ai_exposure"] == "low"
    assert metro["serp_archetype"] == "local_first"
    assert metro["difficulty_tier"] == "T2"
    assert result.opportunity_score == 72
    assert len(result.evidence) == 4
    categories = {e["category"] for e in result.evidence}
    assert categories == {"demand", "competition", "monetization", "ai_resilience"}


def test_score_niche_raises_valueerror_on_unknown_city() -> None:
    import pytest
    with pytest.raises(ValueError, match="no CBSA match"):
        asyncio.run(
            score_niche_for_metro(
                niche="roofing",
                city="Atlantis",
                state="AZ",
                llm_client=object(),
                dataforseo_client=object(),
            )
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pipeline_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: src.pipeline.orchestrator`.

- [ ] **Step 3: Commit the red test**

```bash
git add tests/unit/test_pipeline_orchestrator.py
git commit -m "test(pipeline): add failing spec for end-to-end niche orchestrator"
```

### Task 4: Implement the orchestrator

**Files:**
- Create: `src/pipeline/orchestrator.py`

- [ ] **Step 1: Write the implementation**

Create `src/pipeline/orchestrator.py`:

```python
"""End-to-end niche-scoring orchestrator (M4 -> M9) for a single metro."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from src.classification.ai_exposure import classify_ai_exposure
from src.classification.difficulty_tier import compute_difficulty_tier
from src.classification.guidance_generator import classify_and_generate_guidance
from src.classification.serp_archetype import classify_serp_archetype
from src.data.metro_db import MetroDB
from src.pipeline.data_collection import collect_data
from src.pipeline.keyword_expansion import expand_keywords
from src.pipeline.report_generator import generate_report
from src.pipeline.signal_extraction import extract_signals
from src.scoring.engine import compute_scores


@dataclass(frozen=True)
class ScoreNicheResult:
    """Report plus pre-derived fields for convenience on the API boundary."""

    report: dict[str, Any]
    opportunity_score: int
    evidence: list[dict[str, Any]]


async def score_niche_for_metro(
    *,
    niche: str,
    city: str,
    state: str,
    strategy_profile: str = "balanced",
    llm_client: Any,
    dataforseo_client: Any,
    metro_db: MetroDB | None = None,
) -> ScoreNicheResult:
    """Score a (niche, city, state) pair end-to-end.

    Runs M4 -> M5 -> M6 -> M7 -> M8 -> M9 against the single metro that
    matches (city, state). Raises ValueError if the metro is unknown.
    """
    started = time.monotonic()
    metros_db = metro_db or MetroDB.from_seed()
    candidates = metros_db.expand_scope(scope="state", target=state, depth="standard")
    city_norm = city.strip().lower()
    target = next(
        (
            m for m in candidates
            if any(pc.strip().lower() == city_norm for pc in m.principal_cities)
            or city_norm in m.cbsa_name.lower()
        ),
        None,
    )
    if target is None:
        raise ValueError(f"no CBSA match for city={city!r} state={state!r}")

    target_dict: dict[str, Any] = {
        "cbsa_code": target.cbsa_code,
        "cbsa_name": target.cbsa_name,
        "state": target.state,
        "population": target.population,
        "principal_cities": list(target.principal_cities),
        "dataforseo_location_codes": list(target.dataforseo_location_codes),
    }

    expansion = await expand_keywords(
        niche,
        llm_client=llm_client,
        dataforseo_client=dataforseo_client,
    )

    raw = await collect_data(
        keywords=expansion["keywords"],
        metros=[target_dict],
        strategy_profile=strategy_profile,
        client=dataforseo_client,
    )

    metro_bundle = raw["metros"][target.cbsa_code]
    signals = extract_signals(
        raw_metro_bundle=metro_bundle,
        keyword_expansion=expansion["keywords"],
        cross_metro_domain_stats=None,
        total_metros=1,
    )

    scores = compute_scores(
        metro_signals=signals,
        all_metro_signals=[signals],
        strategy_profile=strategy_profile,
    )

    ai_exposure = classify_ai_exposure(signals, expansion["keywords"])
    serp_archetype = classify_serp_archetype(signals)
    difficulty = compute_difficulty_tier(scores)
    guidance = classify_and_generate_guidance(
        scores=scores,
        signals=signals,
        ai_exposure=ai_exposure,
        serp_archetype=serp_archetype,
        difficulty_tier=difficulty,
    )

    run_input = {
        "run_id": raw["run_id"],
        "input": {
            "niche_keyword": niche,
            "geo_scope": "city",
            "geo_target": f"{city}, {state}",
            "report_depth": "standard",
            "strategy_profile": strategy_profile,
        },
        "keyword_expansion": expansion,
        "metros": [
            {
                "cbsa_code": target.cbsa_code,
                "cbsa_name": target.cbsa_name,
                "population": target.population,
                "scores": scores,
                "confidence": scores["confidence"],
                "serp_archetype": serp_archetype,
                "ai_exposure": ai_exposure,
                "difficulty_tier": difficulty,
                "signals": signals,
                "guidance": guidance,
            }
        ],
        "meta": {
            "total_api_calls": raw.get("total_api_calls", 0),
            "total_cost_usd": raw.get("total_cost_usd", 0.0),
            "processing_time_seconds": time.monotonic() - started,
        },
    }

    report = generate_report(run_input)

    evidence = _build_evidence_from_signals(signals)
    return ScoreNicheResult(
        report=report,
        opportunity_score=int(round(scores["opportunity"])),
        evidence=evidence,
    )


def _build_evidence_from_signals(signals: dict[str, dict]) -> list[dict[str, Any]]:
    def _read(category: str, key: str, default: float = 0.0) -> float:
        node = signals.get(category) or {}
        value = node.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    return [
        {
            "category": "demand",
            "label": "Tier-1 Transactional Volume",
            "value": _read("demand", "tier_1_volume_effective"),
            "source": "M6 demand signals",
            "is_available": True,
        },
        {
            "category": "competition",
            "label": "Median Top-10 Domain Rating",
            "value": _read("organic_competition", "median_top10_dr"),
            "source": "M6 organic competition",
            "is_available": True,
        },
        {
            "category": "monetization",
            "label": "Median Commercial CPC",
            "value": _read("monetization", "median_cpc"),
            "source": "M6 monetization",
            "is_available": True,
        },
        {
            "category": "ai_resilience",
            "label": "AI Overview Penetration",
            "value": _read("ai_resilience", "aio_rate"),
            "source": "M6 AI resilience",
            "is_available": True,
        },
    ]
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_pipeline_orchestrator.py -v`
Expected: PASS (`test_score_niche_for_metro_returns_report_and_score_result`).

- [ ] **Step 3: Run the full unit suite to catch regressions**

Run: `pytest tests/unit/ -v`
Expected: PASS. If any existing test fails, stop and debug — the orchestrator must not break the module-level tests.

- [ ] **Step 4: Lint**

Run: `ruff check src/pipeline/orchestrator.py tests/unit/test_pipeline_orchestrator.py`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/orchestrator.py tests/unit/test_pipeline_orchestrator.py
git commit -m "feat(pipeline): add score_niche_for_metro end-to-end orchestrator (M4-M9)"
```

### Task 5: Add a dry-run path using existing M5/M6 fixtures

Live-API runs cost money and take ~30–60s. Provide a `dry_run=True` mode that loads from existing fixtures so the UI can be developed and Playwright-tested cheaply.

**Files:**
- Modify: `src/pipeline/orchestrator.py`
- Modify: `tests/unit/test_pipeline_orchestrator.py`

- [ ] **Step 1: Write the failing dry-run test**

Append to `tests/unit/test_pipeline_orchestrator.py`:

```python
def test_dry_run_returns_deterministic_report_without_clients() -> None:
    first = asyncio.run(
        score_niche_for_metro(
            niche="roofing",
            city="Phoenix",
            state="AZ",
            llm_client=None,
            dataforseo_client=None,
            dry_run=True,
        )
    )
    second = asyncio.run(
        score_niche_for_metro(
            niche="roofing",
            city="Phoenix",
            state="AZ",
            llm_client=None,
            dataforseo_client=None,
            dry_run=True,
        )
    )
    assert first.opportunity_score == second.opportunity_score
    assert first.report["metros"][0]["cbsa_code"] == second.report["metros"][0]["cbsa_code"]
    assert first.report["meta"]["total_cost_usd"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pipeline_orchestrator.py::test_dry_run_returns_deterministic_report_without_clients -v`
Expected: FAIL — `score_niche_for_metro` doesn't accept `dry_run`.

- [ ] **Step 3: Implement the dry-run path**

In `src/pipeline/orchestrator.py`, add `dry_run: bool = False` to the function signature. At the top of the body (after validating the metro), branch:

```python
    if dry_run:
        return _dry_run_result(
            niche=niche,
            city=city,
            state=state,
            target=target,
            strategy_profile=strategy_profile,
            started=started,
        )
```

Then add below the function:

```python
from src.data.metro_db import Metro  # add to imports at top of file


def _dry_run_result(
    *,
    niche: str,
    city: str,
    state: str,
    target: Metro,
    strategy_profile: str,
    started: float,
) -> ScoreNicheResult:
    from tests.fixtures.m6_signal_extraction_fixtures import fixture_metro_signals
    from tests.fixtures.keyword_expansion_fixtures import fixture_keyword_expansion

    signals = fixture_metro_signals()
    expansion = fixture_keyword_expansion(niche)
    scores = compute_scores(
        metro_signals=signals,
        all_metro_signals=[signals],
        strategy_profile=strategy_profile,
    )
    ai_exposure = classify_ai_exposure(signals, expansion["keywords"])
    serp_archetype = classify_serp_archetype(signals)
    difficulty = compute_difficulty_tier(scores)
    guidance = classify_and_generate_guidance(
        scores=scores,
        signals=signals,
        ai_exposure=ai_exposure,
        serp_archetype=serp_archetype,
        difficulty_tier=difficulty,
    )
    run_input = {
        "run_id": f"dry-run-{target.cbsa_code}",
        "input": {
            "niche_keyword": niche,
            "geo_scope": "city",
            "geo_target": f"{city}, {state}",
            "report_depth": "standard",
            "strategy_profile": strategy_profile,
        },
        "keyword_expansion": expansion,
        "metros": [
            {
                "cbsa_code": target.cbsa_code,
                "cbsa_name": target.cbsa_name,
                "population": target.population,
                "scores": scores,
                "confidence": scores["confidence"],
                "serp_archetype": serp_archetype,
                "ai_exposure": ai_exposure,
                "difficulty_tier": difficulty,
                "signals": signals,
                "guidance": guidance,
            }
        ],
        "meta": {
            "total_api_calls": 0,
            "total_cost_usd": 0.0,
            "processing_time_seconds": time.monotonic() - started,
        },
    }
    report = generate_report(run_input)
    return ScoreNicheResult(
        report=report,
        opportunity_score=int(round(scores["opportunity"])),
        evidence=_build_evidence_from_signals(signals),
    )
```

If `fixture_metro_signals` or `fixture_keyword_expansion` helpers don't exist in those fixture modules, add thin wrappers that return a single prebuilt bundle (read the current fixture modules to find the right attribute name — e.g. `M6_DEMAND_FIXTURE` — and adapt). Commit the helper(s) in the same task.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_pipeline_orchestrator.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/pipeline/orchestrator.py tests/unit/test_pipeline_orchestrator.py
git add src/pipeline/orchestrator.py tests/unit/test_pipeline_orchestrator.py tests/fixtures/
git commit -m "feat(pipeline): add dry_run mode to orchestrator using M6/M4 fixtures"
```

### Task 6: Live integration smoke test (marked, network required)

**Files:**
- Create: `tests/integration/test_pipeline_orchestrator_live.py`

- [ ] **Step 1: Write the integration test**

```python
"""Live integration smoke: one small niche, one metro, real APIs."""
from __future__ import annotations

import asyncio
import os

import pytest

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.llm.client import LLMClient
from src.pipeline.orchestrator import score_niche_for_metro

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not all(os.getenv(k) for k in ("DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD", "ANTHROPIC_API_KEY")),
    reason="live API credentials required",
)
def test_end_to_end_roofing_phoenix() -> None:
    async def _run() -> None:
        async with DataForSEOClient() as dfs:
            llm = LLMClient()
            result = await score_niche_for_metro(
                niche="roofing",
                city="Phoenix",
                state="AZ",
                llm_client=llm,
                dataforseo_client=dfs,
            )
            assert 0 <= result.opportunity_score <= 100
            assert result.report["metros"][0]["cbsa_name"].lower().startswith("phoenix")

    asyncio.run(_run())
```

- [ ] **Step 2: Run locally only if creds are set (skip otherwise)**

Run: `pytest tests/integration/test_pipeline_orchestrator_live.py -v -m integration`
Expected: PASS if creds present, SKIPPED otherwise.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_pipeline_orchestrator_live.py
git commit -m "test(pipeline): add live end-to-end smoke for score_niche_for_metro"
```

---

## Phase 2 — Supabase persistence (minimum viable)

The schema exists (`supabase/migrations/001_core_schema.sql`). Write a thin adapter that persists the M9 report as one row in `reports` plus normalized rows in `report_keywords`, `metro_signals`, `metro_scores`. Skip the experiment/outreach tables — out of scope for this plan.

### Task 7: Add `SUPABASE_SERVICE_ROLE_KEY` to env docs and install supabase-py

**Files:**
- Modify: `.env.example`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add the env var**

Edit `.env.example` — add after the existing Supabase publishable key:

```
# Server-side Supabase key for the Python scoring engine (never expose to browser)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

- [ ] **Step 2: Add supabase dependency**

In `pyproject.toml`, add `supabase = "^2.7.0"` to the main dependency list (or `[tool.poetry.dependencies]` / `[project.dependencies]` section — match the existing style in the file).

- [ ] **Step 3: Install**

Run: `pip install supabase` (or the project's standard install command — check `README.md` / `docs-canonical/ENVIRONMENT.md`).
Expected: installs cleanly.

- [ ] **Step 4: Commit**

```bash
git add .env.example pyproject.toml
git commit -m "chore(deps): add supabase-py and SUPABASE_SERVICE_ROLE_KEY env"
```

### Task 8: Write the Supabase report-persistence adapter (TDD with mocks)

**Files:**
- Create: `src/clients/supabase_persistence.py`
- Create: `tests/unit/test_supabase_persistence.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_supabase_persistence.py`:

```python
"""Unit tests for the Supabase report persistence adapter."""
from __future__ import annotations

from typing import Any

import pytest

from src.clients.supabase_persistence import (
    SupabasePersistence,
    build_report_row,
    build_keyword_rows,
    build_metro_signal_rows,
    build_metro_score_rows,
)


def _sample_report() -> dict[str, Any]:
    return {
        "report_id": "11111111-1111-1111-1111-111111111111",
        "generated_at": "2026-04-20T00:00:00+00:00",
        "spec_version": "1.1",
        "input": {
            "niche_keyword": "roofing",
            "geo_scope": "city",
            "geo_target": "Phoenix, AZ",
            "report_depth": "standard",
            "strategy_profile": "balanced",
        },
        "keyword_expansion": {
            "niche": "roofing",
            "keywords": [
                {"keyword": "roofing near me", "tier": 1, "intent": "transactional",
                 "source": "llm", "aio_risk": "low", "search_volume": 2000, "cpc": 12.5},
            ],
        },
        "metros": [
            {
                "cbsa_code": "38060",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "population": 5000000,
                "scores": {
                    "demand": 70, "organic_competition": 40, "local_competition": 55,
                    "monetization": 65, "ai_resilience": 80, "opportunity": 72,
                    "confidence": 0.82, "resolved_weights": {"organic": 0.6, "local": 0.4},
                },
                "confidence": 0.82,
                "serp_archetype": "local_first",
                "ai_exposure": "low",
                "difficulty_tier": "T2",
                "signals": {"demand": {"tier_1_volume_effective": 4200}},
                "guidance": {"strategy": "lead with local"},
            }
        ],
        "meta": {
            "total_api_calls": 12,
            "total_cost_usd": 0.18,
            "processing_time_seconds": 33.4,
            "feedback_log_id": "22222222-2222-2222-2222-222222222222",
        },
    }


def test_build_report_row_maps_core_fields() -> None:
    row = build_report_row(_sample_report())
    assert row["id"] == "11111111-1111-1111-1111-111111111111"
    assert row["niche_keyword"] == "roofing"
    assert row["geo_scope"] == "city"
    assert row["geo_target"] == "Phoenix, AZ"
    assert row["strategy_profile"] == "balanced"
    assert row["feedback_log_id"] == "22222222-2222-2222-2222-222222222222"
    assert isinstance(row["metros"], list)


def test_build_keyword_rows_one_per_keyword() -> None:
    rows = build_keyword_rows(_sample_report())
    assert len(rows) == 1
    assert rows[0]["keyword"] == "roofing near me"
    assert rows[0]["tier"] == 1
    assert rows[0]["report_id"] == "11111111-1111-1111-1111-111111111111"


def test_build_metro_signal_and_score_rows() -> None:
    signal_rows = build_metro_signal_rows(_sample_report())
    score_rows = build_metro_score_rows(_sample_report())
    assert len(signal_rows) == 1 and len(score_rows) == 1
    assert signal_rows[0]["cbsa_code"] == "38060"
    assert score_rows[0]["opportunity_score"] == 72


class _FakeTable:
    def __init__(self, sink: list[dict]) -> None:
        self.sink = sink

    def insert(self, payload: Any) -> "_FakeTable":
        if isinstance(payload, list):
            self.sink.extend(payload)
        else:
            self.sink.append(payload)
        return self

    def execute(self) -> Any:
        class _R: data = self.sink
        return _R()


class _FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}

    def table(self, name: str) -> _FakeTable:
        self.tables.setdefault(name, [])
        return _FakeTable(self.tables[name])


def test_persist_report_writes_to_all_four_tables() -> None:
    fake = _FakeSupabase()
    adapter = SupabasePersistence(client=fake)
    report_id = adapter.persist_report(_sample_report())
    assert report_id == "11111111-1111-1111-1111-111111111111"
    assert len(fake.tables["reports"]) == 1
    assert len(fake.tables["report_keywords"]) == 1
    assert len(fake.tables["metro_signals"]) == 1
    assert len(fake.tables["metro_scores"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_supabase_persistence.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write the implementation**

Create `src/clients/supabase_persistence.py`:

```python
"""Persist M9 reports to the Supabase schema defined in 001_core_schema.sql."""
from __future__ import annotations

import os
from typing import Any, Protocol


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any: ...


def build_report_row(report: dict[str, Any]) -> dict[str, Any]:
    run_input = report["input"]
    return {
        "id": report["report_id"],
        "created_at": report["generated_at"],
        "spec_version": report["spec_version"],
        "niche_keyword": run_input["niche_keyword"],
        "geo_scope": run_input["geo_scope"],
        "geo_target": run_input["geo_target"],
        "report_depth": run_input.get("report_depth", "standard"),
        "strategy_profile": run_input.get("strategy_profile", "balanced"),
        "resolved_weights": report["metros"][0]["scores"].get("resolved_weights") if report["metros"] else None,
        "keyword_expansion": report["keyword_expansion"],
        "metros": report["metros"],
        "meta": report["meta"],
        "feedback_log_id": report["meta"].get("feedback_log_id"),
    }


def build_keyword_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    keywords = report["keyword_expansion"].get("keywords", [])
    rows: list[dict[str, Any]] = []
    for kw in keywords:
        rows.append({
            "report_id": report_id,
            "keyword": kw["keyword"],
            "tier": int(kw.get("tier", 3)),
            "intent": kw.get("intent", "informational"),
            "source": kw.get("source", "llm"),
            "aio_risk": kw.get("aio_risk", "low"),
            "search_volume": kw.get("search_volume"),
            "cpc": kw.get("cpc"),
        })
    return rows


def build_metro_signal_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    for metro in report["metros"]:
        signals = metro.get("signals") or {}
        rows.append({
            "report_id": report_id,
            "cbsa_code": metro["cbsa_code"],
            "cbsa_name": metro["cbsa_name"],
            "demand": signals.get("demand"),
            "organic_competition": signals.get("organic_competition"),
            "local_competition": signals.get("local_competition"),
            "ai_resilience": signals.get("ai_resilience"),
            "monetization": signals.get("monetization"),
        })
    return rows


def build_metro_score_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_id = report["report_id"]
    rows: list[dict[str, Any]] = []
    for metro in report["metros"]:
        scores = metro["scores"]
        rows.append({
            "report_id": report_id,
            "cbsa_code": metro["cbsa_code"],
            "demand_score": int(round(scores["demand"])),
            "organic_competition_score": int(round(scores["organic_competition"])),
            "local_competition_score": int(round(scores["local_competition"])),
            "monetization_score": int(round(scores["monetization"])),
            "ai_resilience_score": int(round(scores["ai_resilience"])),
            "opportunity_score": int(round(scores["opportunity"])),
            "confidence": float(scores["confidence"]),
            "serp_archetype": metro["serp_archetype"],
            "ai_exposure": metro["ai_exposure"],
            "difficulty_tier": metro["difficulty_tier"],
        })
    return rows


class SupabasePersistence:
    """Writes an M9 report and its normalized children to Supabase."""

    def __init__(self, *, client: _SupabaseLike | None = None) -> None:
        if client is None:
            from supabase import create_client
            url = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
            key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
            client = create_client(url, key)
        self._client = client

    def persist_report(self, report: dict[str, Any]) -> str:
        self._client.table("reports").insert(build_report_row(report)).execute()
        keyword_rows = build_keyword_rows(report)
        if keyword_rows:
            self._client.table("report_keywords").insert(keyword_rows).execute()
        signal_rows = build_metro_signal_rows(report)
        if signal_rows:
            self._client.table("metro_signals").insert(signal_rows).execute()
        score_rows = build_metro_score_rows(report)
        if score_rows:
            self._client.table("metro_scores").insert(score_rows).execute()
        return report["report_id"]
```

Note: the `metro_scores` column list above matches `001_core_schema.sql:54-70`. If that column list drifts, update both together.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_supabase_persistence.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/clients/supabase_persistence.py tests/unit/test_supabase_persistence.py
git add src/clients/supabase_persistence.py tests/unit/test_supabase_persistence.py
git commit -m "feat(clients): add Supabase persistence adapter for M9 reports"
```

---

## Phase 3 — FastAPI niche-scoring routes

The existing FastAPI app at `src/research_agent/api.py` is the Next.js bridge. Add two routes. Keep them thin — orchestrator + persistence already own the logic.

### Task 9: Add `POST /api/niches/score` and `GET /api/niches/{report_id}`

**Files:**
- Modify: `src/research_agent/api.py`
- Create: `tests/unit/test_api_niches.py`

- [ ] **Step 1: Write the failing API test**

Create `tests/unit/test_api_niches.py`:

```python
"""Unit tests for the FastAPI /api/niches routes."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.research_agent.api import app


class _FakeScoreResult:
    def __init__(self) -> None:
        self.report = {
            "report_id": "abc",
            "generated_at": "2026-04-20T00:00:00+00:00",
            "spec_version": "1.1",
            "input": {"niche_keyword": "roofing", "geo_scope": "city",
                      "geo_target": "Phoenix, AZ", "report_depth": "standard",
                      "strategy_profile": "balanced"},
            "keyword_expansion": {"niche": "roofing", "keywords": []},
            "metros": [{"cbsa_code": "38060", "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                         "population": 5000000,
                         "scores": {"demand": 70, "organic_competition": 40,
                                    "local_competition": 55, "monetization": 65,
                                    "ai_resilience": 80, "opportunity": 72,
                                    "confidence": 0.82},
                         "confidence": 0.82, "serp_archetype": "local_first",
                         "ai_exposure": "low", "difficulty_tier": "T2",
                         "signals": {}, "guidance": {}}],
            "meta": {"total_api_calls": 0, "total_cost_usd": 0.0,
                      "processing_time_seconds": 0.1, "feedback_log_id": "fb"},
        }
        self.opportunity_score = 72
        self.evidence = [{"category": "demand", "label": "x", "value": 1.0,
                           "source": "s", "is_available": True}]


def test_post_niches_score_dry_run_returns_report_and_opportunity(monkeypatch: Any) -> None:
    async def _fake_orchestrator(**kwargs: Any) -> _FakeScoreResult:
        assert kwargs["dry_run"] is True
        return _FakeScoreResult()

    with patch("src.research_agent.api.score_niche_for_metro", new=_fake_orchestrator), \
         patch("src.research_agent.api._persist_report", return_value="abc"):
        client = TestClient(app)
        res = client.post("/api/niches/score", json={
            "niche": "roofing", "city": "Phoenix", "state": "AZ", "dry_run": True,
        })
    assert res.status_code == 200
    body = res.json()
    assert body["report_id"] == "abc"
    assert body["opportunity_score"] == 72
    assert body["evidence"][0]["category"] == "demand"


def test_post_niches_score_validation_error_on_empty_city() -> None:
    client = TestClient(app)
    res = client.post("/api/niches/score", json={"niche": "roofing", "city": "", "state": "AZ"})
    assert res.status_code == 400


def test_get_niches_report_reads_from_supabase(monkeypatch: Any) -> None:
    fake_row = {
        "id": "abc", "niche_keyword": "roofing", "geo_target": "Phoenix, AZ",
        "metros": [{"cbsa_code": "38060", "scores": {"opportunity": 72}}],
        "created_at": "2026-04-20T00:00:00+00:00", "spec_version": "1.1",
        "keyword_expansion": {"keywords": []}, "meta": {}, "report_depth": "standard",
        "strategy_profile": "balanced", "geo_scope": "city",
    }
    with patch("src.research_agent.api._read_report_by_id", return_value=fake_row):
        client = TestClient(app)
        res = client.get("/api/niches/abc")
    assert res.status_code == 200
    body = res.json()
    assert body["report_id"] == "abc"
    assert body["input"]["niche_keyword"] == "roofing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_api_niches.py -v`
Expected: FAIL — routes not defined.

- [ ] **Step 3: Implement the routes**

In `src/research_agent/api.py`, add near the other routes:

```python
from pydantic import BaseModel, field_validator

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.llm.client import LLMClient
from src.clients.supabase_persistence import SupabasePersistence
from src.pipeline.orchestrator import score_niche_for_metro


class NicheScoreRequest(BaseModel):
    niche: str
    city: str
    state: str
    strategy_profile: str = "balanced"
    dry_run: bool = False

    @field_validator("niche", "city", "state")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must be non-empty")
        return v


def _persist_report(report: dict[str, Any]) -> str:
    return SupabasePersistence().persist_report(report)


def _read_report_by_id(report_id: str) -> dict[str, Any] | None:
    from supabase import create_client
    import os
    client = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    res = client.table("reports").select("*").eq("id", report_id).limit(1).execute()
    return res.data[0] if res.data else None


@app.post("/api/niches/score")
async def niches_score(req: NicheScoreRequest) -> dict[str, Any]:
    try:
        if req.dry_run:
            result = await score_niche_for_metro(
                niche=req.niche, city=req.city, state=req.state,
                strategy_profile=req.strategy_profile,
                llm_client=None, dataforseo_client=None, dry_run=True,
            )
        else:
            async with DataForSEOClient() as dfs:
                llm = LLMClient()
                result = await score_niche_for_metro(
                    niche=req.niche, city=req.city, state=req.state,
                    strategy_profile=req.strategy_profile,
                    llm_client=llm, dataforseo_client=dfs,
                )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    report_id = _persist_report(result.report)
    return {
        "report_id": report_id,
        "opportunity_score": result.opportunity_score,
        "classification_label": (
            "High" if result.opportunity_score >= 75
            else "Medium" if result.opportunity_score >= 50
            else "Low"
        ),
        "evidence": result.evidence,
        "report": result.report,
    }


@app.get("/api/niches/{report_id}")
def niches_read(report_id: str) -> dict[str, Any]:
    row = _read_report_by_id(report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    return {
        "report_id": row["id"],
        "generated_at": row["created_at"],
        "spec_version": row["spec_version"],
        "input": {
            "niche_keyword": row["niche_keyword"],
            "geo_scope": row["geo_scope"],
            "geo_target": row["geo_target"],
            "report_depth": row["report_depth"],
            "strategy_profile": row["strategy_profile"],
        },
        "keyword_expansion": row["keyword_expansion"],
        "metros": row["metros"],
        "meta": row["meta"],
    }
```

`HTTPException` is already imported in `api.py`; do not re-import.

- [ ] **Step 4: Run the new tests + full unit suite**

Run: `pytest tests/unit/test_api_niches.py tests/unit/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/research_agent/api.py tests/unit/test_api_niches.py
git commit -m "feat(api): add POST /api/niches/score and GET /api/niches/{id}"
```

---

## Phase 4 — Next.js wiring

### Task 10: Rewrite `/api/agent/scoring` to proxy FastAPI

**Files:**
- Modify: `apps/app/src/app/api/agent/scoring/route.ts`
- Create: `apps/app/src/app/api/agent/scoring/route.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it, vi } from "vitest";
import { POST } from "./route";

describe("POST /api/agent/scoring", () => {
  it("proxies to FastAPI and maps the response", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r1",
        opportunity_score: 72,
        classification_label: "Medium",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.score_result.opportunity_score).toBe(72);
    expect(body.score_result.classification_label).toBe("Medium");
    expect(body.report_id).toBe("r1");
  });

  it("passes dry_run=true when NEXT_PUBLIC_NICHE_DRY_RUN=1", async () => {
    process.env.NEXT_PUBLIC_NICHE_DRY_RUN = "1";
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ report_id: "r2", opportunity_score: 50,
        classification_label: "Medium", evidence: [], report: { input: { niche_keyword: "x" }}}), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    await POST(req as never);
    const sent = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(sent.dry_run).toBe(true);
    delete process.env.NEXT_PUBLIC_NICHE_DRY_RUN;
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/app && npx vitest run src/app/api/agent/scoring/route.test.ts`
Expected: FAIL — response has stub shape.

- [ ] **Step 3: Replace the route**

Rewrite `apps/app/src/app/api/agent/scoring/route.ts`:

```ts
import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const validation = validateNicheQueryInput(body);
    if (!validation.ok) {
      return NextResponse.json(
        { status: "validation_error", message: validation.message },
        { status: 400 },
      );
    }
    const dryRun = process.env.NEXT_PUBLIC_NICHE_DRY_RUN === "1";

    const upstream = await fetch(`${API_BASE}/api/niches/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        niche: body.service.trim(),
        city: body.city.trim(),
        state: (body.state ?? "").trim() || "AZ",
        strategy_profile: body.strategy_profile ?? "balanced",
        dry_run: dryRun,
      }),
    });

    if (!upstream.ok) {
      const upstreamBody = await upstream.text();
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Scoring engine did not return a result.",
          upstream_status: upstream.status,
          upstream_body: upstreamBody.slice(0, 2000),
        },
        { status: 502 },
      );
    }

    const data = await upstream.json();
    return NextResponse.json({
      query: { city: body.city.trim(), service: body.service.trim() },
      score_result: {
        opportunity_score: data.opportunity_score,
        classification_label: data.classification_label,
      },
      report_id: data.report_id,
      status: "success",
    });
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Failed to process scoring request.",
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }
}
```

- [ ] **Step 4: Run tests and unit suite**

Run: `cd apps/app && npx vitest run src/app/api/agent/scoring/`
Expected: PASS both tests.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/app/api/agent/scoring/route.ts apps/app/src/app/api/agent/scoring/route.test.ts
git commit -m "feat(app): proxy /api/agent/scoring to FastAPI /api/niches/score"
```

### Task 11: Rewrite `/api/agent/exploration` to proxy and include evidence

**Files:**
- Modify: `apps/app/src/app/api/agent/exploration/route.ts`
- Create: `apps/app/src/app/api/agent/exploration/route.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it, vi } from "vitest";
import { POST } from "./route";

describe("POST /api/agent/exploration", () => {
  it("proxies to FastAPI and returns score_result plus evidence", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r3",
        opportunity_score: 68,
        classification_label: "Medium",
        evidence: [
          { category: "demand", label: "x", value: 100, source: "M6", is_available: true },
        ],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    const req = new Request("http://localhost/api/agent/exploration", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing" }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.score_result.opportunity_score).toBe(68);
    expect(body.evidence.length).toBe(1);
    expect(body.evidence[0].source).toBe("M6");
    expect(body.status).toBe("success");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/app && npx vitest run src/app/api/agent/exploration/route.test.ts`
Expected: FAIL.

- [ ] **Step 3: Replace the route**

Rewrite `apps/app/src/app/api/agent/exploration/route.ts`:

```ts
import { NextRequest, NextResponse } from "next/server";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const validation = validateNicheQueryInput(body);
    if (!validation.ok) {
      return NextResponse.json(
        { status: "validation_error", message: validation.message },
        { status: 400 },
      );
    }
    const dryRun = process.env.NEXT_PUBLIC_NICHE_DRY_RUN === "1";

    const upstream = await fetch(`${API_BASE}/api/niches/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        niche: body.service.trim(),
        city: body.city.trim(),
        state: (body.state ?? "").trim() || "AZ",
        strategy_profile: body.strategy_profile ?? "balanced",
        dry_run: dryRun,
      }),
    });

    if (!upstream.ok) {
      const upstreamBody = await upstream.text();
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Exploration engine did not return a result.",
          upstream_status: upstream.status,
          upstream_body: upstreamBody.slice(0, 2000),
        },
        { status: 502 },
      );
    }

    const data = await upstream.json();
    return NextResponse.json({
      query: { city: body.city.trim(), service: body.service.trim() },
      score_result: {
        opportunity_score: data.opportunity_score,
        classification_label: data.classification_label,
      },
      evidence: data.evidence ?? [],
      report_id: data.report_id,
      status: (data.evidence?.length ?? 0) > 0 ? "success" : "partial_evidence",
    });
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Failed to process exploration request.",
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }
}
```

- [ ] **Step 4: Run tests**

Run: `cd apps/app && npx vitest run src/app/api/agent/exploration/`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/app/api/agent/exploration/route.ts apps/app/src/app/api/agent/exploration/route.test.ts
git commit -m "feat(app): proxy /api/agent/exploration to FastAPI with real evidence"
```

### Task 12: Delete the stub in `response-adapter.ts`

The `buildScoreResult`, `buildEvidence`, `buildStandardResponse`, `buildExplorationResponse` functions are no longer called by the API routes. Remove them so they can't be accidentally resurrected.

**Files:**
- Modify: `apps/app/src/lib/niche-finder/response-adapter.ts` (delete contents)
- Search for any remaining imports

- [ ] **Step 1: Find remaining callers**

Run: `grep -rn "response-adapter\|buildScoreResult\|buildEvidence\|buildStandardResponse\|buildExplorationResponse" apps/app/src`
Expected: only the file itself.

If any other file still imports these helpers, update that file first (replace with call to the API route or delete the unused code). Do NOT proceed to step 2 until grep is clean.

- [ ] **Step 2: Delete the adapter file**

Run: `git rm apps/app/src/lib/niche-finder/response-adapter.ts`

- [ ] **Step 3: Run type-check and unit tests**

Run: `cd apps/app && npx tsc --noEmit && npx vitest run`
Expected: PASS. If any test or type-check references the deleted helpers, fix the caller.

- [ ] **Step 4: Commit**

```bash
git add -A apps/app/src/lib/niche-finder
git commit -m "chore(app): remove hash-based score stubs; scoring now flows through FastAPI"
```

### Task 13: Loading + error UI on the exploration page

Scoring now takes ~30–60s. The existing page assumes instant responses. Add a pending state and error messaging so the user knows the system is working.

**Files:**
- Modify: `apps/app/src/app/(protected)/exploration/page.tsx`
- Modify: `apps/app/src/app/(protected)/page.tsx`

- [x] **Step 1: Identify the current fetch sites**

Run: `grep -n "fetch.*agent/scoring\|fetch.*agent/exploration" apps/app/src/app/(protected)/*.tsx apps/app/src/lib/niche-finder/*.ts`

Note the files and line numbers. For each, you'll add a pending state.

- [x] **Step 2: Add pending + error states**

In `apps/app/src/app/(protected)/exploration/page.tsx`, wherever the fetch happens (likely inside a `useEffect` or a form handler), introduce:

```tsx
const [state, setState] = useState<
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; data: ExplorationSurfaceResponse }
  | { kind: "error"; message: string }
>({ kind: "idle" });

async function runExploration(query: NicheQueryInput) {
  setState({ kind: "loading" });
  try {
    const res = await fetch("/api/agent/exploration", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(query),
    });
    const data = await res.json();
    if (!res.ok || data.status === "unavailable") {
      setState({ kind: "error", message: data.message ?? "Scoring failed." });
      return;
    }
    setState({ kind: "success", data });
  } catch (err) {
    setState({ kind: "error", message: err instanceof Error ? err.message : "Network error" });
  }
}
```

Render:

```tsx
{state.kind === "loading" && (
  <div role="status" aria-live="polite" className="rounded-md border p-4">
    Running live scoring pipeline — this takes up to a minute on first run.
  </div>
)}
{state.kind === "error" && (
  <div role="alert" className="rounded-md border border-red-400 bg-red-50 p-4 text-red-800">
    {state.message}
  </div>
)}
{state.kind === "success" && <ExplorationResults data={state.data} />}
```

For `apps/app/src/app/(protected)/page.tsx`, apply the same three-branch state machine (`idle` / `loading` / `success` / `error`) shown above, but replace the fetch call with:

```tsx
const res = await fetch("/api/agent/scoring", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(query),
});
```

and render `StandardSurfaceResponse`-shaped results (opportunity score + classification label only, no evidence list). Keep the same `role="status"` loading banner and `role="alert"` error banner as the exploration page so their behavior matches.

- [x] **Step 3: Run type-check + vitest**

Run: `cd apps/app && npx tsc --noEmit && npx vitest run`
Expected: PASS. (tsc: 6 pre-existing errors in middleware.test.ts only; vitest: 15 tests pass)

- [x] **Step 4: Commit**

```bash
git add apps/app/src/app/(protected)
git commit -m "feat(app): add loading + error UI for live niche scoring"
```
Committed as c6aa489.

---

## Phase 5 — End-to-end verification

### Task 14: Playwright E2E — dry-run mode

Dry-run keeps the test fast and free.

**Files:**
- Create: `apps/app/e2e/niche-scoring.spec.ts`

Check the existing Playwright config at `apps/app/playwright.config.ts` (should exist from PR #21) to confirm `e2e/` is the right directory. If tests live under a different folder, place the spec there.

- [ ] **Step 1: Write the spec**

```ts
import { test, expect } from "@playwright/test";

test.describe("niche scoring (dry run)", () => {
  test.beforeEach(async ({ context }) => {
    // Signed-in session fixture should already be configured by playwright.config.ts
    await context.addInitScript(() => {
      window.localStorage.setItem("NEXT_PUBLIC_NICHE_DRY_RUN", "1");
    });
  });

  test("user submits city/service and sees real evidence", async ({ page }) => {
    await page.goto("/exploration");
    await page.getByLabel(/city/i).fill("Phoenix");
    await page.getByLabel(/service/i).fill("roofing");
    await page.getByRole("button", { name: /explore/i }).click();
    await expect(page.getByRole("status")).toContainText(/running live scoring/i);
    await expect(page.getByTestId("opportunity-score")).toBeVisible({ timeout: 30_000 });
    const score = await page.getByTestId("opportunity-score").innerText();
    expect(Number(score)).toBeGreaterThanOrEqual(0);
    await expect(page.getByText(/AI Overview Penetration/i)).toBeVisible();
  });
});
```

If the existing page doesn't have `data-testid="opportunity-score"` on the score element, add it during Task 13's UI edit and update this spec accordingly.

- [ ] **Step 2: Run the Python pipeline locally**

In one terminal: `npm run dev:api` (FastAPI on port 8000).
In another: `NEXT_PUBLIC_NICHE_DRY_RUN=1 npm run dev:app` (Next.js on port 3001).

- [ ] **Step 3: Run Playwright**

Run: `cd apps/app && npx playwright test e2e/niche-scoring.spec.ts`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/app/e2e/niche-scoring.spec.ts
git commit -m "test(app): Playwright E2E for dry-run niche scoring flow"
```

### Task 15: Manual live smoke + sprint-plan update

- [ ] **Step 1: Smoke test with live APIs**

Ensure `.env.local` has `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`, `ANTHROPIC_API_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

Start `npm run dev:api` and `npm run dev:app` (no dry-run env var).
In the browser, enter a small niche/city pair (e.g. "roofing", "Phoenix"). Wait for results. Expected: real scores (not always the same) in 30–90s.

Query Supabase: the `reports` table should contain a new row. `report_keywords`, `metro_signals`, `metro_scores` should have matching rows by `report_id`.

- [ ] **Step 2: Update the sprint-plan doc**

The project CLAUDE.md instructs updating the sprint plan after each completed work chunk. Find the sprint plan (likely under `docs/` or `.claude/` — check both) and add a dated entry summarizing what was wired up in this plan.

- [ ] **Step 3: Open PR**

```bash
git push -u origin HEAD
gh pr create --title "feat: wire niche scoring end-to-end (M4-M9 + Supabase + FastAPI)" \
  --body "$(cat <<'EOF'
## Summary
- New Python orchestrator `score_niche_for_metro` sequences M4 through M9
- New FastAPI routes `POST /api/niches/score` and `GET /api/niches/{id}`
- New Supabase persistence adapter writing to `reports`, `report_keywords`, `metro_signals`, `metro_scores`
- Next.js `/api/agent/scoring` and `/api/agent/exploration` now proxy the FastAPI bridge instead of returning hash-based stubs
- UI now has loading + error states for the ~30-60s live pipeline
- Dry-run mode (`NEXT_PUBLIC_NICHE_DRY_RUN=1`) loads fixtures for UI development

## Test plan
- [ ] `pytest tests/unit/ -v` passes
- [ ] `pytest tests/integration/ -v -m integration` passes with creds
- [ ] `npx vitest run` in `apps/app` passes
- [ ] `npx playwright test e2e/niche-scoring.spec.ts` passes in dry-run mode
- [ ] Manual live smoke: submit Phoenix/roofing, confirm Supabase rows written

Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

---

## Notes for the executor

- **Order matters:** Phase 1 must land before Phase 3, Phase 3 before Phase 4. Phases 0 and 2 can land independently at any point but are easiest in the order written.
- **Cost control:** never run the live integration test in CI; keep `pytest.ini` or `tox.ini` marker config so `@pytest.mark.integration` is skipped by default.
- **Snake_case rule (CLAUDE.md):** every JSON payload at an API boundary uses snake_case keys — already followed throughout. If you add new fields, maintain it.
- **Docs sync gate (CLAUDE.md):** changes under `src/pipeline/` or `src/clients/` require updating `docs/product_breakdown.md` OR using `[docs-sync-skip]` in the commit message. The plan's commit messages currently don't include the tag — add `[docs-sync-skip]` if you don't update the product-breakdown doc in the same commit, or update the doc's M4-M9 section to reference `score_niche_for_metro` as the public pipeline entrypoint.
- **FastAPI bridge:** the user previously noted "the agent isn't working." Phase 0 surfaces the real upstream error so you can diagnose whether it's the Render instance being cold, `NEXT_PUBLIC_API_URL` misconfiguration, or something else.
- **Out of scope:** M10–M15 outreach experiment tables (`experiments`, `outreach_events`, etc.), user-scoped RLS policies, and a "recent niche scores" dashboard widget. Ship the scoring flow first; layer those on in a follow-up plan.
