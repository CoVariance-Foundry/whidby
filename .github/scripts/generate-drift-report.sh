#!/usr/bin/env bash
set -euo pipefail

# Generates a summary drift report for review.

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

REPORT_FILE="/tmp/drift-report.md"

cat > "$REPORT_FILE" << 'HEADER'
# Spec Drift Report

**Generated:** $(date -u +"%Y-%m-%d %H:%M UTC")

## Module Status Summary
HEADER

echo "| Module | Spec Exists | Code Exists | Tests Exist | Status |" >> "$REPORT_FILE"
echo "|--------|-------------|-------------|-------------|--------|" >> "$REPORT_FILE"

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

for module in $(echo "${!MODULE_CODE_DIRS[@]}" | tr ' ' '\n' | sort); do
  code_path="${MODULE_CODE_DIRS[$module]}"
  spec_path=".specify/specs/${module}/spec.md"

  spec_status="No"
  code_status="No"
  test_status="No"
  overall="Not started"

  [ -f "$spec_path" ] && [ -s "$spec_path" ] && spec_status="Yes"
  [ -e "$code_path" ] && code_status="Yes"

  module_name=$(basename "$code_path" .py)
  [ -f "tests/unit/test_${module_name}.py" ] && test_status="Yes"

  if [ "$spec_status" = "Yes" ] && [ "$code_status" = "Yes" ] && [ "$test_status" = "Yes" ]; then
    overall="Complete"
  elif [ "$spec_status" = "Yes" ] && [ "$code_status" = "Yes" ]; then
    overall="Missing tests"
  elif [ "$spec_status" = "Yes" ] && [ "$code_status" = "No" ]; then
    overall="Spec only"
  elif [ "$code_status" = "Yes" ] && [ "$spec_status" = "No" ]; then
    overall="DRIFT: No spec"
  fi

  echo "| $module | $spec_status | $code_status | $test_status | $overall |" >> "$REPORT_FILE"
done

cat >> "$REPORT_FILE" << 'FOOTER'

## Recommendations

- Modules in "DRIFT: No spec" state need immediate spec creation via `/speckit.specify`
- Modules in "Missing tests" state need test files before merge
- Modules in "Spec only" state are ready for `/speckit.plan` -> `/speckit.tasks` -> `/speckit.implement`

## Constitution Status

Run `.github/scripts/check-constitution.sh` for detailed compliance check.
FOOTER

echo "Drift report generated at: $REPORT_FILE"
cat "$REPORT_FILE"
