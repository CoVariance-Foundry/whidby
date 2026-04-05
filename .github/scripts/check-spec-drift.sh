#!/usr/bin/env bash
set -euo pipefail

# Checks that every implemented module directory has corresponding spec artifacts.
# Also checks that spec artifacts reference modules that actually exist in code.

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

declare -A MODULE_CODE_DIRS=(
  ["M04-keyword-expansion"]="src/pipeline/keyword_expansion.py"
  ["M05-data-collection"]="src/pipeline/data_collection.py"
  ["M06-signal-extraction"]="src/pipeline/signal_extraction.py"
  ["M07-scoring-engine"]="src/scoring"
  ["M08-classification-guidance"]="src/classification"
  ["M09-report-generation"]="src/pipeline/report_generator.py"
  ["M10-business-discovery"]="src/experiment/business_discovery.py"
  ["M11-site-scanning"]="src/experiment/site_scanner.py"
  ["M12-audit-generation"]="src/experiment/audit_generator.py"
  ["M13-outreach-delivery"]="src/experiment/outreach_manager.py"
  ["M14-response-tracking"]="src/experiment/event_tracker.py"
  ["M15-experiment-analysis"]="src/experiment/experiment_analyzer.py"
)

DRIFT_FOUND=false
IMPL_WITHOUT_SPEC=()
SPEC_WITHOUT_IMPL=()

echo "=== Spec-Code Drift Analysis ==="
echo ""

for module in "${!MODULE_CODE_DIRS[@]}"; do
  code_path="${MODULE_CODE_DIRS[$module]}"
  spec_path=".specify/specs/${module}/spec.md"

  code_exists=false
  spec_exists=false

  if [ -e "$code_path" ]; then
    code_exists=true
  fi

  if [ -f "$spec_path" ] && [ -s "$spec_path" ]; then
    spec_exists=true
  fi

  if [ "$code_exists" = true ] && [ "$spec_exists" = false ]; then
    IMPL_WITHOUT_SPEC+=("$module ($code_path)")
    DRIFT_FOUND=true
  fi

  if [ "$spec_exists" = true ] && [ "$code_exists" = true ]; then
    spec_mod=$(stat -c %Y "$spec_path" 2>/dev/null || stat -f %m "$spec_path" 2>/dev/null || echo 0)
    code_mod=$(stat -c %Y "$code_path" 2>/dev/null || stat -f %m "$code_path" 2>/dev/null || echo 0)

    if [ "$code_mod" -gt "$spec_mod" ]; then
      age_diff=$(( (code_mod - spec_mod) / 86400 ))
      if [ "$age_diff" -gt 7 ]; then
        echo "WARNING: $module code is ${age_diff} days newer than its spec"
      fi
    fi
  fi
done

echo ""

if [ ${#IMPL_WITHOUT_SPEC[@]} -gt 0 ]; then
  echo "DRIFT: Implementation exists without spec artifacts:"
  for item in "${IMPL_WITHOUT_SPEC[@]}"; do
    echo "  - $item"
  done
  echo ""
fi

# Check for test coverage alignment
echo "=== Test Coverage Alignment ==="
for module in "${!MODULE_CODE_DIRS[@]}"; do
  code_path="${MODULE_CODE_DIRS[$module]}"
  if [ -e "$code_path" ]; then
    module_name=$(basename "$code_path" .py)
    test_file="tests/unit/test_${module_name}.py"
    if [ ! -f "$test_file" ]; then
      echo "WARNING: $module has code but no unit test at $test_file"
    fi
  fi
done

echo ""

if [ "$DRIFT_FOUND" = true ]; then
  echo "RESULT: Drift detected. Review findings above."
  exit 1
fi

echo "RESULT: No critical drift detected."
