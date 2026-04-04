"""Thin Anthropic SDK wrapper for all LLM inference. (M3)

This is NOT an agent framework — it's a utility library that calls Claude
at specific pipeline points with structured prompts and validated output.
"""

from __future__ import annotations

import logging
import os

import anthropic

from src.config.constants import CLASSIFICATION_MODEL, DEFAULT_MODEL

from .output_parsers import parse_json_response
from .prompts import intent_classification, keyword_expansion
from .token_tracker import TokenTracker
from .types import LLMResult

logger = logging.getLogger(__name__)


class LLMClient:
    """Async-friendly wrapper around the Anthropic Python SDK.

    Args:
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        default_model: Model for most tasks.
        classification_model: Model for lightweight classification.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        default_model: str = DEFAULT_MODEL,
        classification_model: str = CLASSIFICATION_MODEL,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._anthropic = anthropic.Anthropic(api_key=self._api_key)
        self._default_model = default_model
        self._classification_model = classification_model
        self.tracker = TokenTracker()

    # -- High-level API methods ----------------------------------------------

    async def keyword_expansion(self, niche: str) -> LLMResult:
        """Expand a niche keyword into a classified set. (Algo Spec §4.2)"""
        return await self._structured_call(
            system=keyword_expansion.SYSTEM,
            prompt=keyword_expansion.build_prompt(niche),
            model=self._default_model,
            temperature=0,
            max_tokens=2048,
        )

    async def classify_intent(self, query: str) -> str:
        """Classify a single query's search intent. Returns the intent string.

        Falls back to "commercial" on error.
        """
        result = await self._structured_call(
            system=intent_classification.SYSTEM,
            prompt=intent_classification.build_prompt(query),
            model=self._classification_model,
            temperature=0,
            max_tokens=64,
        )
        if result.success and isinstance(result.data, dict):
            return result.data.get("intent", "commercial")
        return "commercial"

    async def generate(
        self,
        system: str,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResult:
        """Free-form text generation (e.g. audit copy, guidance)."""
        return await self._raw_call(
            system=system,
            prompt=prompt,
            model=model or self._default_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # -- Internal: call patterns ---------------------------------------------

    async def _structured_call(
        self,
        system: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResult:
        """Call Claude and parse the response as JSON."""
        raw = await self._raw_call(system, prompt, model, temperature, max_tokens)
        if not raw.success:
            return raw

        data, err = parse_json_response(raw.data)
        if err is not None:
            return LLMResult(
                success=False,
                error=err,
                tokens_used=raw.tokens_used,
                cost_usd=raw.cost_usd,
            )
        return LLMResult(
            success=True,
            data=data,
            tokens_used=raw.tokens_used,
            cost_usd=raw.cost_usd,
        )

    async def _raw_call(
        self,
        system: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResult:
        """Execute a single Claude API call with error handling and tracking."""
        try:
            message = self._anthropic.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            logger.error("LLM call failed: %s", e, exc_info=True)
            return LLMResult(success=False, error=str(e))

        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        cost = self.tracker.record(model, input_tokens, output_tokens)
        text = message.content[0].text if message.content else ""

        return LLMResult(
            success=True,
            data=text,
            tokens_used=input_tokens + output_tokens,
            cost_usd=cost,
        )
