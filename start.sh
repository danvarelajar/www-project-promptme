#!/bin/bash
# Start PromptMe server in background
cd "$(dirname "$0")"

PIDFILE=".pid"
LOGFILE="logs/main.log"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "PromptMe is already running (PID $PID)"
        exit 1
    fi
    rm -f "$PIDFILE"
fi

mkdir -p logs
nohup python main.py >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "PromptMe started (PID $(cat $PIDFILE)). Logs: $LOGFILE"
