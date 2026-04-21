"""Recipe dataclass and RecipeRegistry for cross-referenced SEO reports.

A *recipe* is a declarative playbook describing a cross-referenced research
workflow: which plugins must be present, which system prompt to hand Claude,
which Jinja template to render, and (optionally) a pure scoring function that
turns collected tool outputs into a deterministic scores dict.

The design mirrors ``src/research_agent/plugins/base.py``: a simple dataclass
to hold recipe metadata plus a registry with duplicate-id protection.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ScoringFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Recipe:
    """A declarative playbook for one cross-referenced SEO report.

    Attributes:
        recipe_id: Unique identifier, e.g. ``"market_opportunity"``.
        audience: Primary user cohort — one of ``"rank_and_rent"``,
            ``"agency"``, or ``"app_builder"``. Used by the UI to group recipes.
        required_plugins: Plugin ``name`` strings that MUST be registered for
            the recipe to run. A missing required plugin blocks execution.
        optional_plugins: Plugin names whose absence degrades the recipe
            output but does not block it.
        inputs_schema: JSON Schema dict describing the recipe's required
            runtime inputs. Shape matches the Anthropic tool ``input_schema``
            convention so the same dict can be forwarded to Claude if needed.
        system_prompt: The Claude system prompt used to orchestrate tool
            calls for this recipe.
        template_name: Filename of the Jinja template used to render the final
            report (e.g. ``"market_opportunity.html"``). Path resolution is
            handled by the report renderer, not this dataclass.
        scoring_fn: Optional pure function that takes collected tool outputs
            and returns a scores dict. ``None`` if the recipe has no
            deterministic scoring component.
    """

    recipe_id: str
    audience: str
    required_plugins: list[str]
    optional_plugins: list[str]
    inputs_schema: dict[str, Any]
    system_prompt: str
    template_name: str
    scoring_fn: ScoringFn | None = None


class RecipeRegistry:
    """Central catalog of registered recipes, keyed by ``recipe_id``.

    Mirrors the shape of ``PluginRegistry`` in
    ``src/research_agent/plugins/base.py``: recipes are registered by id,
    duplicates raise, lookups raise ``KeyError`` for unknown ids, and
    listings are sorted for stable UI rendering.
    """

    def __init__(self) -> None:
        self._recipes: dict[str, Recipe] = {}

    def register(self, recipe: Recipe) -> None:
        """Register *recipe*. Raises ``ValueError`` on duplicate ``recipe_id``.

        Args:
            recipe: A concrete :class:`Recipe` instance.

        Raises:
            ValueError: If ``recipe.recipe_id`` is already registered.
        """
        if recipe.recipe_id in self._recipes:
            raise ValueError(
                f"Recipe id '{recipe.recipe_id}' is already registered"
            )
        self._recipes[recipe.recipe_id] = recipe

    def get(self, recipe_id: str) -> Recipe:
        """Return the recipe registered under *recipe_id*.

        Raises:
            KeyError: If *recipe_id* is not registered.
        """
        if recipe_id not in self._recipes:
            raise KeyError(f"Unknown recipe: '{recipe_id}'")
        return self._recipes[recipe_id]

    def list_recipes(self) -> list[str]:
        """Return a sorted list of registered recipe ids."""
        return sorted(self._recipes.keys())

    def list_by_audience(self, audience: str) -> list[Recipe]:
        """Return all recipes whose ``audience`` matches *audience*.

        Results are returned in ``recipe_id`` order for UI stability.
        """
        return [
            self._recipes[rid]
            for rid in sorted(self._recipes)
            if self._recipes[rid].audience == audience
        ]
