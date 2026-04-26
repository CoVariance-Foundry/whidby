"""FastAPI bridge exposing the research agent to the frontend.

Run with: uvicorn src.research_agent.api:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
from fastapi import FastAPI, HTTPException, Path as FastAPIPath, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.kb_persistence import KBPersistence
from src.data.metro_db import Metro, MetroDB
from src.clients.llm.client import LLMClient
from src.clients.supabase_persistence import SupabasePersistence
from src.pipeline.canonical_key import resolve_canonical_key
from src.pipeline.feedback_logger import log_feedback
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
    fetch_mapbox_place_suggestions,
)
from src.research_agent.recipes.registry_builder import build_recipe_registry
from src.research_agent.recipes.runner import RecipeRunner, RecipeRunnerError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Widby Research Agent API", version="0.1.0")


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
    q: str,
    limit: int = 10,
    country: str | None = None,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Autocomplete places via Mapbox and bridge best-effort DataForSEO location codes."""
    q_norm = q.strip()
    if len(q_norm) < 2:
        return []
    clamped = max(1, min(limit, 20))

    mapbox_access_token = os.environ.get("MAPBOX_ACCESS_TOKEN")
    if not mapbox_access_token:
        raise HTTPException(
            status_code=503,
            detail="Mapbox autocomplete unavailable: MAPBOX_ACCESS_TOKEN is not configured.",
        )

    try:
        suggestions = await fetch_mapbox_place_suggestions(
            query=q_norm,
            limit=clamped,
            access_token=mapbox_access_token,
            country=country,
            language=language,
        )
    except MapboxPlacesError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        logger.error("Unexpected Mapbox places autocomplete failure", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Mapbox autocomplete failed unexpectedly.",
        ) from None

    return [row.to_dict() for row in suggestions]


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
    strategy_profile: str = "balanced"
    dry_run: bool = False

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


# ---------------------------------------------------------------------------
# Niche scoring helpers (patched in tests)
# ---------------------------------------------------------------------------


def _persist_report(report: dict[str, Any]) -> str:
    return SupabasePersistence().persist_report(report)


def _read_report_by_id(report_id: str) -> dict[str, Any] | None:
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
async def niches_score(req: NicheScoreRequest) -> dict[str, Any]:
    """Run M4-M9 pipeline for a (niche, city, state) pair and persist the report."""
    import time as _time

    request_id = str(uuid.uuid4())
    handler_start = _time.monotonic()
    logger.info(
        "niches_score START request_id=%s niche=%r city=%r state=%r dry_run=%s",
        request_id, req.niche, req.city, req.state, req.dry_run,
    )

    canonical = resolve_canonical_key(
        niche=req.niche,
        city=req.city,
        state=req.state,
        place_id=req.place_id,
        dataforseo_location_code=req.dataforseo_location_code,
    )
    input_hash = canonical.input_hash(req.strategy_profile)

    dfs: DataForSEOClient | None = None
    try:
        if req.dry_run:
            result = await score_niche_for_metro(
                niche=req.niche, city=req.city, state=req.state,
                place_id=req.place_id,
                dataforseo_location_code=req.dataforseo_location_code,
                strategy_profile=req.strategy_profile,
                llm_client=None, dataforseo_client=None, dry_run=True,
                request_id=request_id,
            )
        else:
            dfs = _shared_dfs_client()
            if dfs is None:
                import os
                dfs = DataForSEOClient(
                    login=os.environ["DATAFORSEO_LOGIN"],
                    password=os.environ["DATAFORSEO_PASSWORD"],
                )
            llm = LLMClient()
            result = await score_niche_for_metro(
                niche=req.niche, city=req.city, state=req.state,
                place_id=req.place_id,
                dataforseo_location_code=req.dataforseo_location_code,
                strategy_profile=req.strategy_profile,
                llm_client=llm, dataforseo_client=dfs,
                request_id=request_id,
            )
    except ValueError as exc:
        elapsed_ms = int((_time.monotonic() - handler_start) * 1000)
        logger.warning("niches_score ValueError request_id=%s elapsed_ms=%d: %s",
                       request_id, elapsed_ms, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        elapsed_ms = int((_time.monotonic() - handler_start) * 1000)
        logger.exception(
            "niches_score pipeline failed request_id=%s elapsed_ms=%d niche=%r city=%r",
            request_id, elapsed_ms, req.niche, req.city,
        )
        raise HTTPException(status_code=500, detail="Scoring pipeline failed unexpectedly")

    pipeline_ms = int((_time.monotonic() - handler_start) * 1000)

    report_id: str | None = None
    persist_failed = False
    persist_start = _time.monotonic()
    try:
        report_id = _persist_report(result.report)
    except Exception:
        logger.exception("niches_score persistence failed for report_id=%s",
                         result.report.get("report_id"))
        report_id = result.report.get("report_id")
        persist_failed = True
    persist_ms = int((_time.monotonic() - persist_start) * 1000)

    flush_ms = 0
    if dfs is not None and report_id:
        flush_start = _time.monotonic()
        try:
            dfs.cost_tracker.flush_to_supabase(report_id)
        except Exception:
            logger.exception("Failed to flush DFS cost log for report_id=%s", report_id)
        flush_ms = int((_time.monotonic() - flush_start) * 1000)

    entity_id: str | None = None
    snapshot_id: str | None = None
    try:
        kb = KBPersistence()
        entity_id = kb.upsert_entity(canonical)
        snapshot_id = kb.create_snapshot(
            entity_id=entity_id,
            input_hash=input_hash,
            strategy_profile=req.strategy_profile,
            report=result.report,
            report_id=report_id,
        )
        if report_id:
            kb.link_report(report_id=report_id, entity_id=entity_id, snapshot_id=snapshot_id)

        kb.store_evidence(
            snapshot_id=snapshot_id,
            artifact_type="score_bundle",
            payload=result.report.get("metros", []),
        )
        if result.report.get("keyword_expansion"):
            kb.store_evidence(
                snapshot_id=snapshot_id,
                artifact_type="keyword_expansion",
                payload=result.report["keyword_expansion"],
            )
    except Exception:
        logger.exception("KB persistence failed for report_id=%s", report_id)

    try:
        if report_id and not persist_failed:
            kb_client = KBPersistence()
            log_feedback(result.report, kb_client)
    except Exception:
        logger.exception("Feedback logging failed for report_id=%s", report_id)

    total_ms = int((_time.monotonic() - handler_start) * 1000)

    response: dict[str, Any] = {
        "report_id": report_id,
        "opportunity_score": result.opportunity_score,
        "classification_label": (
            "High" if result.opportunity_score >= 75
            else "Medium" if result.opportunity_score >= 50
            else "Low"
        ),
        "evidence": result.evidence,
        "report": result.report,
        "entity_id": entity_id,
        "snapshot_id": snapshot_id,
    }
    if persist_failed:
        response["persist_warning"] = "Report scored successfully but failed to save to database"
    logger.info(
        "niches_score DONE request_id=%s report_id=%s entity_id=%s snapshot_id=%s "
        "opportunity=%s persist_ok=%s pipeline_ms=%d persist_ms=%d flush_ms=%d total_ms=%d",
        request_id, report_id, entity_id, snapshot_id,
        result.opportunity_score, not persist_failed,
        pipeline_ms, persist_ms, flush_ms, total_ms,
    )
    return response


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
