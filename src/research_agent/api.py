"""FastAPI bridge exposing the research agent to the frontend.

Run with: uvicorn src.research_agent.api:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from src.clients.dataforseo.client import DataForSEOClient
from src.data.metro_db import Metro, MetroDB
from src.clients.llm.client import LLMClient
from src.clients.supabase_persistence import SupabasePersistence
from src.pipeline.orchestrator import score_niche_for_metro
from src.research_agent.deep_agent import run_research_session
from src.research_agent.loop.ralph_loop import LoopConfig
from src.research_agent.memory.filesystem_store import FilesystemStore
from src.research_agent.memory.graph_store import ResearchGraphStore

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "https://app.thewidby.com",
        "https://whidby-1.onrender.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_METRO_DB: MetroDB | None = None


def _metro_db() -> MetroDB:
    global _METRO_DB
    if _METRO_DB is None:
        _METRO_DB = MetroDB.from_seed()
    return _METRO_DB


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
    try:
        if req.dry_run:
            result = await score_niche_for_metro(
                niche=req.niche, city=req.city, state=req.state,
                strategy_profile=req.strategy_profile,
                llm_client=None, dataforseo_client=None, dry_run=True,
            )
        else:
            import os

            dfs = DataForSEOClient(
                login=os.environ["DATAFORSEO_LOGIN"],
                password=os.environ["DATAFORSEO_PASSWORD"],
            )
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
