"""Mock Anthropic API responses for LLM client unit tests."""

import json

KEYWORD_EXPANSION_JSON = json.dumps({
    "niche": "plumber",
    "expanded_keywords": [
        {"keyword": "plumber near me", "tier": 1, "intent": "transactional", "source": "llm", "aio_risk": "low"},
        {"keyword": "emergency plumber", "tier": 2, "intent": "transactional", "source": "llm", "aio_risk": "low"},
        {"keyword": "best plumber in phoenix", "tier": 2, "intent": "commercial", "source": "llm", "aio_risk": "low"},
        {"keyword": "drain cleaning", "tier": 2, "intent": "transactional", "source": "llm", "aio_risk": "low"},
        {"keyword": "water heater repair", "tier": 2, "intent": "transactional", "source": "llm", "aio_risk": "low"},
    ],
    "total_keywords": 5,
    "actionable_keywords": 5,
    "informational_keywords_excluded": 0,
    "expansion_confidence": "high",
})

INTENT_TRANSACTIONAL_JSON = json.dumps({
    "intent": "transactional",
})

INTENT_INFORMATIONAL_JSON = json.dumps({
    "intent": "informational",
})

MALFORMED_JSON = "not valid json {{"

AUDIT_COPY_TEXT = (
    "Joe's Plumbing has 3 critical website issues that are costing them leads. "
    "Their site loads in 8.2 seconds (vs. industry average of 3.1s), lacks mobile "
    "optimization, and has no structured data markup."
)


def make_anthropic_message(text: str, input_tokens: int = 500, output_tokens: int = 750):
    """Build a mock object mimicking anthropic's Message response."""

    class _Usage:
        def __init__(self, inp: int, out: int):
            self.input_tokens = inp
            self.output_tokens = out

    class _TextBlock:
        def __init__(self, t: str):
            self.type = "text"
            self.text = t

    class _Message:
        def __init__(self, t: str, inp: int, out: int):
            self.id = "msg_mock_001"
            self.type = "message"
            self.role = "assistant"
            self.content = [_TextBlock(t)]
            self.model = "claude-sonnet-4-20250514"
            self.stop_reason = "end_turn"
            self.usage = _Usage(inp, out)

    return _Message(text, input_tokens, output_tokens)
