"""Unified DataForSEO client. (M0 — Algo Spec V1.1, §14)

Handles authentication, rate limiting, request queuing (standard vs. live),
response caching, error handling, cost tracking, and retry logic.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

import httpx

from src.config.constants import (
    DFS_BASE_URL,
    DFS_CACHE_TTL,
    DFS_DEFAULT_LANGUAGE_CODE,
    DFS_DEFAULT_LOCATION_NAME,
    DFS_MAX_RETRIES,
    DFS_QUEUE_MAX_WAIT,
    DFS_QUEUE_POLL_INTERVAL,
    DFS_RATE_LIMIT,
)

from . import endpoints as ep
from .cache import ResponseCache
from .cost_tracker import CostTracker
from .types import APIResponse, CostRecord

logger = logging.getLogger(__name__)


class _RateLimiter:
    """Token-bucket rate limiter scoped to calls-per-minute."""

    def __init__(self, calls_per_minute: int) -> None:
        self._max = calls_per_minute
        self._interval = 60.0 / calls_per_minute
        self._lock = asyncio.Lock()
        self._last: float = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


class DataForSEOClient:
    """Async DataForSEO API client.

    Args:
        login: DataForSEO account login.
        password: DataForSEO account password.
        base_url: API base URL (default from constants).
        cache_ttl: Response cache TTL in seconds (0 to disable).
        rate_limit: Max calls per minute.
    """

    def __init__(
        self,
        login: str,
        password: str,
        *,
        base_url: str = DFS_BASE_URL,
        cache_ttl: int = DFS_CACHE_TTL,
        rate_limit: int = DFS_RATE_LIMIT,
    ) -> None:
        creds = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._auth_header = f"Basic {creds}"
        self._base_url = base_url.rstrip("/") + "/"
        self._cache = ResponseCache(ttl=cache_ttl)
        self._tracker = CostTracker()
        self._rate_limiter = _RateLimiter(rate_limit)

    # -- Public properties ---------------------------------------------------

    @property
    def cost_log(self) -> list[CostRecord]:
        return self._tracker.records

    @property
    def total_cost(self) -> float:
        return self._tracker.total_cost

    # -- High-level API methods ----------------------------------------------

    async def locations(self) -> APIResponse:
        """GET /serp/google/locations — no payload, free endpoint."""
        return await self._live_request(ep.LOCATIONS, payload=[])

    async def serp_organic(
        self,
        keyword: str,
        location_code: int,
        depth: int = 10,
        language_code: str = DFS_DEFAULT_LANGUAGE_CODE,
    ) -> APIResponse:
        params = {
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": depth,
        }
        return await self._queued_request(ep.SERP_ORGANIC, params)

    async def serp_maps(
        self,
        keyword: str,
        location_code: int,
        depth: int = 10,
        language_code: str = DFS_DEFAULT_LANGUAGE_CODE,
    ) -> APIResponse:
        params = {
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": depth,
        }
        return await self._queued_request(ep.SERP_MAPS, params)

    async def keyword_volume(
        self,
        keywords: list[str],
        location_code: int,
    ) -> APIResponse:
        params = {"keywords": keywords, "location_code": location_code}
        return await self._queued_request(ep.KEYWORD_VOLUME, params)

    async def keyword_suggestions(
        self,
        keyword: str,
        location_name: str = DFS_DEFAULT_LOCATION_NAME,
        limit: int = 50,
        language_code: str = DFS_DEFAULT_LANGUAGE_CODE,
    ) -> APIResponse:
        payload = [
            {
                "keyword": keyword,
                "location_name": location_name,
                "language_code": language_code,
                "limit": limit,
            }
        ]
        return await self._live_request(ep.KEYWORD_SUGGESTIONS, payload)

    async def business_listings(
        self,
        category: str,
        location_code: int,
        limit: int = 100,
    ) -> APIResponse:
        payload = [
            {
                "categories": [category],
                "location_code": location_code,
                "limit": limit,
            }
        ]
        return await self._live_request(
            ep.BUSINESS_LISTINGS,
            payload,
            cache_params={"category": category, "location_code": location_code, "limit": limit},
        )

    async def google_reviews(
        self,
        keyword: str,
        location_code: int,
        depth: int = 20,
    ) -> APIResponse:
        params = {"keyword": keyword, "location_code": location_code, "depth": depth}
        return await self._queued_request(ep.GOOGLE_REVIEWS, params)

    async def google_my_business_info(
        self,
        keyword: str,
        location_code: int,
    ) -> APIResponse:
        payload = [{"keyword": keyword, "location_code": location_code}]
        return await self._live_request(ep.GOOGLE_MY_BUSINESS_INFO, payload)

    async def backlinks_summary(self, target: str) -> APIResponse:
        payload = [{"target": target}]
        return await self._live_request(ep.BACKLINKS_SUMMARY, payload)

    async def lighthouse(self, url: str) -> APIResponse:
        params = {"url": url}
        return await self._queued_request(ep.LIGHTHOUSE, params)

    # -- Internal: queue and live flows --------------------------------------

    async def _queued_request(
        self,
        endpoint: ep.Endpoint,
        params: dict[str, Any],
    ) -> APIResponse:
        """Standard-queue flow: POST task → poll GET until ready."""
        cached = self._cache.get(endpoint.post_path, params)
        if cached is not None:
            self._tracker.record(
                endpoint=endpoint.post_path,
                task_id="cached",
                cost=0,
                cached=True,
                latency_ms=0,
                parameters=params,
            )
            return APIResponse(status="ok", data=cached, cost=0, cached=True)

        start = time.monotonic()
        post_body = await self._post(endpoint.post_path, [params])
        if post_body is None:
            return self._error_response("POST failed after retries", start)

        task = self._extract_task(post_body)
        if task is None:
            return self._error_response("No task in POST response", start)

        if task.get("status_code", 0) >= 40000:
            return self._task_error(task, start)

        task_id = task["id"]
        cost = task.get("cost", endpoint.cost_per_call)

        if endpoint.get_path is None:
            # Live-like endpoint returned inline
            data = task.get("result")
            ms = self._elapsed_ms(start)
            self._cache.put(endpoint.post_path, params, data)
            self._tracker.record(endpoint.post_path, task_id, cost, False, ms, params)
            return APIResponse(status="ok", data=data, cost=cost, latency_ms=ms, task_id=task_id)

        # Poll for results
        get_path = endpoint.get_path.format(task_id=task_id)
        elapsed = 0.0
        while elapsed < DFS_QUEUE_MAX_WAIT:
            await asyncio.sleep(DFS_QUEUE_POLL_INTERVAL)
            elapsed = time.monotonic() - start

            get_body = await self._post(get_path, None, method="GET")
            if get_body is None:
                continue
            result_task = self._extract_task(get_body)
            if result_task is None:
                continue
            if result_task.get("status_code", 0) == 20100:
                continue  # still pending
            if result_task.get("status_code", 0) >= 40000:
                return self._task_error(result_task, start)

            data = result_task.get("result")
            ms = self._elapsed_ms(start)
            result_cost = result_task.get("cost", cost)
            self._cache.put(endpoint.post_path, params, data)
            self._tracker.record(endpoint.post_path, task_id, result_cost, False, ms, params)
            return APIResponse(
                status="ok", data=data, cost=result_cost, latency_ms=ms, task_id=task_id
            )

        return self._error_response(f"Queue timeout after {DFS_QUEUE_MAX_WAIT}s", start)

    async def _live_request(
        self,
        endpoint: ep.Endpoint,
        payload: list[dict[str, Any]],
        *,
        cache_params: dict[str, Any] | None = None,
    ) -> APIResponse:
        """Live-mode flow: single POST → immediate response."""
        cp = cache_params or (payload[0] if payload else {})
        cached = self._cache.get(endpoint.post_path, cp)
        if cached is not None:
            self._tracker.record(endpoint.post_path, "cached", 0, True, 0, cp)
            return APIResponse(status="ok", data=cached, cost=0, cached=True)

        start = time.monotonic()
        body = await self._post(endpoint.post_path, payload)
        if body is None:
            return self._error_response("POST failed after retries", start)

        task = self._extract_task(body)
        if task is None:
            # Some endpoints (like locations) return result directly
            tasks = body.get("tasks", [])
            first = tasks[0] if tasks and isinstance(tasks[0], dict) else {}
            data = first.get("result", body)
            ms = self._elapsed_ms(start)
            self._cache.put(endpoint.post_path, cp, data)
            self._tracker.record(endpoint.post_path, "direct", 0, False, ms, cp)
            return APIResponse(status="ok", data=data, cost=0, latency_ms=ms)

        if task.get("status_code", 0) >= 40000:
            return self._task_error(task, start)

        data = task.get("result")
        cost = task.get("cost", endpoint.cost_per_call)
        task_id = task.get("id", "unknown")
        ms = self._elapsed_ms(start)
        self._cache.put(endpoint.post_path, cp, data)
        self._tracker.record(endpoint.post_path, task_id, cost, False, ms, cp)
        return APIResponse(status="ok", data=data, cost=cost, latency_ms=ms, task_id=task_id)

    # -- Internal: HTTP layer ------------------------------------------------

    async def _post(
        self,
        path: str,
        payload: list[dict[str, Any]] | None,
        *,
        method: str = "POST",
    ) -> dict[str, Any] | None:
        """POST (or GET) with retry logic. Returns parsed JSON or None."""
        for attempt in range(DFS_MAX_RETRIES):
            try:
                return await self._raw_post(path, payload, method=method)
            except Exception:
                logger.warning("DFS request to %s failed (attempt %d)", path, attempt + 1)
                if attempt < DFS_MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
        return None

    async def _raw_post(
        self,
        path: str,
        payload: list[dict[str, Any]] | None,
        *,
        method: str = "POST",
    ) -> dict[str, Any]:
        await self._rate_limiter.acquire()
        url = self._base_url + path
        headers = {"Authorization": self._auth_header, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as http:
            if method == "GET":
                resp = await http.get(url, headers=headers)
            else:
                resp = await http.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    # -- Internal: response helpers ------------------------------------------

    @staticmethod
    def _extract_task(body: dict[str, Any]) -> dict[str, Any] | None:
        tasks = body.get("tasks", [])
        return tasks[0] if tasks else None

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        return int((time.monotonic() - start) * 1000)

    @staticmethod
    def _error_response(msg: str, start: float) -> APIResponse:
        return APIResponse(
            status="error",
            error=msg,
            latency_ms=int((time.monotonic() - start) * 1000),
        )

    @staticmethod
    def _task_error(task: dict[str, Any], start: float) -> APIResponse:
        return APIResponse(
            status="error",
            error=task.get("status_message", "Unknown task error"),
            task_id=task.get("id"),
            latency_ms=int((time.monotonic() - start) * 1000),
        )
