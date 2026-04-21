"""Concrete recipe playbooks.

This package holds the actual :class:`~src.research_agent.recipes.base.Recipe`
instances that a :class:`RecipeRegistry` registers at startup. Each module
exposes exactly one ``RECIPE`` value so the registry-wiring site can do a
flat import per playbook.
"""

from __future__ import annotations

from src.research_agent.recipes.playbooks.market_opportunity import (
    RECIPE as MARKET_OPPORTUNITY_RECIPE,
)

__all__ = ["MARKET_OPPORTUNITY_RECIPE"]
