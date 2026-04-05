#!/usr/bin/env bash
set -euo pipefail

# Validates that the project constitution exists and is not stale.
# Checks key structural requirements defined in the constitution.

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

ISSUES=()

echo "=== Constitution Compliance Check ==="
echo ""

# 1. Constitution exists
if [ ! -f ".specify/memory/constitution.md" ]; then
  ISSUES+=("Constitution file missing at .specify/memory/constitution.md")
else
  echo "Constitution file: EXISTS"

  # Check it has substance (not just the template)
  if grep -q "\[PROJECT_NAME\]" .specify/memory/constitution.md; then
    ISSUES+=("Constitution appears to be unmodified template (still has [PROJECT_NAME] placeholder)")
  fi
fi

# 2. conftest.py exists (required by constitution test structure)
if [ ! -f "tests/conftest.py" ]; then
  ISSUES+=("tests/conftest.py missing (required by constitution)")
else
  echo "conftest.py: EXISTS"
fi

# 3. Ruff configured
if grep -q "ruff" pyproject.toml 2>/dev/null; then
  echo "Ruff config: PRESENT in pyproject.toml"
else
  ISSUES+=("Ruff not configured in pyproject.toml (required by constitution)")
fi

# 4. Test directories exist
for dir in tests/unit tests/integration tests/fixtures; do
  if [ -d "$dir" ]; then
    echo "Test directory $dir: EXISTS"
  else
    ISSUES+=("Test directory $dir missing (required by constitution)")
  fi
done

# 5. Architecture docs exist
for doc in docs/product_breakdown.md docs/module_dependency.md docs/data_flow.md; do
  if [ -f "$doc" ]; then
    echo "Architecture doc $doc: EXISTS"
  else
    ISSUES+=("Architecture doc $doc missing (required by constitution)")
  fi
done

# 6. Spec workflow guide exists
if [ -f "docs/spec_workflow_guide.md" ]; then
  echo "Spec workflow guide: EXISTS"
else
  ISSUES+=("docs/spec_workflow_guide.md missing")
fi

echo ""

if [ ${#ISSUES[@]} -gt 0 ]; then
  echo "ISSUES FOUND:"
  for issue in "${ISSUES[@]}"; do
    echo "  - $issue"
  done
  exit 1
fi

echo "RESULT: Constitution compliance OK."
