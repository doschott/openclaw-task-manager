#!/bin/bash
# run_tests.sh - Run pytest tests for openclaw-task-manager
#
# Uses the prophecy-news-tracker venv which has pytest installed.
# From WSL:
#   bash run_tests.sh
#
# From Windows (in Git Bash or WSL):
#   wsl -u dosubuntu bash run_tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$HOME/clawd/projects/prophecy-news-tracker/venv/bin/python"

echo "Running openclaw-task-manager tests..."
echo "Using Python: $VENV_PYTHON"
echo ""

"$VENV_PYTHON" -m pytest "$SCRIPT_DIR/tests" -v "$@"

echo ""
echo "Tests complete."
