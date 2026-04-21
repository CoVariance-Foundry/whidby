"""SerpAPI async HTTP client.

Covers two engines needed by the recipe-reports feature (012):
  - ``engine=google`` — organic SERP with ``ads[]``, ``local_results``/
    ``local_pack`` and ``ai_overview`` in a single response.
  - ``engine=google_maps`` — Google Maps live local-pack data.

Authentication is a per-request ``api_key`` query parameter. SerpAPI charges
per search; we hard-code a small constant for auditability (the actual cost
varies by plan — we track it, we don't bill on it).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from src.config.constants import SERPAPI_SEARCH_COST_USD

SERPAPI_BASE_URL = "https://serpapi.com/search.json"
_TIMEOUT_SECONDS = 30.0


class SerpAPIError(RuntimeError):
    """Raised when SerpAPI returns a non-2xx response or times out."""


@dataclass
class SerpAPIResponse:
    """Standardised wrapper for SerpAPIClient results."""

    status: str  # "ok" | "error"
    data: dict[str, Any]
    cost: float = 0.0


class SerpAPIClient:
    """Async SerpAPI client.

    Args:
        api_key: SerpAPI account API key. Must be non-empty.
        base_url: Override the default endpoint (tests only).
        timeout: Total HTTP timeout in seconds.

    Raises:
        ValueError: If *api_key* is empty.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = SERPAPI_BASE_URL,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required (empty string was provided)")
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout

    # -- Public methods ------------------------------------------------------

    async def serp_google(
        self,
        q: str,
        location: str,
        gl: str = "us",
        hl: str = "en",
    ) -> SerpAPIResponse:
        """Organic SERP plus ads, local pack, and AI overview (engine=google).

        Args:
            q: Search query.
            location: Human-readable SerpAPI location string
                (e.g. ``"Austin, Texas, United States"``).
            gl: Country code (default ``"us"``).
            hl: UI language (default ``"en"``).
        """
        params = {
            "engine": "google",
            "q": q,
            "location": location,
            "gl": gl,
            "hl": hl,
            "api_key": self._api_key,
        }
        return await self._get(params)

    async def serp_maps(
        self,
        q: str,
        ll: str,
        type_: str = "search",
    ) -> SerpAPIResponse:
        """Google Maps results (engine=google_maps).

        Args:
            q: Search query.
            ll: Lat/lng/zoom string in SerpAPI's format
                (e.g. ``"@40.7128,-74.0060,14z"``).
            type_: Maps query type (``"search"`` or ``"place"``).
        """
        params = {
            "engine": "google_maps",
            "q": q,
            "ll": ll,
            "type": type_,
            "api_key": self._api_key,
        }
        return await self._get(params)

    # -- Internal: HTTP ------------------------------------------------------

    _MAX_ERROR_BODY_CHARS: int = 500

    async def _get(self, params: dict[str, Any]) -> SerpAPIResponse:
        """Execute a single GET and normalize the response."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http:
                resp = await http.get(self._base_url, params=params)
        except httpx.TimeoutException as exc:
            raise SerpAPIError(f"timeout after {self._timeout}s: {exc}") from exc

        if resp.status_code >= 400:
            raise SerpAPIError(
                f"SerpAPI returned HTTP {resp.status_code}: "
                f"{self._redact_body(resp.text)}"
            )

        try:
            body = resp.json()
        except ValueError as exc:
            raise SerpAPIError(f"invalid JSON body: {exc}") from exc

        return SerpAPIResponse(status="ok", data=body, cost=SERPAPI_SEARCH_COST_USD)

    def _redact_body(self, body: str) -> str:
        """Redact the API key from an error body before logging/raising.

        SerpAPI sometimes echoes the failing request back in error responses,
        which includes the ``api_key`` query parameter. We must strip it
        before the message enters the tool-call audit log (which is
        persisted to disk and fed back into the Claude conversation).
        """
        redacted = body or ""
        if self._api_key:
            redacted = redacted.replace(self._api_key, "***")
        if len(redacted) > self._MAX_ERROR_BODY_CHARS:
            redacted = redacted[: self._MAX_ERROR_BODY_CHARS] + "..."
        return redacted
