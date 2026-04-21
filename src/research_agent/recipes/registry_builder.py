"""Factory for the global :class:`RecipeRegistry`.

Phase 1 ships exactly one recipe (``market_opportunity``); Phase 2+ will
register additional playbooks here. Keeping the builder trivial so new
recipes become one-line additions.
"""

from __future__ import annotations

from src.research_agent.recipes.base import RecipeRegistry
from src.research_agent.recipes.playbooks.market_opportunity import (
    RECIPE as MARKET_OPPORTUNITY,
)


def build_recipe_registry() -> RecipeRegistry:
    """Return a :class:`RecipeRegistry` pre-loaded with all built-in recipes."""
    registry = RecipeRegistry()
    registry.register(MARKET_OPPORTUNITY)
    return registry
