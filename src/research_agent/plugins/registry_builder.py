"""Factory for the :class:`PluginRegistry` used by the :class:`RecipeRunner`.

Loads the three plugins recipes can reach for today --- DataForSEO, SerpAPI,
and Report --- via :meth:`PluginRegistry.register_safe` so one plugin
failing to construct does not break the others.

The :class:`ReportPlugin` is registered into the main registry (so Claude
can discover ``compose_report`` as a tool if a future recipe wants to call
it directly) AND returned separately because :class:`RecipeRunner` renders
the final HTML outside the tool-use loop.
"""

from __future__ import annotations

import logging

from src.research_agent.plugins.base import PluginRegistry
from src.research_agent.plugins.dataforseo_plugin import DataForSEOPlugin
from src.research_agent.plugins.report_plugin import ReportPlugin
from src.research_agent.plugins.serpapi_plugin import SerpAPIPlugin

logger = logging.getLogger(__name__)


def build_plugin_registry() -> tuple[PluginRegistry, ReportPlugin]:
    """Return ``(registry, report_plugin)`` ready for :class:`RecipeRunner`.

    ``report_plugin`` is returned separately because the runner calls it
    directly for the final render; registering it in the registry is
    defense-in-depth so Claude can see it as a tool if a recipe wants to
    invoke it mid-loop (no Phase 1 recipe does).
    """
    registry = PluginRegistry()
    registry.register_safe(DataForSEOPlugin())
    registry.register_safe(SerpAPIPlugin())

    report_plugin = ReportPlugin()
    registry.register_safe(report_plugin)

    return registry, report_plugin
