#!/usr/bin/env bash
# ============================================================
# QA Agent Platform — One-Click Startup Script
# ============================================================
# Usage:
#   ./start.sh                     # Start with current .env settings
#   ./start.sh --provider github   # Override provider (uses .env.github if present)
#   ./start.sh --provider openai   # Override provider
#   ./start.sh --port 9000         # Custom port (default: 8000)
#   ./start.sh --reload            # Enable hot-reload (dev mode)
#   ./start.sh --team mobile       # Load config from config/teams/mobile.env

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=8000
RELOAD=""
PROVIDER=""
TEAM=""
ENV_FILE="$PROJECT_DIR/.env"

# ── Parse arguments ──────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)    PORT="$2"; shift 2 ;;
    --reload)  RELOAD="--reload"; shift ;;
    --provider) PROVIDER="$2"; shift 2 ;;
    --team)    TEAM="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Load team profile if specified ───────────────────────────
if [[ -n "$TEAM" ]]; then
  TEAM_ENV="$PROJECT_DIR/config/teams/$TEAM.env"
  if [[ -f "$TEAM_ENV" ]]; then
    echo "📋 Loading team profile: $TEAM ($TEAM_ENV)"
    set -a; source "$TEAM_ENV"; set +a
  else
    echo "❌ Team env not found: $TEAM_ENV"
    echo "   Create it from config/teams/example.env"
    exit 1
  fi
fi

# ── Override provider if flag passed ─────────────────────────
if [[ -n "$PROVIDER" ]]; then
  echo "🔄 Overriding LLM_PROVIDER → $PROVIDER"
  export LLM_PROVIDER="$PROVIDER"
fi

# ── Activate virtual environment ─────────────────────────────
cd "$PROJECT_DIR"

if [[ -d ".venv" ]]; then
  source .venv/bin/activate
elif [[ -d "venv" ]]; then
  source venv/bin/activate
else
  echo "⚠️  No virtual environment found. Running with system Python."
  echo "   Create one: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
fi

# ── Print startup banner ─────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       QA Agent Platform — Starting Up           ║"
echo "╚══════════════════════════════════════════════════╝"
echo " URL     : http://localhost:$PORT"
echo " Provider: ${LLM_PROVIDER:-from .env}"
echo " Jira    : ${USE_MOCK_JIRA:-from .env}"
echo " GitHub  : ${USE_MOCK_GITHUB:-from .env}"
echo ""

# ── Start server ─────────────────────────────────────────────
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" $RELOAD
