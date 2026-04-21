"""Tests for /api/reports endpoints (Phase 1 Task 6 of 012-recipe-reports).

These tests never hit Anthropic. :class:`anthropic.Anthropic` is patched to
a stub and :meth:`RecipeRunner.run` is replaced with a canned dict so the
HTTP layer can be exercised deterministically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from src.research_agent.api import app

    return TestClient(app)


def _canned_runner_result(report_path: Path) -> dict[str, Any]:
    return {
        "report_path": str(report_path),
        "bytes": 4096,
        "context": {"service": "plumber"},
        "collected": {"service": "plumber", "markets": []},
        "tool_calls": [],
        "cost_usd": 0.1234,
        "rounds_used": 3,
        "status": "ok",
    }


def _write_fake_report(runs_dir: Path, run_id: str, filename: str) -> Path:
    report_dir = runs_dir / run_id / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / filename
    report_path.write_text("<html><body>Test report</body></html>", encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# POST /api/reports
# ---------------------------------------------------------------------------


def test_post_reports_happy_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(api_module.anthropic, "Anthropic", MagicMock())

    captured: dict[str, Any] = {}
    expected_path = (
        tmp_path / "abcd1234" / "reports" / "market_opportunity_20260420T120000Z.html"
    )
    expected_path.parent.mkdir(parents=True, exist_ok=True)

    def fake_run(
        self: Any, recipe: Any, inputs: dict[str, Any], output_dir: Path
    ) -> dict[str, Any]:
        captured["recipe_id"] = recipe.recipe_id
        captured["inputs"] = inputs
        captured["output_dir"] = Path(output_dir)
        return _canned_runner_result(expected_path)

    monkeypatch.setattr(api_module.RecipeRunner, "run", fake_run)

    body = {
        "recipe_id": "market_opportunity",
        "inputs": {"service": "plumber", "cities": [{"name": "Austin, TX", "location_code": 2840}]},
        "run_id": "abcd1234",
    }
    res = client.post("/api/reports", json=body)
    assert res.status_code == 200, res.text

    payload = res.json()
    assert payload["report_id"] == "market_opportunity_20260420T120000Z"
    assert payload["recipe_id"] == "market_opportunity"
    assert payload["report_path"] == str(expected_path)
    assert payload["bytes"] == 4096
    assert payload["cost_usd"] == pytest.approx(0.1234)
    assert payload["rounds_used"] == 3
    assert payload["status"] == "ok"
    assert payload["run_id"] == "abcd1234"

    assert captured["recipe_id"] == "market_opportunity"
    assert captured["inputs"] == body["inputs"]
    assert captured["output_dir"] == tmp_path / "abcd1234" / "reports"
    assert captured["output_dir"].resolve().is_relative_to(tmp_path.resolve())


def test_post_reports_unknown_recipe_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(api_module.anthropic, "Anthropic", MagicMock())

    res = client.post(
        "/api/reports",
        json={"recipe_id": "bogus", "inputs": {}},
    )
    assert res.status_code == 404
    assert "bogus" in res.json()["detail"]


def test_post_reports_runner_error_422(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(api_module.anthropic, "Anthropic", MagicMock())

    def fake_run(
        self: Any, recipe: Any, inputs: dict[str, Any], output_dir: Path
    ) -> dict[str, Any]:
        raise api_module.RecipeRunnerError("could not extract final JSON")

    monkeypatch.setattr(api_module.RecipeRunner, "run", fake_run)

    res = client.post(
        "/api/reports",
        json={
            "recipe_id": "market_opportunity",
            "inputs": {"service": "plumber", "cities": []},
            "run_id": "run1",
        },
    )
    assert res.status_code == 422
    assert "could not extract final JSON" in res.json()["detail"]


def test_post_reports_generates_run_id_if_missing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(api_module.anthropic, "Anthropic", MagicMock())

    captured_run_ids: list[str] = []

    def fake_run(
        self: Any, recipe: Any, inputs: dict[str, Any], output_dir: Path
    ) -> dict[str, Any]:
        run_id = Path(output_dir).parent.name
        captured_run_ids.append(run_id)
        fake_path = (
            Path(output_dir) / "market_opportunity_20260420T120000Z.html"
        )
        fake_path.parent.mkdir(parents=True, exist_ok=True)
        return _canned_runner_result(fake_path)

    monkeypatch.setattr(api_module.RecipeRunner, "run", fake_run)

    res = client.post(
        "/api/reports",
        json={
            "recipe_id": "market_opportunity",
            "inputs": {"service": "plumber", "cities": []},
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["run_id"]
    assert len(payload["run_id"]) >= 6
    assert captured_run_ids == [payload["run_id"]]


# ---------------------------------------------------------------------------
# GET /api/reports
# ---------------------------------------------------------------------------


def test_get_reports_list_empty_when_no_runs_dir(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    nonexistent = tmp_path / "does-not-exist"
    monkeypatch.setattr(api_module, "RUNS_DIR", nonexistent)

    res = client.get("/api/reports")
    assert res.status_code == 200
    assert res.json() == {"reports": []}


def test_get_reports_list_scans_directory(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)

    _write_fake_report(
        tmp_path, "run1", "market_opportunity_20260420T120000Z.html"
    )
    _write_fake_report(
        tmp_path, "run2", "market_opportunity_20260421T080000Z.html"
    )

    res = client.get("/api/reports")
    assert res.status_code == 200
    payload = res.json()
    assert len(payload["reports"]) == 2

    # Sorted descending by created_at
    first, second = payload["reports"]
    assert first["created_at"] == "2026-04-21T08:00:00Z"
    assert first["run_id"] == "run2"
    assert first["recipe_id"] == "market_opportunity"
    assert first["report_id"] == "market_opportunity_20260421T080000Z"
    assert first["bytes"] > 0

    assert second["created_at"] == "2026-04-20T12:00:00Z"
    assert second["run_id"] == "run1"


# ---------------------------------------------------------------------------
# GET /api/reports/{run_id}/{report_id}
# ---------------------------------------------------------------------------


def test_get_report_by_id_returns_metadata_and_html(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)

    report_path = _write_fake_report(
        tmp_path, "run1", "market_opportunity_20260420T120000Z.html"
    )
    expected_html = report_path.read_text(encoding="utf-8")

    res = client.get(
        "/api/reports/run1/market_opportunity_20260420T120000Z"
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["report_id"] == "market_opportunity_20260420T120000Z"
    assert payload["run_id"] == "run1"
    assert payload["recipe_id"] == "market_opportunity"
    assert payload["created_at"] == "2026-04-20T12:00:00Z"
    assert payload["bytes"] == len(expected_html.encode("utf-8"))
    assert payload["html"] == expected_html


def test_get_report_404_when_missing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)

    res = client.get("/api/reports/nonexistent/foo")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/reports/{run_id}/{report_id}/download
# ---------------------------------------------------------------------------


def test_get_report_download_returns_html_file_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)

    report_path = _write_fake_report(
        tmp_path, "run1", "market_opportunity_20260420T120000Z.html"
    )
    expected_html = report_path.read_text(encoding="utf-8")

    res = client.get(
        "/api/reports/run1/market_opportunity_20260420T120000Z/download"
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert res.text == expected_html


def test_get_report_download_404_when_missing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)

    res = client.get("/api/reports/nope/none/download")
    assert res.status_code == 404


def test_post_reports_rejects_traversal_in_run_id(
    client: TestClient,
) -> None:
    # Pydantic validator on ReportRequest.run_id rejects "../" and similar;
    # FastAPI returns 422 Unprocessable Entity for request-validation errors.
    res = client.post(
        "/api/reports",
        json={
            "recipe_id": "market_opportunity",
            "inputs": {"service": "plumber", "cities": []},
            "run_id": "../escape",
        },
    )
    assert res.status_code == 422


def test_post_reports_rejects_unsafe_recipe_id(client: TestClient) -> None:
    res = client.post(
        "/api/reports",
        json={
            "recipe_id": "../../etc/passwd",
            "inputs": {},
        },
    )
    assert res.status_code == 422


def test_get_report_rejects_traversal_in_identifiers(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # FastAPI path-param regex rejects characters outside the safe set.
    # Starlette's default path converter doesn't decode `%2F`, so the
    # nested-slash form manifests as a 422 (regex mismatch) or 404
    # (path didn't resolve to a route), never a file read outside RUNS_DIR.
    import src.research_agent.api as api_module

    monkeypatch.setattr(api_module, "RUNS_DIR", tmp_path)

    # Dots aren't in the safe set.
    res = client.get("/api/reports/..%2F..%2Fetc/passwd")
    assert res.status_code in {404, 422}

    # Explicit "." traversal segment.
    res = client.get("/api/reports/bad.id/report")
    assert res.status_code == 422
