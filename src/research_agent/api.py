"""FastAPI bridge exposing the research agent to the frontend.

Run with: uvicorn src.research_agent.api:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Literal

import anthropic
from fastapi import BackgroundTasks, FastAPI, HTTPException, Path as FastAPIPath, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.kb_adapter import KBKnowledgeStore
from src.clients.kb_persistence import KBPersistence
from src.clients.llm.client import LLMClient
from src.clients.strategy_repository import StrategyRepository
from src.clients.supabase_adapter import SupabaseMarketStore
from src.clients.supabase_persistence import SupabaseExploreRefreshStore, SupabasePersistence
from src.data.metro_db import Metro, MetroDB
from src.domain.services.explore_refresh_service import (
    ExploreRefreshFlags,
    ExploreRefreshService,
    QueuedExploreRefreshRun,
)
from src.domain.services.market_service import MarketService, ScoreRequest
from src.pipeline.orchestrator import score_niche_for_metro
from src.research_agent.deep_agent import run_research_session
from src.research_agent.loop.ralph_loop import LoopConfig
from src.research_agent.memory.filesystem_store import FilesystemStore
from src.research_agent.memory.graph_store import ResearchGraphStore
from src.research_agent.plugins.registry_builder import build_plugin_registry
from src.research_agent.plugins.report_plugin import REPORT_TIMESTAMP_FORMAT
from src.research_agent.places import (
    DataForSEOLocationBridge,
    MapboxPlacesError,
    PlaceSuggestion,
    close_mapbox_http_client,
    fetch_mapbox_place_suggestions,
)
from src.research_agent.recipes.registry_builder import build_recipe_registry
from src.research_agent.recipes.runner import RecipeRunner, RecipeRunnerError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_DFS_ENRICH_TIMEOUT_SECONDS = 1.5


@asynccontextmanager
async def _api_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await close_mapbox_http_client()


app = FastAPI(title="Widby Research Agent API", version="0.1.0", lifespan=_api_lifespan)


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return 400 instead of 422 for Pydantic validation errors."""
    # Pydantic v2 ctx values may be non-JSON-serializable exceptions — flatten them.
    def _safe(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_safe(i) for i in obj]
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        return str(obj)

    errors = _safe(exc.errors())
    return JSONResponse(status_code=400, content={"detail": errors})


_CORS_EXTRA = [
    o.strip()
    for o in os.environ.get("CORS_EXTRA_ORIGINS", "").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:3002",
        "https://app.thewidby.com",
    ] + _CORS_EXTRA,
    allow_origin_regex=(
        r"https://.*\.vercel\.app"
        if os.environ.get("ENVIRONMENT") != "production"
        else None
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)

_METRO_DB: MetroDB | None = None
_PLACES_DATAFORSEO_BRIDGE: DataForSEOLocationBridge | None = None
_SHARED_DFS_CLIENT: DataForSEOClient | None = None
_STRATEGY_DISCOVERY_INTERNAL_TOKEN_ENV = "STRATEGY_DISCOVERY_INTERNAL_TOKEN"


def _metro_db() -> MetroDB:
    global _METRO_DB
    if _METRO_DB is None:
        _METRO_DB = MetroDB.from_seed()
    return _METRO_DB


def _shared_dfs_client() -> DataForSEOClient | None:
    """Return the app-lifetime DataForSEO client (shared persistent cache)."""
    global _SHARED_DFS_CLIENT
    if _SHARED_DFS_CLIENT is not None:
        return _SHARED_DFS_CLIENT

    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        return None

    _SHARED_DFS_CLIENT = DataForSEOClient(login=login, password=password)
    return _SHARED_DFS_CLIENT


def _places_dataforseo_bridge() -> DataForSEOLocationBridge | None:
    """Build a cached DataForSEO bridge if credentials are configured."""
    global _PLACES_DATAFORSEO_BRIDGE
    if _PLACES_DATAFORSEO_BRIDGE is not None:
        return _PLACES_DATAFORSEO_BRIDGE

    dfs = _shared_dfs_client()
    if dfs is None:
        return None

    _PLACES_DATAFORSEO_BRIDGE = DataForSEOLocationBridge(dfs)
    return _PLACES_DATAFORSEO_BRIDGE


def _apply_places_enrichment_status(
    suggestions: list[PlaceSuggestion],
    *,
    status: str,
    reason: str | None = None,
) -> list[PlaceSuggestion]:
    for suggestion in suggestions:
        suggestion.enrichment_status = status
        suggestion.enrichment_reason = reason
    return suggestions


# ---------------------------------------------------------------------------
# Discovery service DI wiring
# ---------------------------------------------------------------------------

from src.domain.services.discovery_service import DiscoveryService  # noqa: E402
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter  # noqa: E402


class _NullMarketStore:
    """Returns empty results until a real MarketStore adapter is wired."""

    def persist_report(self, report: dict[str, Any]) -> str:
        return ""

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        return None

    def query_markets(self, query: Any) -> list:
        return []


_DISCOVERY_SERVICE: DiscoveryService | None = None


def _get_discovery_service() -> DiscoveryService:
    global _DISCOVERY_SERVICE
    if _DISCOVERY_SERVICE is None:
        persistence = SupabasePersistence()
        _DISCOVERY_SERVICE = DiscoveryService(
            market_store=StrategyRepository(persistence._client)
        )
    return _DISCOVERY_SERVICE


def _require_strategy_discovery_internal_access(request: Request) -> None:
    token = os.environ.get(_STRATEGY_DISCOVERY_INTERNAL_TOKEN_ENV)
    if not token:
        if os.environ.get("ENVIRONMENT") == "production":
            raise HTTPException(
                status_code=503,
                detail="Strategy discovery internal token is not configured.",
            )
        return

    authorization = request.headers.get("authorization", "")
    internal_token = request.headers.get("x-strategy-discovery-token", "")
    if hmac.compare_digest(authorization, f"Bearer {token}") or hmac.compare_digest(
        internal_token, token
    ):
        return

    raise HTTPException(status_code=401, detail="Strategy discovery access denied.")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for Render and monitoring."""
    return {"status": "ok"}


@app.get("/api/metros/suggest")
def metros_suggest(q: str, limit: int = 10) -> list[dict[str, Any]]:
    """Autocomplete metros by city prefix; returns highest-population matches first."""
    q_norm = q.strip().lower()
    if len(q_norm) < 2:
        return []
    clamped = max(1, min(limit, 20))

    rows: list[tuple[Metro, str]] = []
    for metro in _metro_db().all_metros():
        principal_match = next(
            (pc for pc in metro.principal_cities if pc.strip().lower().startswith(q_norm)),
            None,
        )
        if principal_match is not None:
            rows.append((metro, principal_match))
            continue
        if metro.cbsa_name.lower().startswith(q_norm):
            # Fall back to the CBSA's first principal city for the "city" label.
            display = metro.principal_cities[0] if metro.principal_cities else metro.cbsa_name
            rows.append((metro, display))

    rows.sort(key=lambda pair: pair[0].population, reverse=True)
    rows = rows[:clamped]

    return [
        {
            "cbsa_code": m.cbsa_code,
            "city": city,
            "state": m.state,
            "cbsa_name": m.cbsa_name,
            "population": m.population,
        }
        for m, city in rows
    ]


@app.get("/api/places/suggest")
async def places_suggest(
    request: Request,
    q: str,
    limit: int = 10,
    country: str | None = None,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Autocomplete places with bounded, best-effort DFS enrichment."""
    request_id = request.headers.get("x-request-id", "unknown")
    started_at = time.perf_counter()
    q_norm = q.strip()
    if len(q_norm) < 2:
        return []
    clamped = max(1, min(limit, 20))
    logger.info(
        "[%s] PLACES_SUGGEST START query=%r limit=%d",
        request_id,
        q_norm,
        clamped,
    )

    mapbox_access_token = os.environ.get("MAPBOX_ACCESS_TOKEN")
    if not mapbox_access_token:
        logger.warning("[%s] PLACES_SUGGEST ERROR reason=missing_mapbox_token", request_id)
        raise HTTPException(
            status_code=503,
            detail="Mapbox autocomplete unavailable: MAPBOX_ACCESS_TOKEN is not configured.",
        )

    try:
        mapbox_started = time.perf_counter()
        suggestions = await fetch_mapbox_place_suggestions(
            query=q_norm,
            limit=clamped,
            access_token=mapbox_access_token,
            country=country,
            language=language,
        )
        mapbox_ms = int((time.perf_counter() - mapbox_started) * 1000)
    except MapboxPlacesError as exc:
        logger.warning(
            "[%s] PLACES_SUGGEST ERROR reason=mapbox_failure detail=%s duration_ms=%d",
            request_id,
            exc,
            int((time.perf_counter() - started_at) * 1000),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        logger.error(
            "[%s] PLACES_SUGGEST ERROR reason=mapbox_unexpected duration_ms=%d",
            request_id,
            int((time.perf_counter() - started_at) * 1000),
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Mapbox autocomplete failed unexpectedly.",
        ) from None

    bridge = _places_dataforseo_bridge()
    if bridge is None:
        suggestions = _apply_places_enrichment_status(
            suggestions,
            status="not_configured",
            reason="DataForSEO credentials unavailable.",
        )
        rows = [row.to_dict() for row in suggestions]
        logger.info(
            "[%s] PLACES_SUGGEST DONE rows=%d enrichment_status=%s mapbox_ms=%d duration_ms=%d",
            request_id,
            len(rows),
            "not_configured",
            mapbox_ms,
            int((time.perf_counter() - started_at) * 1000),
        )
        return rows

    try:
        suggestions = await asyncio.wait_for(
            bridge.enrich(suggestions),
            timeout=_DFS_ENRICH_TIMEOUT_SECONDS,
        )
        for suggestion in suggestions:
            if suggestion.dataforseo_location_code is not None:
                suggestion.enrichment_status = "enriched"
                suggestion.enrichment_reason = None
            else:
                suggestion.enrichment_status = "mapbox_only"
                suggestion.enrichment_reason = "No confident DataForSEO match."
    except TimeoutError:
        logger.warning("DFS place enrichment timed out q=%r", q_norm)
        suggestions = _apply_places_enrichment_status(
            suggestions,
            status="timeout",
            reason="DataForSEO enrichment timed out.",
        )
    except Exception:
        logger.warning("DFS place enrichment degraded unexpectedly", exc_info=True)
        suggestions = _apply_places_enrichment_status(
            suggestions,
            status="degraded",
            reason="DataForSEO enrichment failed unexpectedly.",
        )

    rows = [row.to_dict() for row in suggestions]
    logger.info(
        "[%s] PLACES_SUGGEST DONE rows=%d mapbox_ms=%d duration_ms=%d",
        request_id,
        len(rows),
        mapbox_ms,
        int((time.perf_counter() - started_at) * 1000),
    )
    return rows


RUNS_DIR = Path(os.environ.get("RESEARCH_RUNS_DIR", "research_runs"))
GRAPH_PATH = Path(os.environ.get("RESEARCH_GRAPH_PATH", "research_graph.json"))


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SessionRequest(BaseModel):
    scoring_results: dict[str, Any] | None = None
    max_iterations: int = 10
    budget_limit_usd: float = 50.0
    run_id: str | None = None


class ChatRequest(BaseModel):
    message: str
    run_id: str | None = None


class ExplorationFollowupRequest(BaseModel):
    city: str
    service: str
    question: str


class NicheScoreRequest(BaseModel):
    niche: str
    city: str
    state: str | None = None
    place_id: str | None = None
    dataforseo_location_code: int | None = None
    metadata_source: str = "typed"
    strategy_profile: str = "balanced"
    dry_run: bool = False
    owner_account_id: str | None = None
    created_by_user_id: str | None = None

    @field_validator("niche", "city")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must be non-empty")
        return v

    @field_validator("state")
    @classmethod
    def _normalize_state(cls, v: str | None) -> str | None:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None

    @field_validator("place_id")
    @classmethod
    def _normalize_place_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None

    @field_validator("dataforseo_location_code")
    @classmethod
    def _validate_dataforseo_location_code(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("must be a positive integer")
        return v

    @field_validator("metadata_source")
    @classmethod
    def _validate_metadata_source(cls, v: str) -> str:
        normalized = v.strip().lower()
        allowed = {"typed", "mapbox_selected", "recent_history", "fallback_cbsa"}
        if normalized not in allowed:
            raise ValueError("metadata_source must be one of typed|mapbox_selected|recent_history|fallback_cbsa")
        return normalized

    @field_validator("owner_account_id", "created_by_user_id")
    @classmethod
    def _normalize_uuid_context(cls, v: str | None) -> str | None:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            return None
        try:
            uuid.UUID(trimmed)
        except ValueError as exc:
            raise ValueError("must be a valid UUID") from exc
        return trimmed


class ExploreRefreshFlagsPayload(BaseModel):
    force: bool = False
    dry_run: bool = False
    strategy_profile: Literal["balanced", "growth", "defensive"] = "balanced"
    max_items: int = Field(default=50, ge=1, le=500)
    concurrency: int = Field(default=2, ge=1, le=5)


class ExploreRefreshRunRequest(BaseModel):
    scope: Literal["selected", "visible", "stale", "all"]
    target_ids: list[str] = Field(default_factory=list)
    report_ids: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    flags: ExploreRefreshFlagsPayload = Field(default_factory=ExploreRefreshFlagsPayload)


StrategyId = Literal["easy_win", "gbp_blitz", "keyword_hijack", "expand_conquer", "cash_cow"]


class StrategyRunTarget(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cbsa_code: str = Field(min_length=1)
    niche_normalized: str = Field(min_length=1)
    niche_keyword: str | None = Field(default=None, min_length=1)
    primary_keyword: str | None = Field(default=None, min_length=1)


class StrategyRunRequest(BaseModel):
    strategy_id: StrategyId
    mode: Literal["cached", "fresh"] = "cached"
    targets: list[StrategyRunTarget] = Field(default_factory=list)
    quota_consumed: int = Field(default=0, ge=0, le=1)
    account_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID | None = None
    city: str | None = None
    state: str | None = None
    service: str | None = None
    primary_keyword: str | None = None
    reference_city_id: str | None = None
    ai_resilience_filter: bool = False
    limit: int = Field(default=50, ge=1, le=200)

    @model_validator(mode="after")
    def _fresh_runs_need_targets(self) -> "StrategyRunRequest":
        if (
            self.mode == "fresh"
            and not self.targets
            and not (self.city and self.service)
        ):
            raise ValueError("Fresh strategy runs require at least one target.")
        return self


# ---------------------------------------------------------------------------
# MarketService singleton (replaces per-request client construction)
# ---------------------------------------------------------------------------

_MARKET_SERVICE: MarketService | None = None
_EXPLORE_REFRESH_SERVICE: ExploreRefreshService | None = None
_STRATEGY_REPOSITORY: StrategyRepository | None = None


def _build_market_service() -> MarketService:
    dfs = _shared_dfs_client()
    llm: Any = None
    try:
        llm = LLMClient()
    except Exception:
        logger.warning("LLMClient unavailable; only dry-run scoring will work")

    store: Any = None
    kb: Any = None
    try:
        store = SupabaseMarketStore(SupabasePersistence())
    except Exception:
        logger.warning("SupabaseMarketStore unavailable; persistence will fail")
    try:
        kb = KBKnowledgeStore(KBPersistence())
    except Exception:
        logger.warning("KBKnowledgeStore unavailable; KB operations will fail")

    return MarketService(
        pipeline_fn=score_niche_for_metro,
        dfs_client=dfs,
        llm_client=llm,
        market_store=store,
        knowledge_store=kb,
    )


def _market_service() -> MarketService:
    global _MARKET_SERVICE
    if _MARKET_SERVICE is None:
        _MARKET_SERVICE = _build_market_service()
    return _MARKET_SERVICE


def _get_explore_refresh_service() -> ExploreRefreshService:
    global _EXPLORE_REFRESH_SERVICE
    if _EXPLORE_REFRESH_SERVICE is None:
        persistence = SupabasePersistence()
        store = SupabaseExploreRefreshStore(client=persistence._client)
        _EXPLORE_REFRESH_SERVICE = ExploreRefreshService(
            store=store,
            market_service=_market_service(),
        )
    return _EXPLORE_REFRESH_SERVICE


def _get_strategy_repository() -> StrategyRepository:
    global _STRATEGY_REPOSITORY
    if _STRATEGY_REPOSITORY is None:
        persistence = SupabasePersistence()
        _STRATEGY_REPOSITORY = StrategyRepository(persistence._client)
    return _STRATEGY_REPOSITORY


def _read_report_by_id(report_id: str) -> dict[str, Any] | None:
    """Read a report by ID. Used by GET /api/niches/{report_id}."""
    svc = _market_service()
    if svc._store is not None:
        return svc._store.read_report(report_id)
    import os
    from supabase import create_client
    client = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    res = client.table("reports").select("*").eq("id", report_id).limit(1).execute()
    return res.data[0] if res.data else None


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------


@app.post("/api/sessions")
def start_session(req: SessionRequest) -> dict[str, Any]:
    """Start a new research session."""
    scoring = req.scoring_results or _demo_scoring_results()
    config = LoopConfig(
        max_iterations=req.max_iterations,
        budget_limit_usd=req.budget_limit_usd,
        base_dir=str(RUNS_DIR),
    )
    if req.run_id:
        config.run_id = req.run_id

    result = run_research_session(
        scoring_results=scoring,
        config=config,
        graph_path=str(GRAPH_PATH),
    )
    return {
        "run_id": config.run_id,
        "report": result.get("report", ""),
        "recommendations": result.get("recommendations", []),
        "outcome": result.get("outcome"),
    }


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    """List all session run IDs with basic summaries."""
    if not RUNS_DIR.exists():
        return []
    sessions: list[dict[str, Any]] = []
    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        summary: dict[str, Any] = {"run_id": run_dir.name}
        state_path = run_dir / "loop_state.json"
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
            summary["completed"] = state.get("completed", False)
            summary["stop_reason"] = state.get("stop_reason")
            summary["iterations_completed"] = state.get("iterations_completed", 0)
            summary["total_cost_usd"] = state.get("total_cost_usd", 0)
            summary["validated_count"] = state.get("validated_count", 0)
            summary["invalidated_count"] = state.get("invalidated_count", 0)
            summary["saved_at"] = state.get("saved_at")
        sessions.append(summary)
    return sessions


@app.get("/api/sessions/{run_id}")
def get_session(run_id: str) -> dict[str, Any]:
    """Get full session detail: outcome, progress, recommendations."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(404, f"Run {run_id} not found")

    fs = FilesystemStore(run_id=run_id, base_dir=str(RUNS_DIR))
    result: dict[str, Any] = {"run_id": run_id}

    state = fs.load_loop_state()
    if state:
        result["outcome"] = state

    result["progress"] = fs.read_progress()
    result["backlog"] = fs.load_backlog()
    result["experiment_ids"] = fs.list_experiment_results()
    result["snapshots"] = fs.list_snapshots()

    return result


# ---------------------------------------------------------------------------
# Chat endpoint (simplified for V1)
# ---------------------------------------------------------------------------


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    """Process a chat message. V1 runs hypothesis generation from the message.

    In a full implementation this would stream responses from the Deep Agent.
    """
    from src.research_agent.hypothesis.generator import generate_novel_hypothesis

    hypothesis = generate_novel_hypothesis(req.message)
    return {
        "response": (
            f"I've created a novel hypothesis based on your observation:\n\n"
            f"**{hypothesis['title']}**\n\n"
            f"{hypothesis['description']}\n\n"
            f"Target proxy: {hypothesis['target_proxy']}\n"
            f"Priority: {hypothesis['priority']}\n"
            f"Status: {hypothesis['status']}"
        ),
        "hypothesis": hypothesis,
        "tool_calls": [
            {
                "tool": "propose_novel_hypothesis",
                "input": req.message,
                "output": hypothesis,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Exploration follow-up endpoint
# ---------------------------------------------------------------------------


@app.post("/api/exploration/followup")
def exploration_followup(req: ExplorationFollowupRequest) -> dict[str, Any]:
    """Run a plugin-backed exploration follow-up query.

    Uses ClaudeAgent.run_exploration_followup to invoke approved scoring/search
    plugin tools while preserving the active city/service context.
    """
    from src.research_agent.agent import _build_registry
    from src.research_agent.agent.claude_agent import ClaudeAgent

    try:
        registry = _build_registry()
        agent = ClaudeAgent(registry=registry)
        result = agent.run_exploration_followup(
            city=req.city.strip(),
            service=req.service.strip(),
            question=req.question.strip(),
        )
        return result
    except Exception:
        logger.error("Exploration follow-up failed", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Exploration follow-up failed. Try a simpler question.",
        )


# ---------------------------------------------------------------------------
# Niche scoring endpoints
# ---------------------------------------------------------------------------


@app.post("/api/niches/score")
async def niches_score(req: NicheScoreRequest, request: Request) -> dict[str, Any]:
    """Run M4-M9 pipeline for a (niche, city, state) pair and persist the report."""
    request_id = request.headers.get("x-request-id")
    started_at = time.perf_counter()
    logger.info(
        "[%s] NICHES_SCORE START niche=%r city=%r metadata_source=%s dry_run=%s",
        request_id or "unknown",
        req.niche,
        req.city,
        req.metadata_source,
        req.dry_run,
    )
    try:
        score_request = ScoreRequest(
            niche=req.niche,
            city=req.city,
            state=req.state,
            place_id=req.place_id,
            dataforseo_location_code=req.dataforseo_location_code,
            metadata_source=req.metadata_source,
            request_id=request_id,
            strategy_profile=req.strategy_profile,
            dry_run=req.dry_run,
            owner_account_id=req.owner_account_id,
            created_by_user_id=req.created_by_user_id,
        )
        result = await _market_service().score(score_request)
        logger.info(
            "[%s] NICHES_SCORE DONE report_id=%s opportunity=%s duration_ms=%d",
            request_id or "unknown",
            result.report_id,
            result.opportunity_score,
            int((time.perf_counter() - started_at) * 1000),
        )
        return result.to_api_response()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception(
            "niches_score pipeline failed request_id=%s niche=%r city=%r metadata_source=%s",
            request_id,
            req.niche,
            req.city,
            req.metadata_source,
        )
        raise HTTPException(
            status_code=500, detail="Scoring pipeline failed unexpectedly"
        )


@app.get("/api/niches/{report_id}")
def niches_read(report_id: str) -> dict[str, Any]:
    """Read a persisted niche report from Supabase by ID."""
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


# ---------------------------------------------------------------------------
# Explore refresh endpoints
# ---------------------------------------------------------------------------


def _explore_refresh_service_or_503() -> ExploreRefreshService:
    try:
        return _get_explore_refresh_service()
    except RuntimeError as exc:
        logger.warning("Explore refresh service unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Explore refresh service unavailable: {exc}",
        ) from exc


def _explore_refresh_flags(payload: ExploreRefreshFlagsPayload) -> ExploreRefreshFlags:
    return ExploreRefreshFlags(
        force=payload.force,
        dry_run=payload.dry_run,
        strategy_profile=payload.strategy_profile,
        max_items=payload.max_items,
        concurrency=payload.concurrency,
    )


def _queued_refresh_response(result: str | dict[str, Any] | QueuedExploreRefreshRun) -> dict[str, str]:
    if isinstance(result, QueuedExploreRefreshRun):
        run_id = result.run_id
    elif isinstance(result, dict):
        run_id = result.get("run_id")
    else:
        run_id = result
    if not run_id:
        raise RuntimeError("Explore refresh service returned no run_id")
    return {"run_id": str(run_id), "status": "queued"}


async def _execute_explore_refresh_run(
    service: ExploreRefreshService,
    queued_run: QueuedExploreRefreshRun,
) -> None:
    try:
        await service.execute_queued_run(queued_run)
    except Exception:
        logger.exception("Explore refresh background run failed run_id=%s", queued_run.run_id)


@app.post("/api/explore/refresh/runs")
async def create_explore_refresh_run(
    payload: ExploreRefreshRunRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Queue a manual Explore cache refresh run."""
    service = _explore_refresh_service_or_503()
    flags = _explore_refresh_flags(payload.flags)
    try:
        targets = service.resolve_manual_targets(
            scope=payload.scope,
            target_ids=payload.target_ids,
            report_ids=payload.report_ids,
            filters=payload.filters,
            flags=flags,
        )
        queued_run = service.queue_selected_targets(
            targets,
            flags=flags,
            requested_by=None,
            now=datetime.now(timezone.utc),
            scope=payload.scope,
        )
        background_tasks.add_task(_execute_explore_refresh_run, service, queued_run)
        return _queued_refresh_response(queued_run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Explore refresh run failed")
        raise HTTPException(
            status_code=500,
            detail=f"Explore refresh run failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Explore refresh run failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail="Explore refresh run failed unexpectedly",
        ) from exc


@app.post("/api/explore/refresh/due")
async def refresh_due_explore_targets(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Queue refreshes for due Explore cache targets."""
    expected_secret = os.environ.get("EXPLORE_REFRESH_CRON_SECRET")
    if not expected_secret:
        raise HTTPException(
            status_code=503,
            detail="Explore refresh cron secret is not configured",
        )
    if request.headers.get("x-cron-secret") != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    service = _explore_refresh_service_or_503()
    try:
        queued_run = service.queue_due_targets(
            now=datetime.now(timezone.utc),
            flags=ExploreRefreshFlags(),
        )
        background_tasks.add_task(_execute_explore_refresh_run, service, queued_run)
        return _queued_refresh_response(queued_run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Explore due refresh failed")
        raise HTTPException(
            status_code=500,
            detail=f"Explore due refresh failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Explore due refresh failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail="Explore due refresh failed unexpectedly",
        ) from exc


@app.get("/api/explore/refresh/runs/{run_id}")
def get_explore_refresh_run(run_id: str) -> dict[str, Any]:
    """Return Explore refresh run status and items."""
    service = _explore_refresh_service_or_503()
    try:
        return service.get_run_status(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Explore refresh status lookup failed run_id=%s", run_id)
        raise HTTPException(
            status_code=500,
            detail=f"Explore refresh status lookup failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Explore refresh status lookup failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail="Explore refresh status lookup failed unexpectedly",
        ) from exc


# ---------------------------------------------------------------------------
# Graph endpoints
# ---------------------------------------------------------------------------


@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    """Return the full knowledge graph for visualization."""
    if not GRAPH_PATH.exists():
        return {"nodes": [], "edges": [], "summary": {"total_nodes": 0, "total_edges": 0}}

    graph = ResearchGraphStore(persist_path=str(GRAPH_PATH))
    nodes = graph.list_nodes()
    all_edges: list[dict[str, Any]] = []

    for node in nodes:
        edges = graph.get_edges(node.id, direction="outgoing")
        for e in edges:
            all_edges.append(e.to_dict())

    return {
        "nodes": [n.to_dict() for n in nodes],
        "edges": all_edges,
        "summary": graph.export_summary(),
    }


@app.get("/api/graph/{node_id}/neighborhood")
def get_neighborhood(node_id: str, depth: int = 2) -> dict[str, Any]:
    """Get neighborhood of a graph node."""
    if not GRAPH_PATH.exists():
        raise HTTPException(404, "Graph not initialized")

    graph = ResearchGraphStore(persist_path=str(GRAPH_PATH))
    center = graph.get_node(node_id)
    if not center:
        raise HTTPException(404, f"Node {node_id} not found")

    neighbors = graph.neighborhood(node_id, max_depth=depth)
    edges = graph.get_edges(node_id, direction="both")

    return {
        "center": center.to_dict(),
        "neighbors": [n.to_dict() for n in neighbors],
        "edges": [e.to_dict() for e in edges],
    }


# ---------------------------------------------------------------------------
# Experiment endpoints
# ---------------------------------------------------------------------------


@app.get("/api/experiments/{run_id}")
def get_experiments(run_id: str) -> list[dict[str, Any]]:
    """List experiment results for a run."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(404, f"Run {run_id} not found")

    fs = FilesystemStore(run_id=run_id, base_dir=str(RUNS_DIR))
    results: list[dict[str, Any]] = []
    for exp_id in fs.list_experiment_results():
        data = fs.load_experiment_result(exp_id)
        if data:
            data["experiment_id"] = exp_id
            results.append(data)
    return results


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


# Path-safe identifier: letters, digits, underscore, hyphen. Rejects "..",
# "/", and anything that could escape the reports root.
_SAFE_ID_PATTERN: str = r"^[A-Za-z0-9_-]+$"
_SAFE_ID_RE = re.compile(_SAFE_ID_PATTERN)


class ReportRequest(BaseModel):
    recipe_id: str
    inputs: dict[str, Any]
    run_id: str | None = None

    @field_validator("recipe_id")
    @classmethod
    def _recipe_id_safe(cls, v: str) -> str:
        if not _SAFE_ID_RE.match(v):
            raise ValueError(
                "recipe_id must contain only letters, digits, '-', or '_'"
            )
        return v

    @field_validator("run_id")
    @classmethod
    def _run_id_safe(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _SAFE_ID_RE.match(v):
            raise ValueError(
                "run_id must contain only letters, digits, '-', or '_'"
            )
        return v


class ReportResponse(BaseModel):
    report_id: str
    recipe_id: str
    report_path: str
    bytes: int
    cost_usd: float
    rounds_used: int
    status: str
    run_id: str


class ReportListItem(BaseModel):
    report_id: str
    recipe_id: str
    run_id: str
    created_at: str
    bytes: int


class ReportListResponse(BaseModel):
    reports: list[ReportListItem]


def _ensure_path_under(child: Path, parent: Path) -> None:
    """Raise HTTPException(400) if *child* is not a subpath of *parent*.

    Both paths are resolved first. Prevents ``../`` escapes and absolute-path
    arguments from writing outside the reports root.
    """
    try:
        child_resolved = child.resolve()
        parent_resolved = parent.resolve()
    except OSError as exc:
        raise HTTPException(400, f"Invalid report path: {exc}") from exc

    try:
        child_resolved.relative_to(parent_resolved)
    except ValueError as exc:
        raise HTTPException(
            400,
            f"Report output path {child_resolved} is not under {parent_resolved}",
        ) from exc


def _parse_report_filename(stem: str) -> tuple[str, str]:
    """Split ``{recipe_id}_{timestamp}`` into ``(recipe_id, created_at_iso)``.

    Mirrors the filename convention produced by :class:`ReportPlugin` via
    :data:`REPORT_TIMESTAMP_FORMAT`. Returns the timestamp in ISO-8601
    (``%Y-%m-%dT%H:%M:%SZ``). Unrecognised formats fall back to
    ``(stem, "")``.
    """
    if "_" not in stem:
        return stem, ""
    recipe_id, timestamp = stem.rsplit("_", 1)
    try:
        parsed = datetime.strptime(timestamp, REPORT_TIMESTAMP_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return recipe_id, ""
    return recipe_id, parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.post("/api/reports", response_model=ReportResponse)
def create_report(req: ReportRequest) -> ReportResponse:
    """Run a recipe end-to-end and return the rendered report metadata."""
    recipe_registry = build_recipe_registry()
    plugin_registry, report_plugin = build_plugin_registry()

    try:
        recipe = recipe_registry.get(req.recipe_id)
    except KeyError as exc:
        raise HTTPException(404, f"Unknown recipe: '{req.recipe_id}'") from exc

    run_id = req.run_id or str(uuid.uuid4())[:8]
    output_dir = RUNS_DIR / run_id / "reports"

    # Validate path containment BEFORE creating any directories so a crafted
    # run_id can't pre-create a directory outside the reports root even if
    # _ensure_path_under later rejects the write.
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_path_under(output_dir, RUNS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        anthropic_client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
    except ValueError as exc:
        logger.warning("Anthropic client construction failed: %s", exc)
        raise HTTPException(400, f"Anthropic client error: {exc}") from exc

    runner = RecipeRunner(
        plugin_registry,
        report_plugin=report_plugin,
        anthropic_client=anthropic_client,
    )

    try:
        result = runner.run(recipe, req.inputs, output_dir)
    except RecipeRunnerError as exc:
        logger.warning("Recipe runner error for '%s': %s", req.recipe_id, exc)
        raise HTTPException(422, str(exc)) from exc
    except ValueError as exc:
        logger.warning("Invalid recipe input for '%s': %s", req.recipe_id, exc)
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error running recipe '%s'", req.recipe_id)
        raise HTTPException(500, f"Unexpected recipe failure: {exc}") from exc

    report_path = Path(result["report_path"])
    report_id = report_path.stem

    return ReportResponse(
        report_id=report_id,
        recipe_id=recipe.recipe_id,
        report_path=str(report_path),
        bytes=int(result["bytes"]),
        cost_usd=float(result["cost_usd"]),
        rounds_used=int(result["rounds_used"]),
        status=str(result["status"]),
        run_id=run_id,
    )


@app.get("/api/reports", response_model=ReportListResponse)
def list_reports() -> ReportListResponse:
    """List all reports across every run in ``RUNS_DIR``."""
    if not RUNS_DIR.exists():
        return ReportListResponse(reports=[])

    items: list[ReportListItem] = []
    for run_dir in RUNS_DIR.iterdir():
        if not run_dir.is_dir():
            continue
        reports_dir = run_dir / "reports"
        if not reports_dir.is_dir():
            continue
        for report_path in reports_dir.glob("*.html"):
            if not report_path.is_file():
                continue
            stem = report_path.stem
            recipe_id, created_at = _parse_report_filename(stem)
            try:
                byte_size = report_path.stat().st_size
            except OSError:
                continue
            items.append(
                ReportListItem(
                    report_id=stem,
                    recipe_id=recipe_id,
                    run_id=run_dir.name,
                    created_at=created_at,
                    bytes=byte_size,
                )
            )

    items.sort(key=lambda it: it.created_at, reverse=True)
    return ReportListResponse(reports=items)


@app.get("/api/reports/{run_id}/{report_id}")
def get_report(
    run_id: str = FastAPIPath(..., pattern=_SAFE_ID_PATTERN),
    report_id: str = FastAPIPath(..., pattern=_SAFE_ID_PATTERN),
) -> dict[str, Any]:
    """Return a single report's metadata plus its HTML contents."""
    report_path = RUNS_DIR / run_id / "reports" / f"{report_id}.html"

    # Containment is checked BEFORE any filesystem access so a crafted
    # identifier can't cause is_file() on a path outside the reports root.
    _ensure_path_under(report_path, RUNS_DIR)

    if not report_path.is_file():
        raise HTTPException(
            404, f"Report '{report_id}' not found for run '{run_id}'"
        )

    recipe_id, created_at = _parse_report_filename(report_id)
    html = report_path.read_text(encoding="utf-8")
    return {
        "report_id": report_id,
        "run_id": run_id,
        "recipe_id": recipe_id,
        "created_at": created_at,
        "bytes": report_path.stat().st_size,
        "html": html,
    }


@app.get("/api/reports/{run_id}/{report_id}/download")
def download_report(
    run_id: str = FastAPIPath(..., pattern=_SAFE_ID_PATTERN),
    report_id: str = FastAPIPath(..., pattern=_SAFE_ID_PATTERN),
) -> FileResponse:
    """Return the raw HTML file for a report."""
    report_path = RUNS_DIR / run_id / "reports" / f"{report_id}.html"

    _ensure_path_under(report_path, RUNS_DIR)

    if not report_path.is_file():
        raise HTTPException(
            404, f"Report '{report_id}' not found for run '{run_id}'"
        )
    return FileResponse(
        path=str(report_path),
        media_type="text/html",
        filename=f"{report_id}.html",
    )


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------


def _demo_scoring_results() -> dict[str, Any]:
    return {
        "metros": [
            {
                "cbsa_code": "38060",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "scores": {
                    "demand": 72, "organic_competition": 45,
                    "local_competition": 58, "monetization": 81,
                    "ai_resilience": 92, "opportunity": 71,
                },
            },
            {
                "cbsa_code": "47900",
                "cbsa_name": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
                "scores": {
                    "demand": 85, "organic_competition": 30,
                    "local_competition": 35, "monetization": 78,
                    "ai_resilience": 88, "opportunity": 62,
                },
            },
            {
                "cbsa_code": "12060",
                "cbsa_name": "Atlanta-Sandy Springs-Alpharetta, GA",
                "scores": {
                    "demand": 68, "organic_competition": 55,
                    "local_competition": 62, "monetization": 70,
                    "ai_resilience": 90, "opportunity": 69,
                },
            },
        ]
    }


# ---------------------------------------------------------------------------
# Discovery & Lens endpoints
# ---------------------------------------------------------------------------


class DiscoverRequest(BaseModel):
    """Request body for /api/discover."""

    lens_id: str = "balanced"
    primary_keyword: str | None = None
    city_filters: list[dict[str, Any]] = Field(default_factory=list)
    service_filters: list[dict[str, Any]] = Field(default_factory=list)
    portfolio_market_ids: list[str] | None = None
    reference_city_id: str | None = None
    ai_resilience_filter: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


@app.get("/api/strategies")
async def list_strategies() -> dict[str, Any]:
    """List strategy discovery catalog entries and global modifiers."""
    from src.domain.lenses import get_lens

    strategy_specs = [
        ("easy_win", "launch", "city_service"),
        ("gbp_blitz", "launch", "city_service"),
        ("keyword_hijack", "launch", "city_service_keyword"),
        ("expand_conquer", "launch", "reference_city_service"),
        ("cash_cow", "phase_2", "cached_scan"),
    ]

    return {
        "strategies": [
            {
                "strategy_id": strategy_id,
                "name": get_lens(strategy_id).name,
                "description": get_lens(strategy_id).description,
                "status": phase,
                "input_shape": input_shape,
            }
            for strategy_id, phase, input_shape in strategy_specs
        ],
        "global_modifiers": [
            {
                "modifier_id": "ai_resilience",
                "name": "AI Resilience",
                "behavior": "warn_not_hide",
            }
        ],
    }


@app.post("/api/strategy-runs")
async def create_strategy_run(req: StrategyRunRequest, request: Request) -> dict[str, Any]:
    """Create a strategy discovery run and queue fresh target fanout."""
    _require_strategy_discovery_internal_access(request)
    target_count = len(req.targets)
    if req.mode == "fresh" and target_count > 100:
        raise HTTPException(
            status_code=400,
            detail="Fresh strategy runs are capped at 100 city-service pairs.",
        )

    run_id = str(uuid.uuid4())
    status = "queued" if req.mode == "fresh" else "succeeded"
    payload = {
        "id": run_id,
        "account_id": str(req.account_id) if req.account_id else None,
        "created_by_user_id": str(req.created_by_user_id) if req.created_by_user_id else None,
        "strategy_id": req.strategy_id,
        "mode": req.mode,
        "status": status,
        "input_payload": {
            "targets": [target.model_dump() for target in req.targets],
            "city": req.city,
            "state": req.state,
            "service": req.service,
            "primary_keyword": req.primary_keyword,
            "reference_city_id": req.reference_city_id,
            "ai_resilience_filter": req.ai_resilience_filter,
            "limit": req.limit,
        },
        "result_count": target_count if req.mode == "cached" else 0,
        "quota_consumed": req.quota_consumed if req.mode == "fresh" else 0,
    }
    try:
        created = _get_strategy_repository().create_run(payload)
    except Exception as exc:
        logger.warning("Strategy run store unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Strategy run store unavailable.",
        ) from exc

    return {
        "run_id": str(created.get("id") or run_id),
        "strategy_id": req.strategy_id,
        "mode": req.mode,
        "status": str(created.get("status") or status),
        "target_count": target_count,
    }


@app.post("/api/discover")
async def discover(req: DiscoverRequest, request: Request) -> dict[str, Any]:
    """Multi-market discovery — filters, lenses, ranking."""
    _require_strategy_discovery_internal_access(request)

    if req.portfolio_market_ids:
        raise HTTPException(
            status_code=400,
            detail="portfolio_market_ids not yet supported (Phase 7)",
        )

    from src.domain.lenses import get_lens, is_discoverable_lens

    if not is_discoverable_lens(req.lens_id):
        raise HTTPException(
            status_code=400,
            detail=f"Lens '{req.lens_id}' is not available for discovery",
        )
    lens = get_lens(req.lens_id)

    query = MarketQuery(
        city_filters=[
            CityFilter(f["field"], f["operator"], f["value"])
            for f in req.city_filters
        ],
        service_filters=[
            ServiceFilter(f["field"], f["operator"], f["value"])
            for f in req.service_filters
        ],
        lens=lens,
        reference_city_id=req.reference_city_id,
        primary_keyword=req.primary_keyword,
        ai_resilience_filter=req.ai_resilience_filter,
        limit=req.limit,
        offset=req.offset,
    )

    svc = _get_discovery_service()
    results = await svc.discover(query)

    return {
        "markets": [
            {
                "rank": r.rank,
                "opportunity_score": round(r.opportunity_score, 1),
                "lens_id": r.lens_id,
                "city": {
                    "city_id": r.market.city.city_id,
                    "name": r.market.city.name,
                    "state": r.market.city.state,
                    "population": r.market.city.population,
                },
                "service": {
                    "service_id": r.market.service.service_id,
                    "name": r.market.service.name,
                },
                "score_breakdown": r.score_breakdown,
                "strategy_evidence": r.strategy_evidence,
                "warnings": r.warnings,
            }
            for r in results
        ],
        "total": len(results),
        "lens": {
            "lens_id": lens.lens_id,
            "name": lens.name,
            "description": lens.description,
        },
        "query": {
            "primary_keyword": req.primary_keyword,
            "city_filters": req.city_filters,
            "service_filters": req.service_filters,
            "reference_city_id": req.reference_city_id,
            "ai_resilience_filter": req.ai_resilience_filter,
            "limit": req.limit,
            "offset": req.offset,
        },
    }


@app.get("/api/lenses")
async def list_lenses() -> dict[str, Any]:
    """List all available scoring lenses."""
    from src.domain.lenses import available_lenses

    return {
        "lenses": [
            {
                "lens_id": lens.lens_id,
                "name": lens.name,
                "description": lens.description,
                "weights": lens.weights,
                "filters": [
                    {"signal": f.signal, "operator": f.operator, "value": f.value}
                    for f in lens.filters
                ],
            }
            for lens in available_lenses()
        ]
    }
