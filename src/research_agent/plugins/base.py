"""ToolPlugin ABC and PluginRegistry for modular tool loading.

Each plugin encapsulates a set of related tools with Anthropic-compatible
schema definitions and a dispatch method for execution.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ToolPlugin(ABC):
    """Base class for research agent tool plugins.

    Subclasses declare their tools via ``tool_definitions()`` and handle
    execution via ``execute()``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier string."""

    @abstractmethod
    def tool_definitions(self) -> list[dict[str, Any]]:
        """Return Anthropic-format tool schema dicts.

        Each dict must have ``name``, ``description``, and ``input_schema`` keys
        following the Anthropic tool-use JSON Schema convention.
        """

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call and return a result dict.

        Args:
            tool_name: Name of the tool to execute (must match a name from
                ``tool_definitions()``).
            arguments: Input arguments matching the tool's ``input_schema``.

        Returns:
            Result dict. Should include ``cost_usd`` (float) when the tool
            incurs API cost.

        Raises:
            KeyError: If *tool_name* is not provided by this plugin.
        """


class PluginRegistry:
    """Central catalog of loaded plugins and their tools.

    Resolves tool names to the appropriate plugin for execution and
    enforces uniqueness of both plugin names and tool names.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, ToolPlugin] = {}
        self._tool_map: dict[str, str] = {}

    def register(self, plugin: ToolPlugin) -> None:
        """Register a plugin. Raises on name or tool-name collision.

        Args:
            plugin: A concrete ``ToolPlugin`` instance.

        Raises:
            ValueError: If the plugin name is already registered or any of its
                tool names collide with an existing tool.
        """
        if plugin.name in self._plugins:
            raise ValueError(
                f"Plugin name '{plugin.name}' is already registered"
            )

        for tool_def in plugin.tool_definitions():
            tool_name = tool_def["name"]
            if tool_name in self._tool_map:
                existing = self._tool_map[tool_name]
                raise ValueError(
                    f"Tool name '{tool_name}' from plugin '{plugin.name}' "
                    f"collides with plugin '{existing}'"
                )

        self._plugins[plugin.name] = plugin
        for tool_def in plugin.tool_definitions():
            self._tool_map[tool_def["name"]] = plugin.name

    def register_safe(self, plugin: ToolPlugin) -> bool:
        """Register a plugin, catching and logging errors on failure.

        Args:
            plugin: A concrete ``ToolPlugin`` instance.

        Returns:
            True if registration succeeded, False otherwise.
        """
        try:
            self.register(plugin)
            return True
        except Exception:
            try:
                plugin_name = plugin.name
            except Exception:
                plugin_name = type(plugin).__name__
            logger.error(
                "Failed to register plugin '%s'", plugin_name, exc_info=True
            )
            return False

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return merged tool definitions from all registered plugins."""
        definitions: list[dict[str, Any]] = []
        for plugin in self._plugins.values():
            definitions.extend(plugin.tool_definitions())
        return definitions

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route a tool call to the correct plugin.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Input arguments for the tool.

        Returns:
            Result dict from the plugin's ``execute()`` method.

        Raises:
            KeyError: If *tool_name* is not registered.
        """
        if tool_name not in self._tool_map:
            raise KeyError(f"Unknown tool: '{tool_name}'")
        plugin_name = self._tool_map[tool_name]
        return self._plugins[plugin_name].execute(tool_name, arguments)

    def list_plugins(self) -> list[str]:
        """Return sorted list of registered plugin names."""
        return sorted(self._plugins.keys())
