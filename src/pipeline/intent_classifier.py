"""Intent classification helpers for M4 keyword expansion."""

from __future__ import annotations

from src.config.constants import M4_ALLOWED_INTENTS

INFORMATIONAL_PREFIXES = (
    "how to",
    "what is",
    "why ",
    "can i ",
    "do i ",
    "guide to",
    "tips for",
)
INFORMATIONAL_HINTS = ("tutorial", "checklist", "ideas", "examples")
TRANSACTIONAL_HINTS = (
    "near me",
    "emergency",
    "24 hour",
    "same day",
    "repair",
    "service",
    "services",
    "install",
    "replacement",
)
COMMERCIAL_HINTS = ("best", "top", "reviews", "cost", "price", "quote", "company")


def infer_intent_from_rules(query: str) -> str | None:
    """Return intent from deterministic keyword rules, if confidently inferred."""
    normalized = query.strip().lower()
    if not normalized:
        return None

    if any(normalized.startswith(prefix) for prefix in INFORMATIONAL_PREFIXES):
        return "informational"
    if any(hint in normalized for hint in INFORMATIONAL_HINTS):
        return "informational"
    if any(hint in normalized for hint in TRANSACTIONAL_HINTS):
        return "transactional"
    if any(hint in normalized for hint in COMMERCIAL_HINTS):
        return "commercial"
    return None


async def classify_keyword_intent(
    keyword: str,
    llm_client: object | None = None,
    llm_intent: str | None = None,
) -> str:
    """Classify intent using deterministic precedence.

    Order:
    1) Explicit LLM intent from structured payload (if valid)
    2) Rule-based intent detection
    3) LLM one-off classifier call
    4) Default fallback ("commercial")
    """
    if llm_intent in M4_ALLOWED_INTENTS:
        return llm_intent

    inferred = infer_intent_from_rules(keyword)
    if inferred is not None:
        return inferred

    if llm_client is not None and hasattr(llm_client, "classify_intent"):
        try:
            predicted = await llm_client.classify_intent(keyword)
            if predicted in M4_ALLOWED_INTENTS:
                return predicted
        except Exception:
            pass
    return "commercial"


def aio_risk_for_intent(intent: str) -> str:
    """Map intent label to AIO exposure risk bucket."""
    if intent == "transactional":
        return "low"
    if intent == "informational":
        return "high"
    return "moderate"


def is_actionable_intent(intent: str) -> bool:
    """Actionability policy used by M4 and downstream M5."""
    return intent in {"transactional", "commercial"}
