"""Template matrix for M8 guidance generation."""

from __future__ import annotations

from src.classification.types import AIExposure, DifficultyTier, GuidanceTemplate, SerpArchetype

ARCHETYPE_LABELS: dict[SerpArchetype, str] = {
    "AGGREGATOR_DOMINATED": "Aggregator dominated",
    "LOCAL_PACK_FORTIFIED": "Local pack fortified",
    "LOCAL_PACK_ESTABLISHED": "Local pack established",
    "LOCAL_PACK_VULNERABLE": "Local pack vulnerable",
    "FRAGMENTED_WEAK": "Fragmented weak",
    "FRAGMENTED_COMPETITIVE": "Fragmented competitive",
    "BARREN": "Barren",
    "MIXED": "Mixed",
}

DIFFICULTY_NOTES: dict[DifficultyTier, str] = {
    "EASY": "Expect a short runway if execution is consistent.",
    "MODERATE": "Plan for sustained execution and operational consistency.",
    "HARD": "Expect heavy competition; differentiation and persistence are required.",
    "VERY_HARD": "Only pursue if you have strong operational or authority advantages.",
}

ARCHETYPE_ACTIONS: dict[SerpArchetype, list[str]] = {
    "AGGREGATOR_DOMINATED": [
        "Target long-tail service pages that directories under-serve.",
        "Differentiate local proof signals with reviews and GBP freshness.",
    ],
    "LOCAL_PACK_FORTIFIED": [
        "Invest in sustained review generation before aggressive expansion.",
        "Build GBP completeness and posting cadence to narrow trust gaps.",
    ],
    "LOCAL_PACK_ESTABLISHED": [
        "Prioritize GBP and local landing pages before broad content expansion.",
        "Close review and profile completeness gaps against incumbents.",
    ],
    "LOCAL_PACK_VULNERABLE": [
        "Launch GBP-first and service-page coverage for fast local visibility.",
        "Capture early momentum with consistent review acquisition.",
    ],
    "FRAGMENTED_WEAK": [
        "Out-execute with clearer offers and stronger local trust assets.",
        "Create service clusters that cover high-intent sub-services.",
    ],
    "FRAGMENTED_COMPETITIVE": [
        "Focus on niche specialization and stronger conversion assets.",
        "Sequence link-building and GBP improvements in parallel.",
    ],
    "BARREN": [
        "Validate demand quality before scaling content and operations.",
        "Move quickly on core pages while competition remains low.",
    ],
    "MIXED": [
        "Prioritize gaps where incumbents show weak local execution.",
        "Use a balanced SEO + GBP plan and iterate from live signals.",
    ],
}

AI_RESILIENCE_NOTES: dict[AIExposure, str | None] = {
    "AI_SHIELDED": None,
    "AI_MINIMAL": None,
    "AI_MODERATE": (
        "AI Overviews appear on a meaningful portion of queries; prioritize transactional"
        " and local-intent pages to protect click-through."
    ),
    "AI_EXPOSED": (
        "AI Overview exposure is high; lean on local-pack visibility and high-intent terms"
        " while avoiding broad informational content as a primary acquisition path."
    ),
}


def _build_template(
    archetype: SerpArchetype,
    difficulty: DifficultyTier,
) -> GuidanceTemplate:
    """Build one matrix entry for an archetype and difficulty tier."""
    label = ARCHETYPE_LABELS[archetype]
    headline = f"{label}: {difficulty.replace('_', ' ').title()} execution profile"
    strategy = (
        "{metro_name} in '{niche}' currently matches the "
        f"{label.lower()} pattern. {DIFFICULTY_NOTES[difficulty]}"
    )
    actions = [
        ARCHETYPE_ACTIONS[archetype][0],
        ARCHETYPE_ACTIONS[archetype][1],
        "Track monthly movement in competition signals before shifting strategy.",
    ]
    return {
        "headline": headline,
        "strategy": strategy,
        "priority_actions": actions,
    }


GUIDANCE_TEMPLATES: dict[tuple[SerpArchetype, DifficultyTier], GuidanceTemplate] = {
    (archetype, difficulty): _build_template(archetype, difficulty)
    for archetype in ARCHETYPE_LABELS
    for difficulty in DIFFICULTY_NOTES
}
