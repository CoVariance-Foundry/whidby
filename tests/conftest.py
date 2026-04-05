"""Shared pytest configuration and markers for the Widby test suite."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: requires real API calls (deselect with '-m \"not integration\"')",
    )
