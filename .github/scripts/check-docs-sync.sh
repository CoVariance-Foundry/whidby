#!/usr/bin/env bash
set -euo pipefail

BASE_SHA="${1:-origin/main}"
HEAD_SHA="${2:-HEAD}"

CHANGED_FILES=$(git diff --name-only "$BASE_SHA" "$HEAD_SHA" 2>/dev/null || git diff --name-only HEAD~1 HEAD)

INTERFACE_PATTERNS=(
  "src/pipeline/"
  "src/scoring/"
  "src/classification/"
  "src/experiment/"
  "src/clients/"
  "src/data/"
)

has_interface_change=false
for file in $CHANGED_FILES; do
  for pattern in "${INTERFACE_PATTERNS[@]}"; do
    if [[ "$file" == *"$pattern"* ]] && [[ "$file" == *.py ]]; then
      has_interface_change=true
      break 2
    fi
  done
done

if [ "$has_interface_change" = false ]; then
  echo "No interface-level code changes detected. Docs sync check: PASS"
  exit 0
fi

ARCH_DOCS=(
  "docs/product_breakdown.md"
  "docs/module_dependency.md"
  "docs/data_flow.md"
)

docs_updated=false
for file in $CHANGED_FILES; do
  for doc in "${ARCH_DOCS[@]}"; do
    if [[ "$file" == "$doc" ]]; then
      docs_updated=true
      break 2
    fi
  done
done

if [ "$docs_updated" = false ]; then
  echo "WARNING: Module interface code was changed but no architecture docs were updated."
  echo ""
  echo "If this change affects module I/O contracts, dependencies, or data flow,"
  echo "update the relevant docs in the same PR:"
  echo "  - docs/product_breakdown.md (I/O contracts)"
  echo "  - docs/module_dependency.md (dependency changes)"
  echo "  - docs/data_flow.md (data shape changes)"
  echo ""
  echo "If contracts are unchanged, add '[docs-sync-skip]' to a commit message to bypass."

  SKIP_TAG=$(git log "$BASE_SHA".."$HEAD_SHA" --oneline 2>/dev/null || git log --oneline -5)
  if echo "$SKIP_TAG" | grep -q "\[docs-sync-skip\]"; then
    echo ""
    echo "Found [docs-sync-skip] tag. Docs sync check: PASS (bypassed)"
    exit 0
  fi

  exit 1
fi

echo "Docs sync check: PASS (architecture docs updated alongside interface changes)"
