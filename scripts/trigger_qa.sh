#!/usr/bin/env bash
# ============================================================
# scripts/trigger_qa.sh
# ============================================================
# Trigger the QA workflow against a RUNNING local server.
# Use this when you want to fire a single analysis from your
# terminal without going through GitHub Actions.
#
# Usage:
#   ./scripts/trigger_qa.sh CRFLT-123 statements
#   ./scripts/trigger_qa.sh CRFLT-123 confirms --no-bdd
#
# Requires: curl, jq (brew install jq)
# ============================================================

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────
API_BASE="${QA_API_BASE:-http://localhost:8000/api/v1}"
JIRA_ID="${1:?Usage: $0 <jira-id> <team-id> [options]}"
TEAM_ID="${2:?Usage: $0 <jira-id> <team-id>}"
shift 2

# Step toggles (each can be overridden via flags below)
QUALITY=true
ALIGNMENT=true
TEST_CASES=true
BDD=true
STEP_DEFS=true
STEP_STYLE="pytest_bdd"
UPLOAD_JIRA=false
CREATE_PR=false
CUSTOM_PROMPT=""
TRIGGERED_BY="${USER:-cli}"

# ── Parse optional flags ──────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-quality)    QUALITY=false ;;
    --no-alignment)  ALIGNMENT=false ;;
    --no-test-cases) TEST_CASES=false ;;
    --no-bdd)        BDD=false ;;
    --no-step-defs)  STEP_DEFS=false ;;
    --step-style)    STEP_STYLE="$2"; shift ;;
    --upload-jira)   UPLOAD_JIRA=true ;;
    --create-pr)     CREATE_PR=true ;;
    --by)            TRIGGERED_BY="$2"; shift ;;
    --prompt)        CUSTOM_PROMPT="$2"; shift ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
  shift
done

echo "▶  QA Workflow"
echo "   Jira  : $JIRA_ID"
echo "   Team  : $TEAM_ID"
echo "   By    : $TRIGGERED_BY"
echo "   API   : $API_BASE"
echo ""

# ── Health check ─────────────────────────────────────────────
if ! curl -sf "$API_BASE/health" > /dev/null; then
  echo "ERROR: Server not reachable at $API_BASE" >&2
  echo "Start it with:  ./start.sh" >&2
  exit 1
fi

# ── POST /run-qa ──────────────────────────────────────────────
PAYLOAD=$(jq -n \
  --arg jira_id        "$JIRA_ID" \
  --arg team_id        "$TEAM_ID" \
  --arg triggered_by   "$TRIGGERED_BY" \
  --argjson quality    "$QUALITY" \
  --argjson alignment  "$ALIGNMENT" \
  --argjson test_cases "$TEST_CASES" \
  --argjson bdd        "$BDD" \
  --argjson step_defs  "$STEP_DEFS" \
  --arg step_style     "$STEP_STYLE" \
  --arg custom_prompt  "$CUSTOM_PROMPT" \
  '{
    jira_id:      $jira_id,
    team_id:      $team_id,
    triggered_by: $triggered_by,
    custom_prompt: (if $custom_prompt == "" then null else $custom_prompt end),
    steps: {
      ticket_quality:   $quality,
      code_alignment:   $alignment,
      test_cases:       $test_cases,
      bdd_scenarios:    $bdd,
      step_definitions: $step_defs,
      step_def_style:   $step_style
    }
  }')

echo "📤 Sending request..."
RESPONSE=$(curl -sf -X POST "$API_BASE/run-qa" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

# ── Print results ─────────────────────────────────────────────
GRADE=$(echo "$RESPONSE" | jq -r '.grade // "N/A"')
SCORE=$(echo "$RESPONSE" | jq -r '.overall_score // 0')
RUN_ID=$(echo "$RESPONSE" | jq -r '.run_id // "unknown"')
ISSUES=$(echo "$RESPONSE" | jq '.issues_found | length')

echo ""
echo "✅ Done"
echo "   Run ID : $RUN_ID"
echo "   Grade  : $GRADE"
echo "   Score  : $SCORE / 100"
echo "   Issues : $ISSUES"
echo ""

# ── List output files ─────────────────────────────────────────
echo "📁 Outputs:"
echo "$RESPONSE" | jq -r '.outputs // {} | to_entries[] | "   \(.key): \(.value)"'
echo ""

# ── Open HTML report in browser if macOS ─────────────────────
REPORT=$(echo "$RESPONSE" | jq -r '.outputs.report // empty')
if [[ -n "$REPORT" && "$OSTYPE" == "darwin"* ]]; then
  echo "🌐 Opening report in browser..."
  open "http://localhost:8000/api/v1/outputs/${REPORT#outputs/}"
fi
