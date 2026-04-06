"""Plugin system for the research agent.

Provides a modular tool registry where each data source or capability
is encapsulated as a self-contained plugin.
"""

from src.research_agent.plugins.base import PluginRegistry, ToolPlugin

__all__ = ["PluginRegistry", "ToolPlugin"]
