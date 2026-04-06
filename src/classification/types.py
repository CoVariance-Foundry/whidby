"""Typed contracts for M8 classification and guidance."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

SerpArchetype = Literal[
    "AGGREGATOR_DOMINATED",
    "LOCAL_PACK_FORTIFIED",
    "LOCAL_PACK_ESTABLISHED",
    "LOCAL_PACK_VULNERABLE",
    "FRAGMENTED_WEAK",
    "FRAGMENTED_COMPETITIVE",
    "BARREN",
    "MIXED",
]

AIExposure = Literal["AI_SHIELDED", "AI_MINIMAL", "AI_MODERATE", "AI_EXPOSED"]
DifficultyTier = Literal["EASY", "MODERATE", "HARD", "VERY_HARD"]
GuidanceStatus = Literal["generated", "fallback_template"]
StrategyProfile = Literal["organic_first", "balanced", "local_dominant", "auto"]


class ResolvedWeights(TypedDict):
    """Resolved strategy profile weights used for difficulty tiering."""

    organic: float
    local: float


class DifficultyInputs(TypedDict):
    """Inputs captured for difficulty-tier traceability."""

    organic_competition: float
    local_competition: float
    resolved_weights: ResolvedWeights


class ClassificationMetadata(TypedDict):
    """Diagnostic metadata for debugging and downstream logging."""

    serp_rule_id: str
    difficulty_inputs: DifficultyInputs
    guidance_fallback_reason: str | None


class GuidanceBundle(TypedDict):
    """User-facing guidance payload."""

    headline: str
    strategy: str
    priority_actions: list[str]
    ai_resilience_note: str | None
    guidance_status: GuidanceStatus


class ClassificationGuidanceBundle(TypedDict):
    """Final M8 output bundle for one metro."""

    serp_archetype: SerpArchetype
    ai_exposure: AIExposure
    difficulty_tier: DifficultyTier
    guidance: GuidanceBundle
    metadata: ClassificationMetadata


class ClassificationInput(TypedDict):
    """Input envelope consumed by M8 classification and guidance orchestration."""

    niche: str
    metro_name: str
    signals: dict[str, Any]
    scores: dict[str, Any]
    strategy_profile: StrategyProfile | str


class GuidanceTemplate(TypedDict):
    """Template scaffold before LLM enhancement."""

    headline: str
    strategy: str
    priority_actions: list[str]
