"""Tests for FastAPI research agent API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.research_agent.api import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
