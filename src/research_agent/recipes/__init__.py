"""Recipe playbooks for cross-referenced SEO reports.

A *recipe* is a declarative workflow (system prompt + required plugins +
scoring function + Jinja template) that Claude orchestrates to produce a
cross-referenced report for a specific audience.
"""

from __future__ import annotations

from src.research_agent.recipes.base import Recipe, RecipeRegistry
from src.research_agent.recipes.scoring import (
    OPPORTUNITY_COMPONENTS,
    OPPORTUNITY_WEIGHTS,
    opportunity_score,
)

__all__ = [
    "OPPORTUNITY_COMPONENTS",
    "OPPORTUNITY_WEIGHTS",
    "Recipe",
    "RecipeRegistry",
    "opportunity_score",
]
