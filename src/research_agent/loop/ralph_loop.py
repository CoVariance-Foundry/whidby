"""Ralph-style iterative research loop for the research agent.

Cycle stages:
  1. select_task   — pick highest-priority incomplete hypothesis from backlog
  2. run_experiment — execute the experiment via Deep Agent tools
  3. evaluate      — compare results against baseline and expected uplift
  4. record_learning — persist outcomes to filesystem + promote to graph
  5. reprioritize  — update backlog priorities based on new evidence

Stop conditions:
  - max_iterations reached
  - convergence (no meaningful score delta across N consecutive iterations)
  - budget threshold (cumulative API cost exceeds limit)
  - all backlog items completed or invalidated
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from src.research_agent.memory.filesystem_store import FilesystemStore
from src.research_agent.memory.graph_store import ResearchGraphStore
from src.research_agent.memory.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeStatus,
    NodeType,
)

logger = logging.getLogger(__name__)


class StopReason(str, Enum):
    MAX_ITERATIONS = "max_iterations"
    CONVERGENCE = "convergence"
    BUDGET_EXCEEDED = "budget_exceeded"
    BACKLOG_EMPTY = "backlog_empty"
    EXTERNAL_HALT = "external_halt"


@dataclass
class LoopConfig:
    """Configuration for the research loop."""

    max_iterations: int = 10
    convergence_window: int = 3
    convergence_threshold: float = 0.01
    budget_limit_usd: float = 50.0
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    base_dir: str = "research_runs"
    graph_persist_path: str | None = None


@dataclass
class IterationResult:
    """Outcome of a single loop iteration."""

    iteration: int
    hypothesis_id: str
    experiment_id: str
    baseline_score: float
    candidate_score: float
    delta: float
    validated: bool
    cost_usd: float
    learning: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "hypothesis_id": self.hypothesis_id,
            "experiment_id": self.experiment_id,
            "baseline_score": self.baseline_score,
            "candidate_score": self.candidate_score,
            "delta": self.delta,
            "validated": self.validated,
            "cost_usd": self.cost_usd,
            "learning": self.learning,
            "timestamp": self.timestamp,
        }


@dataclass
class LoopOutcome:
    """Final outcome of a completed research loop."""

    run_id: str
    iterations_completed: int
    stop_reason: StopReason
    total_cost_usd: float
    results: list[IterationResult]
    validated_count: int
    invalidated_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "iterations_completed": self.iterations_completed,
            "stop_reason": self.stop_reason.value,
            "total_cost_usd": self.total_cost_usd,
            "validated_count": self.validated_count,
            "invalidated_count": self.invalidated_count,
            "results": [r.to_dict() for r in self.results],
        }


ExperimentRunner = Callable[
    [dict[str, Any], FilesystemStore], dict[str, Any]
]
Evaluator = Callable[
    [dict[str, Any], dict[str, Any]], tuple[float, float, str]
]


class RalphResearchLoop:
    """Iterative research loop inspired by the Ralph autonomous agent pattern.

    Each iteration:
      1. Picks the highest-priority pending hypothesis from the backlog.
      2. Delegates experiment execution to a runner callback.
      3. Evaluates baseline vs candidate via an evaluator callback.
      4. Records learnings to filesystem and (if validated) promotes to graph.
      5. Reprioritizes the remaining backlog.

    Args:
        config: Loop configuration.
        experiment_runner: Callable that executes an experiment given a
            hypothesis dict and the filesystem store. Returns a result dict
            with at minimum {"cost_usd": float, "candidate_scores": dict}.
        evaluator: Callable that takes (baseline_snapshot, experiment_result)
            and returns (baseline_score, candidate_score, learning_text).
    """

    def __init__(
        self,
        config: LoopConfig,
        experiment_runner: ExperimentRunner,
        evaluator: Evaluator,
    ) -> None:
        self._config = config
        self._run_experiment = experiment_runner
        self._evaluate = evaluator
        self._fs = FilesystemStore(
            run_id=config.run_id, base_dir=config.base_dir
        )
        graph_path = config.graph_persist_path or str(
            self._fs.run_dir / "knowledge_graph.json"
        )
        self._graph = ResearchGraphStore(persist_path=graph_path)
        self._cumulative_cost = 0.0
        self._results: list[IterationResult] = []

    @property
    def fs_store(self) -> FilesystemStore:
        return self._fs

    @property
    def graph_store(self) -> ResearchGraphStore:
        return self._graph

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, backlog: list[dict[str, Any]] | None = None) -> LoopOutcome:
        """Execute the full research loop until a stop condition is met.

        Args:
            backlog: Initial hypothesis backlog. If None, loads from filesystem.

        Returns:
            LoopOutcome summarising the run.
        """
        if backlog is not None:
            self._fs.save_backlog(backlog)
        current_backlog = self._fs.load_backlog()

        # Load baseline snapshot (must be set externally before run)
        baseline = self._fs.load_snapshot("baseline")
        if baseline is None:
            baseline = {}

        stop_reason = StopReason.MAX_ITERATIONS

        for iteration in range(1, self._config.max_iterations + 1):
            # -- Check stop: backlog empty --
            pending = [h for h in current_backlog if h.get("status") == "pending"]
            if not pending:
                stop_reason = StopReason.BACKLOG_EMPTY
                break

            # -- Check stop: budget --
            if self._cumulative_cost >= self._config.budget_limit_usd:
                stop_reason = StopReason.BUDGET_EXCEEDED
                break

            # -- Check stop: convergence --
            if self._check_convergence():
                stop_reason = StopReason.CONVERGENCE
                break

            # -- 1. Select task --
            hypothesis = self._select_task(pending)
            hypothesis["status"] = "in_progress"
            self._fs.save_backlog(current_backlog)

            logger.info(
                "Iteration %d/%d — hypothesis: %s",
                iteration,
                self._config.max_iterations,
                hypothesis.get("title", hypothesis.get("id", "unknown")),
            )

            # -- Save loop state for crash recovery --
            self._fs.save_loop_state(
                {
                    "iteration": iteration,
                    "hypothesis_id": hypothesis.get("id", ""),
                    "cumulative_cost_usd": self._cumulative_cost,
                }
            )

            # -- 2. Run experiment --
            experiment_id = str(uuid.uuid4())[:8]
            try:
                experiment_result = self._run_experiment(hypothesis, self._fs)
            except Exception as e:
                logger.error("Experiment failed: %s", e, exc_info=True)
                hypothesis["status"] = "failed"
                self._fs.save_backlog(current_backlog)
                self._fs.append_progress(
                    {
                        "iteration": iteration,
                        "hypothesis_id": hypothesis.get("id"),
                        "event": "experiment_failed",
                        "error": str(e),
                    }
                )
                continue

            experiment_cost = experiment_result.get("cost_usd", 0.0)
            self._cumulative_cost += experiment_cost
            self._fs.save_experiment_result(experiment_id, experiment_result)

            # -- 3. Evaluate --
            try:
                baseline_score, candidate_score, learning = self._evaluate(
                    baseline, experiment_result
                )
            except Exception as e:
                logger.error("Evaluation failed: %s", e, exc_info=True)
                hypothesis["status"] = "eval_failed"
                self._fs.save_backlog(current_backlog)
                continue

            delta = candidate_score - baseline_score
            validated = delta > 0

            result = IterationResult(
                iteration=iteration,
                hypothesis_id=hypothesis.get("id", ""),
                experiment_id=experiment_id,
                baseline_score=baseline_score,
                candidate_score=candidate_score,
                delta=delta,
                validated=validated,
                cost_usd=experiment_cost,
                learning=learning,
            )
            self._results.append(result)

            # -- 4. Record learning --
            hypothesis["status"] = "validated" if validated else "invalidated"
            self._fs.save_backlog(current_backlog)
            self._fs.append_progress(
                {
                    "iteration": iteration,
                    **result.to_dict(),
                }
            )
            self._promote_to_graph(hypothesis, result)

            # -- 5. Reprioritize --
            current_backlog = self._reprioritize(current_backlog, result)
            self._fs.save_backlog(current_backlog)

            logger.info(
                "Iteration %d complete — delta=%.4f validated=%s cost=$%.4f",
                iteration,
                delta,
                validated,
                experiment_cost,
            )

        validated_count = sum(1 for r in self._results if r.validated)
        invalidated_count = sum(1 for r in self._results if not r.validated)

        outcome = LoopOutcome(
            run_id=self._config.run_id,
            iterations_completed=len(self._results),
            stop_reason=stop_reason,
            total_cost_usd=self._cumulative_cost,
            results=self._results,
            validated_count=validated_count,
            invalidated_count=invalidated_count,
        )

        self._fs.save_loop_state(
            {
                "completed": True,
                "stop_reason": stop_reason.value,
                **outcome.to_dict(),
            }
        )
        return outcome

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_task(self, pending: list[dict[str, Any]]) -> dict[str, Any]:
        """Pick the highest-priority pending hypothesis."""
        return sorted(
            pending, key=lambda h: h.get("priority", 0), reverse=True
        )[0]

    def _check_convergence(self) -> bool:
        """True if the last N iterations all had delta below threshold."""
        window = self._config.convergence_window
        if len(self._results) < window:
            return False
        recent = self._results[-window:]
        return all(
            abs(r.delta) < self._config.convergence_threshold for r in recent
        )

    def _promote_to_graph(
        self, hypothesis: dict[str, Any], result: IterationResult
    ) -> None:
        """Promote validated experiment outcomes to graph memory."""
        h_node = GraphNode(
            id=hypothesis.get("id", str(uuid.uuid4())[:8]),
            node_type=NodeType.HYPOTHESIS,
            title=hypothesis.get("title", ""),
            description=hypothesis.get("description", ""),
            status=(
                NodeStatus.VALIDATED if result.validated else NodeStatus.INVALIDATED
            ),
            confidence=abs(result.delta),
            provenance_artifact=self._fs.artifact_path(
                f"experiment_results/{result.experiment_id}.json"
            ),
            metadata={
                "baseline_score": result.baseline_score,
                "candidate_score": result.candidate_score,
                "delta": result.delta,
            },
        )
        self._graph.add_node(h_node)

        exp_node = GraphNode(
            id=result.experiment_id,
            node_type=NodeType.EXPERIMENT,
            title=f"Experiment for: {hypothesis.get('title', '')}",
            description=result.learning,
            status=NodeStatus.VALIDATED if result.validated else NodeStatus.INVALIDATED,
            confidence=abs(result.delta),
            provenance_artifact=self._fs.artifact_path(
                f"experiment_results/{result.experiment_id}.json"
            ),
            metadata={"cost_usd": result.cost_usd},
        )
        self._graph.add_node(exp_node)

        edge_type = EdgeType.SUPPORTS if result.validated else EdgeType.CONTRADICTS
        self._graph.add_edge(
            GraphEdge(
                source_id=exp_node.id,
                target_id=h_node.id,
                edge_type=edge_type,
                weight=abs(result.delta),
            )
        )

    def _reprioritize(
        self,
        backlog: list[dict[str, Any]],
        latest_result: IterationResult,
    ) -> list[dict[str, Any]]:
        """Adjust priorities of remaining pending hypotheses based on evidence.

        Hypotheses that share a target proxy with a validated result get
        a priority boost. Those related to invalidated hypotheses get demoted.
        """
        for item in backlog:
            if item.get("status") != "pending":
                continue
            if latest_result.validated:
                if item.get("target_proxy") == latest_result.hypothesis_id:
                    item["priority"] = item.get("priority", 0) + 1
            else:
                if item.get("related_to") == latest_result.hypothesis_id:
                    item["priority"] = max(item.get("priority", 0) - 1, 0)
        return backlog
