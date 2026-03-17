#!/bin/bash
# Stop PromptMe server
cd "$(dirname "$0")"

PIDFILE=".pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "PromptMe stopped (PID $PID)"
    else
        echo "Process $PID not running"
    fi
    rm -f "$PIDFILE"
else
    # Fallback: try pkill
    if pkill -f "python main.py" 2>/dev/null; then
        echo "PromptMe stopped (via pkill)"
    else
        echo "PromptMe is not running"
    fi
fi
