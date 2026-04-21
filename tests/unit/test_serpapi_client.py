"""Unit tests for the SerpAPI client.

Tests are mocked — no network calls. Covers:
  Authentication (empty key guard), engine=google organic+ads+local_pack+ai_overview,
  engine=google_maps, error handling, timeout handling, cost accounting.
"""

from __future__ import annotations

import httpx
import pytest

from src.clients.serpapi.client import (
    SerpAPIClient,
    SerpAPIError,
    SerpAPIResponse,
)
from src.config.constants import SERPAPI_SEARCH_COST_USD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.text = text or (str(json_body) if json_body else "")

    def json(self):
        return self._json_body

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://serpapi.com/search.json")
            raise httpx.HTTPStatusError(
                f"{self.status_code}",
                request=request,
                response=httpx.Response(self.status_code, text=self.text),
            )


class _FakeAsyncClient:
    """Drop-in replacement for httpx.AsyncClient."""

    _captured: list[dict] = []
    _response: _FakeResponse | None = None
    _exception: Exception | None = None

    def __init__(self, *args, **kwargs):
        self._init_kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None, headers=None):
        type(self)._captured.append({"url": url, "params": params, "headers": headers})
        if type(self)._exception is not None:
            raise type(self)._exception
        assert type(self)._response is not None, "Test did not configure _response"
        return type(self)._response


@pytest.fixture(autouse=True)
def _reset_fake():
    _FakeAsyncClient._captured = []
    _FakeAsyncClient._response = None
    _FakeAsyncClient._exception = None
    yield


# ---------------------------------------------------------------------------
# Construction / auth
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key"):
            SerpAPIClient(api_key="")

    def test_valid_key_constructs(self):
        client = SerpAPIClient(api_key="abc123")
        assert client._api_key == "abc123"


# ---------------------------------------------------------------------------
# serp_google
# ---------------------------------------------------------------------------


class TestSerpGoogle:
    @pytest.mark.asyncio
    async def test_passes_correct_params(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient._response = _FakeResponse(
            200,
            json_body={
                "organic_results": [{"title": "x"}],
                "ads": [],
                "local_results": {"places": []},
                "ai_overview": {},
                "extra_key": "should_still_pass_through",
            },
        )

        client = SerpAPIClient(api_key="k123")
        resp = await client.serp_google(q="plumber", location="Austin, Texas, United States")

        assert isinstance(resp, SerpAPIResponse)
        assert resp.status == "ok"
        assert resp.cost == SERPAPI_SEARCH_COST_USD
        assert resp.data["organic_results"] == [{"title": "x"}]

        captured = _FakeAsyncClient._captured[0]
        assert captured["url"] == "https://serpapi.com/search.json"
        params = captured["params"]
        assert params["engine"] == "google"
        assert params["q"] == "plumber"
        assert params["location"] == "Austin, Texas, United States"
        assert params["api_key"] == "k123"
        assert params["gl"] == "us"
        assert params["hl"] == "en"

    @pytest.mark.asyncio
    async def test_custom_gl_hl(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient._response = _FakeResponse(200, json_body={"organic_results": []})

        client = SerpAPIClient(api_key="k")
        await client.serp_google(q="cafe", location="Paris, France", gl="fr", hl="fr")

        params = _FakeAsyncClient._captured[0]["params"]
        assert params["gl"] == "fr"
        assert params["hl"] == "fr"


# ---------------------------------------------------------------------------
# serp_maps
# ---------------------------------------------------------------------------


class TestSerpMaps:
    @pytest.mark.asyncio
    async def test_passes_correct_engine_and_ll(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient._response = _FakeResponse(
            200, json_body={"local_results": [{"title": "Bob's Plumbing"}]}
        )

        client = SerpAPIClient(api_key="k")
        resp = await client.serp_maps(q="plumber", ll="@40.7128,-74.0060,14z")

        assert resp.status == "ok"
        assert resp.cost == SERPAPI_SEARCH_COST_USD

        params = _FakeAsyncClient._captured[0]["params"]
        assert params["engine"] == "google_maps"
        assert params["q"] == "plumber"
        assert params["ll"] == "@40.7128,-74.0060,14z"
        assert params["type"] == "search"
        assert params["api_key"] == "k"

    @pytest.mark.asyncio
    async def test_custom_type(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient._response = _FakeResponse(200, json_body={"place_results": {}})

        client = SerpAPIClient(api_key="k")
        await client.serp_maps(q="plumber", ll="@40,-74,14z", type_="place")

        assert _FakeAsyncClient._captured[0]["params"]["type"] == "place"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_4xx_raises_serpapi_error(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient._response = _FakeResponse(
            401, json_body={"error": "Invalid API key"}, text='{"error":"Invalid API key"}'
        )

        client = SerpAPIClient(api_key="bad")
        with pytest.raises(SerpAPIError) as excinfo:
            await client.serp_google(q="x", location="y")
        assert "401" in str(excinfo.value)
        assert "Invalid API key" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_5xx_raises_serpapi_error(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient._response = _FakeResponse(503, text="Service Unavailable")

        client = SerpAPIClient(api_key="k")
        with pytest.raises(SerpAPIError) as excinfo:
            await client.serp_google(q="x", location="y")
        assert "503" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_timeout_raises_serpapi_error(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient._exception = httpx.TimeoutException("timed out")

        client = SerpAPIClient(api_key="k")
        with pytest.raises(SerpAPIError) as excinfo:
            await client.serp_google(q="x", location="y")
        assert "timeout" in str(excinfo.value).lower()

    def test_serpapi_error_is_runtime_error(self):
        assert issubclass(SerpAPIError, RuntimeError)

    @pytest.mark.asyncio
    async def test_malformed_json_body_raises_serpapi_error(self, mocker):
        mocker.patch("src.clients.serpapi.client.httpx.AsyncClient", _FakeAsyncClient)

        class _BrokenJSONResponse(_FakeResponse):
            def json(self):
                raise ValueError("Expecting value: line 1 column 1 (char 0)")

        _FakeAsyncClient._response = _BrokenJSONResponse(200, text="<html>not json</html>")

        client = SerpAPIClient(api_key="k")
        with pytest.raises(SerpAPIError) as excinfo:
            await client.serp_google(q="x", location="y")
        assert "invalid JSON body" in str(excinfo.value)
