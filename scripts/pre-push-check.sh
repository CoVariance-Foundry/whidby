#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
WARN=0

run_check() {
  local name="$1"
  shift
  echo -n "  $name... "
  if "$@" > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS++))
  else
    echo -e "${RED}FAIL${NC}"
    ((FAIL++))
  fi
}

run_warn() {
  local name="$1"
  shift
  echo -n "  $name... "
  if "$@" > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
    ((PASS++))
  else
    echo -e "${YELLOW}WARN${NC}"
    ((WARN++))
  fi
}

echo "======================================="
echo "  Widby Pre-Push Quality Check"
echo "======================================="
echo ""

echo "Python Quality:"
run_check "ruff check" ruff check src/ tests/
run_check "unit tests" python -m pytest tests/unit/ -v --tb=short -q

echo ""
echo "Web Quality:"
run_warn "npm lint" npm run lint 2>&1

echo ""
echo "Spec Artifacts:"
if [ -f ".github/scripts/check-spec-artifacts.sh" ]; then
  run_warn "spec artifacts" bash .github/scripts/check-spec-artifacts.sh
else
  echo "  spec artifacts... SKIP (script not found)"
fi

echo ""
echo "Docs Sync:"
if [ -f ".github/scripts/check-docs-sync.sh" ]; then
  run_warn "docs sync" bash .github/scripts/check-docs-sync.sh
else
  echo "  docs sync... SKIP (script not found)"
fi

echo ""
echo "======================================="
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "======================================="

if [ "$FAIL" -gt 0 ]; then
  echo -e "${RED}Fix failures before pushing.${NC}"
  exit 1
fi

if [ "$WARN" -gt 0 ]; then
  echo -e "${YELLOW}Warnings present. Review before merging.${NC}"
fi

exit 0
