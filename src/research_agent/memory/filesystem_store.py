"""Filesystem-based memory for operational state and artifact persistence.

Manages per-run artifacts, append-only progress logs, hypothesis backlogs,
experiment results, and deterministic replay bundles.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_BASE = Path("research_runs")


class FilesystemStore:
    """Durable filesystem store for research agent state and artifacts.

    Directory layout per run::

        {base_dir}/{run_id}/
            progress.jsonl          # append-only learning log
            backlog.json            # current hypothesis backlog
            experiment_results/     # per-experiment result snapshots
                {experiment_id}.json
            tool_outputs/           # raw tool responses for replay
                {step}_{tool}.json
            snapshots/              # scoring snapshots for diff
                baseline.json
                candidate_{n}.json
    """

    def __init__(self, run_id: str, base_dir: str | Path | None = None) -> None:
        self._run_id = run_id
        self._base = Path(base_dir) if base_dir else _DEFAULT_BASE
        self._run_dir = self._base / run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        (self._run_dir / "experiment_results").mkdir(exist_ok=True)
        (self._run_dir / "tool_outputs").mkdir(exist_ok=True)
        (self._run_dir / "snapshots").mkdir(exist_ok=True)

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    # ------------------------------------------------------------------
    # Progress log (append-only)
    # ------------------------------------------------------------------

    def append_progress(self, entry: dict[str, Any]) -> None:
        """Append a learning/progress entry with timestamp."""
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        path = self._run_dir / "progress.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def read_progress(self) -> list[dict[str, Any]]:
        """Read all progress entries."""
        path = self._run_dir / "progress.jsonl"
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    # ------------------------------------------------------------------
    # Hypothesis backlog
    # ------------------------------------------------------------------

    def save_backlog(self, backlog: list[dict[str, Any]]) -> None:
        """Overwrite the current hypothesis backlog."""
        path = self._run_dir / "backlog.json"
        with open(path, "w") as f:
            json.dump(backlog, f, indent=2, default=str)

    def load_backlog(self) -> list[dict[str, Any]]:
        path = self._run_dir / "backlog.json"
        if not path.exists():
            return []
        with open(path) as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Experiment results
    # ------------------------------------------------------------------

    def save_experiment_result(
        self, experiment_id: str, result: dict[str, Any]
    ) -> Path:
        """Persist an experiment result snapshot."""
        result["saved_at"] = datetime.now(timezone.utc).isoformat()
        path = self._run_dir / "experiment_results" / f"{experiment_id}.json"
        with open(path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        return path

    def load_experiment_result(self, experiment_id: str) -> dict[str, Any] | None:
        path = self._run_dir / "experiment_results" / f"{experiment_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def list_experiment_results(self) -> list[str]:
        results_dir = self._run_dir / "experiment_results"
        return [p.stem for p in results_dir.glob("*.json")]

    # ------------------------------------------------------------------
    # Tool outputs (for deterministic replay)
    # ------------------------------------------------------------------

    def save_tool_output(
        self, step: int, tool_name: str, output: Any
    ) -> Path:
        """Save a raw tool output for replay."""
        path = self._run_dir / "tool_outputs" / f"{step:04d}_{tool_name}.json"
        with open(path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        return path

    def load_tool_output(self, step: int, tool_name: str) -> Any | None:
        path = self._run_dir / "tool_outputs" / f"{step:04d}_{tool_name}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Scoring snapshots
    # ------------------------------------------------------------------

    def save_snapshot(self, name: str, data: dict[str, Any]) -> Path:
        """Save a scoring snapshot (baseline or candidate)."""
        data["snapshot_at"] = datetime.now(timezone.utc).isoformat()
        path = self._run_dir / "snapshots" / f"{name}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def load_snapshot(self, name: str) -> dict[str, Any] | None:
        path = self._run_dir / "snapshots" / f"{name}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def list_snapshots(self) -> list[str]:
        return [p.stem for p in (self._run_dir / "snapshots").glob("*.json")]

    # ------------------------------------------------------------------
    # Loop state (for resumability)
    # ------------------------------------------------------------------

    def save_loop_state(self, state: dict[str, Any]) -> None:
        """Persist current loop iteration state for crash recovery."""
        state["saved_at"] = datetime.now(timezone.utc).isoformat()
        path = self._run_dir / "loop_state.json"
        with open(path, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def load_loop_state(self) -> dict[str, Any] | None:
        path = self._run_dir / "loop_state.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Run summary
    # ------------------------------------------------------------------

    def artifact_path(self, relative: str) -> str:
        """Return the absolute path string for a relative artifact path within this run."""
        return str(self._run_dir / relative)
