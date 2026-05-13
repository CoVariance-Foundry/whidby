#!/usr/bin/env python3
"""Architectural lint: verify src/domain/ has no infrastructure imports.

Exit code: 0 if clean, 1 if violations found.
"""
import ast
import sys
from pathlib import Path

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

BANNED_ATTRS = [
    ("os", "environ"),
    ("os", "getenv"),
]

DOMAIN_ROOT = Path("src/domain")


def check_file(filepath: Path) -> list[str]:
    violations = []
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        violations.append(f"{filepath}:{e.lineno}: SyntaxError: {e.msg}")
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for banned in BANNED_PREFIXES:
                    if alias.name.startswith(banned):
                        violations.append(
                            f"{filepath}:{node.lineno}: "
                            f"Banned import '{alias.name}' "
                            f"(domain must not import from {banned})"
                        )

        if isinstance(node, ast.ImportFrom) and node.module:
            for banned in BANNED_PREFIXES:
                if node.module.startswith(banned):
                    violations.append(
                        f"{filepath}:{node.lineno}: "
                        f"Banned import 'from {node.module}' "
                        f"(domain must not import from {banned})"
                    )

        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            for mod, attr in BANNED_ATTRS:
                if node.value.id == mod and node.attr == attr:
                    violations.append(
                        f"{filepath}:{node.lineno}: "
                        f"Banned usage '{mod}.{attr}' "
                        f"(domain must not read environment variables)"
                    )

    return violations


def main() -> int:
    if not DOMAIN_ROOT.exists():
        print(f"Domain root {DOMAIN_ROOT} does not exist. Skipping.")
        return 0

    all_violations = []
    for pyfile in sorted(DOMAIN_ROOT.rglob("*.py")):
        all_violations.extend(check_file(pyfile))

    if all_violations:
        print(f"\n{'='*60}")
        print(f"ARCHITECTURAL VIOLATION: {len(all_violations)} banned import(s) in src/domain/")
        print(f"{'='*60}\n")
        for v in all_violations:
            print(f"  ✗ {v}")
        print(f"\nThe domain layer must depend only on:")
        print(f"  - Python stdlib")
        print(f"  - src.domain.* (internal)")
        print(f"  - src.scoring.* (pure scoring math)")
        print(f"  - src.classification.* (pure classification)")
        print(f"\nInfrastructure access goes through Protocol interfaces in src/domain/ports.py")
        return 1

    file_count = len(list(DOMAIN_ROOT.rglob("*.py")))
    print(f"✓ Domain layer is clean: {file_count} files checked, 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
