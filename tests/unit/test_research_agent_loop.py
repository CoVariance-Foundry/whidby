"""Unit tests for the Ralph-style research loop."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.research_agent.loop.ralph_loop import (
    IterationResult,
    LoopConfig,
    LoopOutcome,
    RalphResearchLoop,
    StopReason,
)
from src.research_agent.memory.filesystem_store import FilesystemStore


def _make_backlog(n: int = 3) -> list[dict[str, Any]]:
    return [
        {
            "id": f"h{i}",
            "title": f"Hypothesis {i}",
            "description": f"Test hypothesis {i}",
            "target_proxy": "demand",
            "priority": n - i,
            "status": "pending",
        }
        for i in range(n)
    ]


def _simple_runner(hypothesis: dict[str, Any], fs: FilesystemStore) -> dict[str, Any]:
    return {
        "cost_usd": 0.01,
        "candidate_scores": {
            "metros": [
                {"scores": {"opportunity": 73}},
                {"scores": {"opportunity": 65}},
            ]
        },
    }


def _simple_evaluator(
    baseline: dict[str, Any], experiment: dict[str, Any]
) -> tuple[float, float, str]:
    return 70.0, 72.0, "Score improved by 2 points"


def _degrading_evaluator(
    baseline: dict[str, Any], experiment: dict[str, Any]
) -> tuple[float, float, str]:
    return 70.0, 68.0, "Score degraded by 2 points"


def _flat_evaluator(
    baseline: dict[str, Any], experiment: dict[str, Any]
) -> tuple[float, float, str]:
    return 70.0, 70.0, "No change"


class TestLoopConfig:
    def test_default_values(self):
        cfg = LoopConfig()
        assert cfg.max_iterations == 10
        assert cfg.convergence_window == 3
        assert cfg.convergence_threshold == 0.01
        assert cfg.budget_limit_usd == 50.0
        assert len(cfg.run_id) == 8


class TestRalphResearchLoop:
    def test_runs_to_backlog_empty(self, tmp_path: Path):
        cfg = LoopConfig(
            max_iterations=20,
            run_id="test-run",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, _simple_runner, _simple_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        outcome = loop.run(backlog=_make_backlog(2))

        assert outcome.stop_reason == StopReason.BACKLOG_EMPTY
        assert outcome.iterations_completed == 2
        assert outcome.validated_count == 2

    def test_stops_at_max_iterations(self, tmp_path: Path):
        cfg = LoopConfig(
            max_iterations=2,
            run_id="test-max",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, _simple_runner, _simple_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        outcome = loop.run(backlog=_make_backlog(5))

        assert outcome.stop_reason == StopReason.MAX_ITERATIONS
        assert outcome.iterations_completed == 2

    def test_stops_on_budget_exceeded(self, tmp_path: Path):
        def expensive_runner(h: dict, fs: FilesystemStore) -> dict:
            return {"cost_usd": 30.0, "candidate_scores": {}}

        cfg = LoopConfig(
            max_iterations=10,
            budget_limit_usd=25.0,
            run_id="test-budget",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, expensive_runner, _simple_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        outcome = loop.run(backlog=_make_backlog(5))

        assert outcome.stop_reason == StopReason.BUDGET_EXCEEDED
        assert outcome.total_cost_usd >= 25.0

    def test_convergence_detection(self, tmp_path: Path):
        cfg = LoopConfig(
            max_iterations=20,
            convergence_window=3,
            convergence_threshold=0.05,
            run_id="test-converge",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, _simple_runner, _flat_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        outcome = loop.run(backlog=_make_backlog(10))

        assert outcome.stop_reason == StopReason.CONVERGENCE

    def test_invalidated_hypotheses_tracked(self, tmp_path: Path):
        cfg = LoopConfig(
            max_iterations=5,
            run_id="test-invalid",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, _simple_runner, _degrading_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        outcome = loop.run(backlog=_make_backlog(3))

        assert outcome.invalidated_count == outcome.iterations_completed

    def test_progress_persisted(self, tmp_path: Path):
        cfg = LoopConfig(
            max_iterations=2,
            run_id="test-progress",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, _simple_runner, _simple_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        loop.run(backlog=_make_backlog(3))

        progress = loop.fs_store.read_progress()
        assert len(progress) >= 2

    def test_graph_nodes_created(self, tmp_path: Path):
        cfg = LoopConfig(
            max_iterations=2,
            run_id="test-graph",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, _simple_runner, _simple_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        loop.run(backlog=_make_backlog(2))

        summary = loop.graph_store.export_summary()
        assert summary["total_nodes"] >= 4
        assert summary["total_edges"] >= 2

    def test_experiment_failure_continues_loop(self, tmp_path: Path):
        call_count = 0

        def failing_runner(h: dict, fs: FilesystemStore) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated API failure")
            return {"cost_usd": 0.01, "candidate_scores": {}}

        cfg = LoopConfig(
            max_iterations=5,
            run_id="test-fail",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, failing_runner, _simple_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        outcome = loop.run(backlog=_make_backlog(3))

        assert outcome.iterations_completed >= 1

    def test_loop_state_saved_for_crash_recovery(self, tmp_path: Path):
        cfg = LoopConfig(
            max_iterations=1,
            run_id="test-state",
            base_dir=str(tmp_path),
        )
        loop = RalphResearchLoop(cfg, _simple_runner, _simple_evaluator)
        loop.fs_store.save_snapshot("baseline", {"metros": []})
        loop.run(backlog=_make_backlog(1))

        state = loop.fs_store.load_loop_state()
        assert state is not None
        assert "completed" in state


class TestIterationResult:
    def test_to_dict(self):
        result = IterationResult(
            iteration=1,
            hypothesis_id="h1",
            experiment_id="e1",
            baseline_score=70.0,
            candidate_score=72.0,
            delta=2.0,
            validated=True,
            cost_usd=0.05,
            learning="Test learning",
        )
        d = result.to_dict()
        assert d["iteration"] == 1
        assert d["validated"] is True
        assert d["delta"] == 2.0
