#!/bin/bash
# Check if PromptMe server is running
cd "$(dirname "$0")"

PIDFILE=".pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "PromptMe is running (PID $PID)"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

# Fallback: check by process name
PIDS=$(pgrep -f "python.*main\.py" 2>/dev/null | tr '\n' ' ')
if [ -n "$PIDS" ]; then
    echo "PromptMe is running (PID ${PIDS% })"
    exit 0
fi

echo "PromptMe is not running"
exit 1
