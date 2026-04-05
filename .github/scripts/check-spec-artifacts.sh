#!/usr/bin/env bash
set -euo pipefail

BASE_SHA="${1:-origin/main}"
HEAD_SHA="${2:-HEAD}"

declare -A MODULE_DIRS=(
  ["src/pipeline/keyword_expansion"]="M04-keyword-expansion"
  ["src/pipeline/intent_classifier"]="M04-keyword-expansion"
  ["src/pipeline/keyword_deduplication"]="M04-keyword-expansion"
  ["src/pipeline/data_collection"]="M05-data-collection"
  ["src/pipeline/collection_plan"]="M05-data-collection"
  ["src/pipeline/batch_executor"]="M05-data-collection"
  ["src/pipeline/result_assembler"]="M05-data-collection"
  ["src/pipeline/signal_extraction"]="M06-signal-extraction"
  ["src/pipeline/extractors/"]="M06-signal-extraction"
  ["src/pipeline/serp_parser"]="M06-signal-extraction"
  ["src/pipeline/domain_classifier"]="M06-signal-extraction"
  ["src/pipeline/effective_volume"]="M06-signal-extraction"
  ["src/pipeline/review_velocity"]="M06-signal-extraction"
  ["src/pipeline/gbp_completeness"]="M06-signal-extraction"
  ["src/scoring/"]="M07-scoring-engine"
  ["src/classification/"]="M08-classification-guidance"
  ["src/pipeline/report_generator"]="M09-report-generation"
  ["src/pipeline/feedback_logger"]="M09-report-generation"
  ["src/experiment/business_discovery"]="M10-business-discovery"
  ["src/experiment/email_discovery"]="M10-business-discovery"
  ["src/experiment/business_qualification"]="M10-business-discovery"
  ["src/experiment/site_scanner"]="M11-site-scanning"
  ["src/experiment/weakness_scorer"]="M11-site-scanning"
  ["src/experiment/quality_bucketing"]="M11-site-scanning"
  ["src/experiment/audit_generator"]="M12-audit-generation"
  ["src/experiment/audit_templates/"]="M12-audit-generation"
  ["src/experiment/audit_hosting"]="M12-audit-generation"
  ["src/experiment/outreach_manager"]="M13-outreach-delivery"
  ["src/experiment/email_sender"]="M13-outreach-delivery"
  ["src/experiment/email_templates/"]="M13-outreach-delivery"
  ["src/experiment/email_adapters/"]="M13-outreach-delivery"
  ["src/experiment/compliance"]="M13-outreach-delivery"
  ["src/experiment/event_tracker"]="M14-response-tracking"
  ["src/experiment/reply_classifier"]="M14-response-tracking"
  ["src/experiment/engagement_scorer"]="M14-response-tracking"
  ["src/experiment/experiment_analyzer"]="M15-experiment-analysis"
  ["src/experiment/ab_analysis"]="M15-experiment-analysis"
  ["src/experiment/rentability_signal"]="M15-experiment-analysis"
)

CHANGED_FILES=$(git diff --name-only "$BASE_SHA" "$HEAD_SHA" 2>/dev/null || git diff --name-only HEAD~1 HEAD)

REQUIRED_SPECS=()

for file in $CHANGED_FILES; do
  for pattern in "${!MODULE_DIRS[@]}"; do
    if [[ "$file" == *"$pattern"* ]]; then
      spec_dir="${MODULE_DIRS[$pattern]}"
      if [[ ! " ${REQUIRED_SPECS[*]:-} " =~ " ${spec_dir} " ]]; then
        REQUIRED_SPECS+=("$spec_dir")
      fi
    fi
  done
done

if [ ${#REQUIRED_SPECS[@]} -eq 0 ]; then
  echo "No module-scoped code changes detected. Spec artifact check: PASS"
  exit 0
fi

MISSING=()
for spec_dir in "${REQUIRED_SPECS[@]}"; do
  spec_path=".specify/specs/${spec_dir}/spec.md"
  if [ ! -f "$spec_path" ] || [ ! -s "$spec_path" ]; then
    MISSING+=("$spec_dir")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "FAIL: The following modules have code changes but missing spec artifacts:"
  for m in "${MISSING[@]}"; do
    echo "  - $m (expected: .specify/specs/${m}/spec.md)"
  done
  echo ""
  echo "Run /speckit.specify for each module before implementation."
  exit 1
fi

echo "Spec artifact check: PASS"
echo "Verified spec artifacts for: ${REQUIRED_SPECS[*]}"
