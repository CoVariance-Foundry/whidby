"""M8 orchestration for classification and guidance generation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from src.classification.ai_exposure import classify_ai_exposure
from src.classification.difficulty_tier import compute_difficulty_tier
from src.classification.serp_archetype import classify_serp_archetype
from src.classification.templates.guidance_templates import AI_RESILIENCE_NOTES, GUIDANCE_TEMPLATES
from src.classification.types import (
    AIExposure,
    ClassificationGuidanceBundle,
    ClassificationInput,
    DifficultyTier,
    GuidanceBundle,
)

logger = logging.getLogger(__name__)

_GUIDANCE_SYSTEM = (
    "You are a local SEO strategy assistant. Keep guidance concise, practical, and"
    " aligned with provided classifications. Do not contradict archetype, AI exposure,"
    " or difficulty tier."
)


async def classify_and_generate_guidance(
    classification_input: ClassificationInput,
    llm_client: Any | None,
) -> ClassificationGuidanceBundle:
    """Classify one metro and generate structured guidance.

    Args:
        classification_input: Input envelope including niche, metro, signals, and scores.
        llm_client: M3-compatible LLM client exposing async `generate(...)`.

    Returns:
        Classification and guidance bundle for downstream consumers.

    Raises:
        ValueError: If required input fields are missing or malformed.
    """
    _validate_input(classification_input)

    signals = classification_input["signals"]
    scores = classification_input["scores"]
    strategy_profile = str(classification_input.get("strategy_profile", "balanced"))

    archetype, rule_id = classify_serp_archetype(signals)
    ai_exposure = classify_ai_exposure(signals)
    difficulty_tier, combined_comp, resolved_weights = compute_difficulty_tier(
        scores=scores,
        strategy_profile=strategy_profile,
        signals=signals,
    )

    context = _build_template_context(
        classification_input=classification_input,
        archetype=archetype,
        ai_exposure=ai_exposure,
        difficulty_tier=difficulty_tier,
        combined_comp=combined_comp,
    )
    guidance, fallback_reason = await _build_guidance(
        llm_client=llm_client,
        context=context,
        archetype=archetype,
        ai_exposure=ai_exposure,
        difficulty_tier=difficulty_tier,
    )

    return {
        "serp_archetype": archetype,
        "ai_exposure": ai_exposure,
        "difficulty_tier": difficulty_tier,
        "guidance": guidance,
        "metadata": {
            "serp_rule_id": rule_id,
            "difficulty_inputs": {
                "organic_competition": _to_float(scores.get("organic_competition")),
                "local_competition": _to_float(scores.get("local_competition")),
                "resolved_weights": resolved_weights,
            },
            "guidance_fallback_reason": fallback_reason,
        },
    }


def _validate_input(classification_input: Mapping[str, Any]) -> None:
    """Validate required input contract fields including nested numerics."""
    required_fields = ("niche", "metro_name", "signals", "scores")
    missing = [field for field in required_fields if field not in classification_input]
    if missing:
        raise ValueError(f"classification_input missing required field(s): {', '.join(missing)}")

    signals = classification_input.get("signals")
    scores = classification_input.get("scores")
    if not isinstance(signals, Mapping):
        raise ValueError("classification_input.signals must be a mapping")
    if not isinstance(scores, Mapping):
        raise ValueError("classification_input.scores must be a mapping")

    _validate_score_fields(scores)
    _validate_signal_fields(signals)


def _validate_score_fields(scores: Mapping[str, Any]) -> None:
    """Validate required numeric fields in M7 scores."""
    for field in ("organic_competition", "local_competition"):
        if field not in scores:
            raise ValueError(f"scores missing required field: {field}")
        _require_numeric(scores[field], f"scores.{field}")


def _validate_signal_fields(signals: Mapping[str, Any]) -> None:
    """Validate required nested signal sections and numeric fields."""
    _require_section(signals, "organic_competition", "signals")
    organic = signals["organic_competition"]
    for field in ("aggregator_count", "local_biz_count", "avg_top5_da"):
        _require_numeric(organic.get(field), f"signals.organic_competition.{field}")

    _require_section(signals, "local_competition", "signals")
    local = signals["local_competition"]
    for field in ("local_pack_review_count_avg", "review_velocity_avg"):
        _require_numeric(local.get(field), f"signals.local_competition.{field}")

    _require_section(signals, "ai_resilience", "signals")
    ai = signals["ai_resilience"]
    _require_numeric(ai.get("aio_trigger_rate"), "signals.ai_resilience.aio_trigger_rate")


def _require_section(parent: Mapping[str, Any], key: str, parent_name: str) -> None:
    """Require a nested mapping section exists."""
    if key not in parent or not isinstance(parent[key], Mapping):
        raise ValueError(f"{parent_name}.{key} must be a mapping with required fields")


def _require_numeric(value: Any, path: str) -> None:
    """Require a value to be present and coercible to float."""
    if value is None:
        raise ValueError(f"{path} is required but missing")
    try:
        float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{path} must be numeric, got {type(value).__name__}: {value!r}")


def _build_template_context(
    *,
    classification_input: Mapping[str, Any],
    archetype: str,
    ai_exposure: str,
    difficulty_tier: str,
    combined_comp: float,
) -> dict[str, Any]:
    """Build stable format context for template and prompt rendering."""
    signals = classification_input["signals"]
    organic = _mapping(signals.get("organic_competition"))
    local = _mapping(signals.get("local_competition"))
    ai = _mapping(signals.get("ai_resilience"))

    return {
        "niche": str(classification_input["niche"]),
        "metro_name": str(classification_input["metro_name"]),
        "serp_archetype": archetype,
        "ai_exposure": ai_exposure,
        "difficulty_tier": difficulty_tier,
        "combined_competition": round(combined_comp, 2),
        "aggregator_count": int(_to_float(organic.get("aggregator_count"))),
        "local_pack_review_count_avg": round(_to_float(local.get("local_pack_review_count_avg")), 1),
        "review_velocity_avg": round(_to_float(local.get("review_velocity_avg")), 2),
        "aio_trigger_rate": round(_to_float(ai.get("aio_trigger_rate")) * 100, 1),
    }


async def _build_guidance(
    *,
    llm_client: Any | None,
    context: Mapping[str, Any],
    archetype: str,
    ai_exposure: AIExposure,
    difficulty_tier: DifficultyTier,
) -> tuple[GuidanceBundle, str | None]:
    """Build guidance payload using template baseline and optional LLM enhancement."""
    template = GUIDANCE_TEMPLATES[(archetype, difficulty_tier)]
    rendered_strategy = template["strategy"].format(**context)
    ai_note = AI_RESILIENCE_NOTES[ai_exposure]

    base_guidance: GuidanceBundle = {
        "headline": template["headline"],
        "strategy": rendered_strategy,
        "priority_actions": list(template["priority_actions"]),
        "ai_resilience_note": ai_note,
        "guidance_status": "fallback_template",
    }

    if llm_client is None or not hasattr(llm_client, "generate"):
        return base_guidance, "llm_client_unavailable"

    prompt = _build_prompt(context=context, base_guidance=base_guidance)
    try:
        result = await llm_client.generate(
            system=_GUIDANCE_SYSTEM,
            prompt=prompt,
            temperature=0.2,
            max_tokens=250,
        )
    except Exception as exc:
        logger.error("Guidance generation failed", exc_info=True)
        return base_guidance, str(exc)

    if not getattr(result, "success", False):
        return base_guidance, str(getattr(result, "error", "llm_generation_failed"))

    llm_text = _normalize_llm_text(getattr(result, "data", None))
    if not llm_text:
        return base_guidance, "empty_llm_response"

    contradiction = _check_guidance_consistency(
        llm_text=llm_text,
        archetype=archetype,
        ai_exposure=ai_exposure,
        difficulty_tier=difficulty_tier,
    )
    if contradiction:
        logger.warning("LLM guidance contradicts classification: %s", contradiction)
        return base_guidance, f"contradiction_guardrail: {contradiction}"

    enhanced = dict(base_guidance)
    enhanced["strategy"] = f"{base_guidance['strategy']} {llm_text}".strip()
    enhanced["guidance_status"] = "generated"
    return enhanced, None


_TIER_CONTRADICTION_TERMS: dict[str, set[str]] = {
    "EASY": {"very hard", "extremely difficult", "not recommended", "avoid this market"},
    "MODERATE": {"extremely difficult", "not recommended", "avoid this market"},
    "HARD": {"quick win", "easy win", "no competition", "rank immediately"},
    "VERY_HARD": {"quick win", "easy win", "no competition", "rank immediately", "effortless"},
}

_EXPOSURE_CONTRADICTION_TERMS: dict[str, set[str]] = {
    "AI_SHIELDED": {"high ai risk", "ai disruption", "ai will replace", "heavily exposed to ai"},
    "AI_EXPOSED": {"no ai risk", "ai-proof", "immune to ai", "zero ai exposure"},
}


def _check_guidance_consistency(
    *,
    llm_text: str,
    archetype: str,
    ai_exposure: str,
    difficulty_tier: str,
) -> str | None:
    """Return a reason string if LLM text contradicts classification, else None."""
    lower = llm_text.lower()

    tier_terms = _TIER_CONTRADICTION_TERMS.get(difficulty_tier, set())
    for term in tier_terms:
        if term in lower:
            return f"difficulty_tier={difficulty_tier} contradicted by '{term}'"

    exposure_terms = _EXPOSURE_CONTRADICTION_TERMS.get(ai_exposure, set())
    for term in exposure_terms:
        if term in lower:
            return f"ai_exposure={ai_exposure} contradicted by '{term}'"

    return None


def _build_prompt(*, context: Mapping[str, Any], base_guidance: Mapping[str, Any]) -> str:
    """Build bounded prompt for concise guidance refinement."""
    return (
        "Refine the strategy text without changing the underlying recommendation.\n"
        f"Niche: {context['niche']}\n"
        f"Metro: {context['metro_name']}\n"
        f"Archetype: {context['serp_archetype']}\n"
        f"AI Exposure: {context['ai_exposure']}\n"
        f"Difficulty: {context['difficulty_tier']}\n"
        f"Combined Competition: {context['combined_competition']}\n"
        f"Base Strategy: {base_guidance['strategy']}\n"
        "Return one concise sentence (max 35 words)."
    )


def _normalize_llm_text(data: Any) -> str:
    """Normalize free-form LLM output into a short single line."""
    text = str(data or "").strip().replace("\n", " ")
    if len(text) > 220:
        return text[:220].rstrip() + "..."
    return text


def _mapping(value: Any) -> Mapping[str, Any]:
    """Coerce unknown values into dict-like views."""
    if isinstance(value, Mapping):
        return value
    return {}


def _to_float(value: Any) -> float:
    """Safely coerce numeric-like values to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
