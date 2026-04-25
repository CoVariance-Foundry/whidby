# Phase 6: CI Layer Enforcement

**Objective:** Add automated checks that enforce the dependency rules defined in the architecture: `src/domain/` never imports from `src/clients/`, `src/research_agent/`, or `src/data/`. Make the architecture self-policing.

**Risk:** Zero. No behavior changes.
**Depends on:** Phase 1-5 (domain layer exists and is clean).
**Blocks:** Nothing, but should ship before Phase 7 to catch violations from new providers.

---

## Agent Instructions

### Step 1: Add a ruff rule or custom lint script

**Option A: Ruff banned-imports (preferred if ruff is already configured)**

Check if the project uses ruff:

```bash
cat pyproject.toml | grep -A 20 "\[tool.ruff\]"
cat ruff.toml 2>/dev/null
```

If ruff is configured, add a per-file ban:

```toml
# In pyproject.toml under [tool.ruff.lint] or ruff.toml

[tool.ruff.lint.per-file-ignores]
# No additional ignores needed for domain

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"src.clients".msg = "Domain layer must not import from infrastructure (src.clients). Use ports.py interfaces instead."
"src.research_agent".msg = "Domain layer must not import from API layer (src.research_agent)."
"src.data".msg = "Domain layer must not import from data layer (src.data). Use ports.py interfaces instead."

# Scope the ban to domain files only
[tool.ruff.lint.per-file-ignores]
"src/domain/**" = []  # all rules apply
```

**Note:** Ruff's `banned-api` doesn't support per-file scoping natively. If this doesn't work, use Option B.

**Option B: Custom lint script (works everywhere)**

Create `scripts/check_domain_imports.py`:

```python
#!/usr/bin/env python3
"""
Architectural lint: verify src/domain/ has no infrastructure imports.

This enforces the dependency rule:
  API → Domain → Infrastructure (via ports)
  Domain NEVER imports directly from Infrastructure or API layers.

Run: python scripts/check_domain_imports.py
Exit code: 0 if clean, 1 if violations found.
"""
import ast
import sys
from pathlib import Path

# These modules must never appear in imports inside src/domain/
BANNED_PREFIXES = [
    "src.clients",
    "src.research_agent",
    "src.data",
    # Infrastructure packages that should never leak into domain
    "supabase",
    "httpx",
    "openai",
    "anthropic",
    "dataforseo",
]

# Also ban os.environ / os.getenv — domain shouldn't read env vars
BANNED_ATTRS = [
    ("os", "environ"),
    ("os", "getenv"),
]

DOMAIN_ROOT = Path("src/domain")


def check_file(filepath: Path) -> list[str]:
    """Check a single Python file for banned imports."""
    violations = []
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        violations.append(f"{filepath}:{e.lineno}: SyntaxError: {e.msg}")
        return violations

    for node in ast.walk(tree):
        # Check `import X` statements
        if isinstance(node, ast.Import):
            for alias in node.names:
                for banned in BANNED_PREFIXES:
                    if alias.name.startswith(banned):
                        violations.append(
                            f"{filepath}:{node.lineno}: "
                            f"Banned import '{alias.name}' "
                            f"(domain must not import from {banned})"
                        )

        # Check `from X import Y` statements
        if isinstance(node, ast.ImportFrom) and node.module:
            for banned in BANNED_PREFIXES:
                if node.module.startswith(banned):
                    violations.append(
                        f"{filepath}:{node.lineno}: "
                        f"Banned import 'from {node.module}' "
                        f"(domain must not import from {banned})"
                    )

        # Check os.environ / os.getenv usage
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
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
        violations = check_file(pyfile)
        all_violations.extend(violations)

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

    print(f"✓ Domain layer is clean: {len(list(DOMAIN_ROOT.rglob('*.py')))} files checked, 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Step 2: Add to CI pipeline

Find the CI config and add the check:

```bash
# Find CI configuration
ls .github/workflows/ 2>/dev/null
cat .github/workflows/*.yml 2>/dev/null
cat Makefile 2>/dev/null | head -50
```

**If GitHub Actions:**

Add a step to the existing workflow (or create `.github/workflows/architecture.yml`):

```yaml
name: Architecture Check

on: [push, pull_request]

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Check domain layer imports
        run: python scripts/check_domain_imports.py
```

**If Makefile:**

```makefile
.PHONY: lint-architecture
lint-architecture:
	python scripts/check_domain_imports.py

.PHONY: lint
lint: lint-architecture  ## add to existing lint target
	ruff check src/
```

### Step 3: Add a pre-commit hook (optional but recommended)

If the project uses pre-commit:

```bash
cat .pre-commit-config.yaml 2>/dev/null
```

Add:

```yaml
  - repo: local
    hooks:
      - id: domain-imports
        name: Check domain layer imports
        entry: python scripts/check_domain_imports.py
        language: python
        pass_filenames: false
        files: ^src/domain/
```

### Step 4: Write a test that enforces the rule in pytest

**`tests/architecture/test_domain_imports.py`:**

```python
"""
Architectural test: domain layer dependency rules.

This test runs as part of the normal test suite, catching violations
before CI does. It's a safety net for local development.
"""
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
]


def test_domain_has_no_infrastructure_imports():
    """src/domain/ must not import from infrastructure or API layers."""
    violations = []

    for pyfile in DOMAIN_ROOT.rglob("*.py"):
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

    for pyfile in DOMAIN_ROOT.rglob("*.py"):
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
```

### Step 5: Validate

```bash
# Run the lint script
python scripts/check_domain_imports.py

# Run the pytest architectural tests
python -m pytest tests/architecture/test_domain_imports.py -v

# Intentionally introduce a violation and verify it's caught:
echo "from src.clients.dataforseo.client import DataForSEOClient" >> src/domain/entities.py
python scripts/check_domain_imports.py  # should exit 1
python -m pytest tests/architecture/test_domain_imports.py -v  # should fail

# Remove the intentional violation
git checkout src/domain/entities.py
```

**Done criteria:**
- `scripts/check_domain_imports.py` exists and catches violations
- The check runs in CI (GitHub Actions, Makefile, or equivalent)
- `tests/architecture/test_domain_imports.py` catches violations in the normal test suite
- Both env var access and infrastructure imports are checked
- Intentionally adding a banned import causes the check to fail
- All existing tests still pass
