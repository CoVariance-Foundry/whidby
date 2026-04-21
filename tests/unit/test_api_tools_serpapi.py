"""Tests for the SerpAPI api_tools facades' graceful-degradation path.

When ``SERPAPI_KEY`` is unset, the facades must return a structured error
payload instead of raising, so the Claude tool-use loop can surface the
misconfiguration as a normal tool result rather than crash the runner.
"""

from __future__ import annotations

import json

import pytest

from src.research_agent.tools.api_tools import (
    fetch_serpapi_google,
    fetch_serpapi_maps,
)


def test_fetch_serpapi_google_returns_error_payload_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SERPAPI_KEY", raising=False)

    raw = fetch_serpapi_google(keyword="plumber", location="Austin, TX")
    payload = json.loads(raw)
    assert payload["status"] == "error"
    assert payload["cost"] == 0.0
    assert "SERPAPI_KEY" in payload["data"]["error"]


def test_fetch_serpapi_maps_returns_error_payload_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SERPAPI_KEY", raising=False)

    raw = fetch_serpapi_maps(keyword="plumber", ll="@30.2672,-97.7431,14z")
    payload = json.loads(raw)
    assert payload["status"] == "error"
    assert payload["cost"] == 0.0
    assert "SERPAPI_KEY" in payload["data"]["error"]
