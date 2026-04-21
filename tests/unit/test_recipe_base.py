"""Tests for Recipe dataclass and RecipeRegistry."""

from __future__ import annotations

import pytest

from src.research_agent.recipes.base import Recipe, RecipeRegistry


def _make_recipe(
    recipe_id: str = "market_opportunity",
    audience: str = "rank_and_rent",
    required_plugins: list[str] | None = None,
    optional_plugins: list[str] | None = None,
    inputs_schema: dict | None = None,
    system_prompt: str = "You are a market opportunity analyst.",
    template_name: str = "market_opportunity.html",
    scoring_fn=None,
) -> Recipe:
    return Recipe(
        recipe_id=recipe_id,
        audience=audience,
        required_plugins=required_plugins or ["dataforseo"],
        optional_plugins=optional_plugins or [],
        inputs_schema=inputs_schema
        or {
            "type": "object",
            "properties": {"niche": {"type": "string"}},
            "required": ["niche"],
        },
        system_prompt=system_prompt,
        template_name=template_name,
        scoring_fn=scoring_fn,
    )


class TestRecipeConstruction:
    def test_recipe_instantiates_with_required_fields(self) -> None:
        recipe = _make_recipe()
        assert recipe.recipe_id == "market_opportunity"
        assert recipe.audience == "rank_and_rent"
        assert recipe.required_plugins == ["dataforseo"]
        assert recipe.optional_plugins == []
        assert recipe.inputs_schema["type"] == "object"
        assert recipe.system_prompt.startswith("You are")
        assert recipe.template_name == "market_opportunity.html"
        assert recipe.scoring_fn is None

    def test_recipe_accepts_scoring_fn(self) -> None:
        def score(outputs: dict) -> dict:
            return {"score": 1.0}

        recipe = _make_recipe(scoring_fn=score)
        assert recipe.scoring_fn is score
        assert recipe.scoring_fn({}) == {"score": 1.0}

    def test_recipe_accepts_optional_plugins(self) -> None:
        recipe = _make_recipe(optional_plugins=["serpapi"])
        assert recipe.optional_plugins == ["serpapi"]


class TestRecipeRegistry:
    def test_register_recipe(self) -> None:
        registry = RecipeRegistry()
        recipe = _make_recipe()
        registry.register(recipe)
        assert "market_opportunity" in registry.list_recipes()

    def test_duplicate_recipe_id_raises(self) -> None:
        registry = RecipeRegistry()
        registry.register(_make_recipe(recipe_id="dup"))
        with pytest.raises(ValueError, match="dup"):
            registry.register(_make_recipe(recipe_id="dup"))

    def test_get_returns_registered_recipe(self) -> None:
        registry = RecipeRegistry()
        recipe = _make_recipe(recipe_id="agency_audit", audience="agency")
        registry.register(recipe)
        retrieved = registry.get("agency_audit")
        assert retrieved is recipe

    def test_get_unknown_raises_key_error(self) -> None:
        registry = RecipeRegistry()
        with pytest.raises(KeyError, match="unknown"):
            registry.get("unknown")

    def test_list_recipes_returns_sorted(self) -> None:
        registry = RecipeRegistry()
        registry.register(_make_recipe(recipe_id="zebra"))
        registry.register(_make_recipe(recipe_id="alpha"))
        registry.register(_make_recipe(recipe_id="mango"))
        assert registry.list_recipes() == ["alpha", "mango", "zebra"]

    def test_list_by_audience_filters(self) -> None:
        registry = RecipeRegistry()
        registry.register(
            _make_recipe(recipe_id="r1", audience="rank_and_rent")
        )
        registry.register(_make_recipe(recipe_id="r2", audience="agency"))
        registry.register(
            _make_recipe(recipe_id="r3", audience="rank_and_rent")
        )
        registry.register(
            _make_recipe(recipe_id="r4", audience="app_builder")
        )

        rnr = registry.list_by_audience("rank_and_rent")
        assert {r.recipe_id for r in rnr} == {"r1", "r3"}

        agency = registry.list_by_audience("agency")
        assert [r.recipe_id for r in agency] == ["r2"]

        app_builder = registry.list_by_audience("app_builder")
        assert [r.recipe_id for r in app_builder] == ["r4"]

    def test_list_by_audience_empty_returns_empty_list(self) -> None:
        registry = RecipeRegistry()
        registry.register(_make_recipe(audience="rank_and_rent"))
        assert registry.list_by_audience("agency") == []
