"""FastAPI bridge exposing the research agent to the frontend.

Run with: uvicorn src.research_agent.api:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.research_agent.deep_agent import run_research_session
from src.research_agent.loop.ralph_loop import LoopConfig
from src.research_agent.memory.filesystem_store import FilesystemStore
from src.research_agent.memory.graph_store import ResearchGraphStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Widby Research Agent API", version="0.1.0")

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

@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for Render and monitoring."""
    return {"status": "ok"}


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
