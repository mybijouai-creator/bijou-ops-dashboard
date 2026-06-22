#!/usr/bin/env bash
# Cron-ready startup script for Bijou AI Operations Dashboard
# Run every day to keep dashboard available, or use as a systemd service template

set -e

PROJECT_DIR="/c/Users/W3jde/Movies/Hub/Projects/w3j/bijou-ops-dashboard"
LOG_FILE="/tmp/bijou-dashboard.log"
PID_FILE="/tmp/bijou-dashboard.pid"

cd "$PROJECT_DIR"

# Use existing Hermes venv if available, otherwise create one
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate" 2>/dev/null || source "$VENV_DIR/Scripts/activate"
pip install -q -r requirements.txt

# Kill existing instance if running
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Dashboard already running at PID $(cat $PID_FILE)"
    exit 0
fi

# Start dashboard
nohup uvicorn main:app --host 0.0.0.0 --port 8765 > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Bijou Operations Dashboard started on http://localhost:8765 (PID $!)"
