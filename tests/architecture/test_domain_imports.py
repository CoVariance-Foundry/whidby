"""Architectural test: domain layer dependency rules."""
import ast
from pathlib import Path

DOMAIN_ROOT = Path("src/domain")

BANNED_PREFIXES = [
    "src.clients",
    "src.research_agent",
    "src.data",
    "supabase",
    "httpx",
    "openai",
    "anthropic",
    "dataforseo",
]


def test_domain_has_no_infrastructure_imports():
    """src/domain/ must not import from infrastructure or API layers."""
    violations = []

    for pyfile in sorted(DOMAIN_ROOT.rglob("*.py")):
        source = pyfile.read_text()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for banned in BANNED_PREFIXES:
                        if alias.name.startswith(banned):
                            violations.append(f"{pyfile}:{node.lineno}: import {alias.name}")

            if isinstance(node, ast.ImportFrom) and node.module:
                for banned in BANNED_PREFIXES:
                    if node.module.startswith(banned):
                        violations.append(f"{pyfile}:{node.lineno}: from {node.module}")

    assert violations == [], (
        f"Domain layer has {len(violations)} banned import(s):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_domain_does_not_read_env_vars():
    """src/domain/ must not use os.environ or os.getenv."""
    violations = []

    for pyfile in sorted(DOMAIN_ROOT.rglob("*.py")):
        source = pyfile.read_text()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "os" and node.attr in ("environ", "getenv"):
                    violations.append(f"{pyfile}:{node.lineno}: os.{node.attr}")

    assert violations == [], (
        f"Domain layer reads env vars in {len(violations)} place(s):\n"
        + "\n".join(f"  {v}" for v in violations)
    )
