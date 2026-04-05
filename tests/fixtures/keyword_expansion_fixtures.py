"""Fixtures and fakes for M4 keyword expansion tests."""

from __future__ import annotations

from copy import deepcopy

from src.clients.dataforseo.types import APIResponse
from src.clients.llm.types import LLMResult

LLM_EXPANSION_PAYLOAD = {
    "niche": "plumber",
    "expanded_keywords": [
        {"keyword": "Plumber", "tier": 1, "intent": "commercial", "source": "llm", "aio_risk": "moderate"},
        {
            "keyword": "plumber near me",
            "tier": 1,
            "intent": "transactional",
            "source": "llm",
            "aio_risk": "low",
        },
        {
            "keyword": "emergency plumber",
            "tier": 2,
            "intent": "transactional",
            "source": "llm",
            "aio_risk": "low",
        },
        {
            "keyword": "how to fix a leaky faucet",
            "tier": 3,
            "intent": "informational",
            "source": "llm",
            "aio_risk": "high",
        },
    ],
}

DFS_SUGGESTION_KEYWORDS = [
    "plumber near me",
    "drain cleaning",
    "24 hour plumber",
]


class FakeLLMClient:
    """Minimal async fake matching the M3 public API used by M4."""

    def __init__(
        self,
        *,
        expansion_payload: dict | None = None,
        expansion_success: bool = True,
        classify_map: dict[str, str] | None = None,
        raise_on_expand: bool = False,
        raise_on_classify: bool = False,
    ) -> None:
        self._expansion_payload = expansion_payload or deepcopy(LLM_EXPANSION_PAYLOAD)
        self._expansion_success = expansion_success
        self._classify_map = classify_map or {}
        self._raise_on_expand = raise_on_expand
        self._raise_on_classify = raise_on_classify

    async def keyword_expansion(self, niche: str) -> LLMResult:
        if self._raise_on_expand:
            raise RuntimeError("LLM unavailable")
        payload = deepcopy(self._expansion_payload)
        payload["niche"] = niche
        return LLMResult(success=self._expansion_success, data=payload)

    async def classify_intent(self, query: str) -> str:
        if self._raise_on_classify:
            raise RuntimeError("Intent classification unavailable")
        return self._classify_map.get(query, "commercial")


class FakeDataForSEOClient:
    """Minimal async fake matching the DataForSEO method used by M4."""

    def __init__(
        self,
        *,
        keywords: list[str] | None = None,
        status: str = "ok",
        raise_on_suggestions: bool = False,
    ) -> None:
        self._keywords = keywords or list(DFS_SUGGESTION_KEYWORDS)
        self._status = status
        self._raise_on_suggestions = raise_on_suggestions

    async def keyword_suggestions(
        self,
        keyword: str,
        location_name: str = "United States",
        limit: int = 50,
    ) -> APIResponse:
        if self._raise_on_suggestions:
            raise RuntimeError("DataForSEO unavailable")

        items = [{"keyword": kw} for kw in self._keywords[:limit]]
        data = [{"keyword": keyword, "location_name": location_name, "items": items}]
        return APIResponse(status=self._status, data=data)
