"""Deep Agent coordinator for the research agent.

Initializes a LangChain Deep Agent with project-specific tools,
manages the research loop lifecycle, and provides the primary
interface for running research sessions.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from src.research_agent.evaluation.evaluator import evaluate_experiment
from src.research_agent.hypothesis.experiment_planner import plan_experiment
from src.research_agent.hypothesis.generator import (
    generate_hypotheses,
    generate_novel_hypothesis,
)
from src.research_agent.loop.ralph_loop import LoopConfig, RalphResearchLoop
from src.research_agent.memory.filesystem_store import FilesystemStore
from src.research_agent.memory.graph_store import ResearchGraphStore
from src.research_agent.recommendations.recommender import (
    generate_improvement_report,
    synthesize_recommendations,
)
from src.research_agent.tools.api_tools import ALL_TOOLS

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are a research scientist agent for the Widby niche scoring engine.

Your goal is to systematically improve the scoring algorithm by:
1. Analyzing scoring outputs to identify weak proxies and calibration issues
2. Generating hypotheses about parameter adjustments that could improve accuracy
3. Designing controlled experiments to test those hypotheses
4. Evaluating results and producing evidence-based recommendations

You have access to:
- DataForSEO API tools for SERP, keyword, business, and backlink data
- Metro database tools for geographic scope expansion
- LLM tools for keyword expansion and intent classification
- Scoring evaluation tools for comparing baseline vs candidate outcomes

Operating principles:
- Every hypothesis must be testable via the available proxy metrics
- Every experiment must have a clear rollback condition
- Recommendations require confidence scores and evidence bundles
- Avoid repeating invalidated hypotheses (check graph memory)
- Respect API budget limits across the research session

The scoring algorithm uses five proxy dimensions (Algo Spec V1.1):
  - Demand (§7.1): effective_search_volume, volume_breadth, transactional_ratio
  - Organic Competition (§7.2): avg_top5_da, local_biz_count, lighthouse performance
  - Local Competition (§7.3): review counts, review velocity, GBP completeness
  - Monetization (§7.4): CPC, business density, LSA/ads presence
  - AI Resilience (§7.5): AIO trigger rate, transactional keyword ratio, PAA density

Each dimension is weighted and combined into a composite opportunity score.
"""


# ---------------------------------------------------------------------------
# Research-specific tools (higher-level than API tools)
# ---------------------------------------------------------------------------


@tool
def generate_research_hypotheses(scoring_results_json: str) -> str:
    """Generate hypotheses from scoring results by identifying weak proxy dimensions.

    Args:
        scoring_results_json: JSON string of scoring results with per-metro data.

    Returns:
        JSON string of hypothesis list.
    """
    import json

    results = json.loads(scoring_results_json)
    hypotheses = generate_hypotheses(results)
    return json.dumps(hypotheses, indent=2)


@tool
def plan_research_experiment(hypothesis_json: str) -> str:
    """Convert a hypothesis into a structured experiment plan.

    Args:
        hypothesis_json: JSON string of a single hypothesis dict.

    Returns:
        JSON string of the experiment plan.
    """
    import json

    hypothesis = json.loads(hypothesis_json)
    plan = plan_experiment(hypothesis)
    return json.dumps(plan, indent=2)


@tool
def propose_novel_hypothesis(observation: str) -> str:
    """Propose a novel hypothesis from a free-form observation or idea.

    Args:
        observation: Description of the observation that motivated the hypothesis.

    Returns:
        JSON string of the hypothesis.
    """
    import json

    hypothesis = generate_novel_hypothesis(observation)
    return json.dumps(hypothesis, indent=2)


RESEARCH_TOOLS = ALL_TOOLS + [
    generate_research_hypotheses,
    plan_research_experiment,
    propose_novel_hypothesis,
]


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_research_agent(
    system_prompt: str | None = None,
    tools: list | None = None,
) -> Any:
    """Create a Deep Agent configured for research.

    Args:
        system_prompt: Override for the default research system prompt.
        tools: Override for the default tool set.

    Returns:
        A configured deep agent instance.
    """
    from deepagents import create_deep_agent

    return create_deep_agent(
        tools=tools or RESEARCH_TOOLS,
        system_prompt=system_prompt or RESEARCH_SYSTEM_PROMPT,
    )


# ---------------------------------------------------------------------------
# Research session orchestrator
# ---------------------------------------------------------------------------


def default_experiment_runner(
    hypothesis: dict[str, Any],
    fs: FilesystemStore,
) -> dict[str, Any]:
    """Default experiment runner that simulates parameter modification.

    In production, this would re-run the scoring pipeline with modified
    parameters. For now, it creates the experiment plan and records it.
    """
    plan = plan_experiment(hypothesis)
    fs.save_experiment_result(plan["experiment_id"], plan)
    return {
        "experiment_id": plan["experiment_id"],
        "cost_usd": 0.0,
        "modifications": plan["modifications"],
        "candidate_scores": {},
        "plan": plan,
    }


def run_research_session(
    scoring_results: dict[str, Any],
    config: LoopConfig | None = None,
    graph_path: str | None = None,
) -> dict[str, Any]:
    """Run a full research session: generate hypotheses, run experiments, recommend.

    This is the main entry point for the research agent pipeline.

    Args:
        scoring_results: Current scoring output to analyze.
        config: Optional loop configuration.
        graph_path: Optional path for persistent graph storage.

    Returns:
        Dict with recommendations, report, and loop outcome.
    """
    cfg = config or LoopConfig()
    if graph_path:
        cfg.graph_persist_path = graph_path

    graph = ResearchGraphStore(persist_path=cfg.graph_persist_path)
    hypotheses = generate_hypotheses(scoring_results, graph=graph)

    if not hypotheses:
        return {
            "recommendations": [],
            "report": "No hypotheses generated — scoring appears well-calibrated.",
            "outcome": None,
        }

    backlog = hypotheses

    loop = RalphResearchLoop(
        config=cfg,
        experiment_runner=default_experiment_runner,
        evaluator=evaluate_experiment,
    )

    loop.fs_store.save_snapshot("baseline", scoring_results)
    outcome = loop.run(backlog=backlog)

    recommendations = synthesize_recommendations(
        [r.to_dict() for r in outcome.results],
        graph=loop.graph_store,
    )

    report = generate_improvement_report(
        recommendations,
        [r.to_dict() for r in outcome.results],
    )

    loop.fs_store.append_progress(
        {
            "event": "session_complete",
            "stop_reason": outcome.stop_reason.value,
            "recommendations_count": len(recommendations),
        }
    )

    return {
        "recommendations": recommendations,
        "report": report,
        "outcome": outcome.to_dict(),
    }
