"""Token usage and cost tracking across LLM calls."""

from __future__ import annotations


# Approximate per-token pricing (USD) for Anthropic models, input/output
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-20250514": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude-haiku-4-5-20251001": (0.80 / 1_000_000, 4.0 / 1_000_000),
}
_DEFAULT_PRICING = (3.0 / 1_000_000, 15.0 / 1_000_000)


class TokenTracker:
    """Accumulates token usage and estimated cost across calls."""

    def __init__(self) -> None:
        self._total_input: int = 0
        self._total_output: int = 0
        self._total_cost: float = 0.0
        self._call_count: int = 0

    def record(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record a completed call. Returns estimated cost in USD."""
        inp_price, out_price = _MODEL_PRICING.get(model, _DEFAULT_PRICING)
        cost = input_tokens * inp_price + output_tokens * out_price
        self._total_input += input_tokens
        self._total_output += output_tokens
        self._total_cost += cost
        self._call_count += 1
        return cost

    @property
    def total_tokens(self) -> int:
        return self._total_input + self._total_output

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost

    @property
    def call_count(self) -> int:
        return self._call_count
