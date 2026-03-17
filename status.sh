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
fi

if pgrep -f "python main.py" >/dev/null; then
    echo "PromptMe is running (PID $(pgrep -f 'python main.py'))"
else
    echo "PromptMe is not running"
    exit 1
fi
