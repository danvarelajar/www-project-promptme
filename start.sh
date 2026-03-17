#!/bin/bash
# Start PromptMe server in background (detached from terminal session)
cd "$(dirname "$0")"

PIDFILE=".pid"
LOGFILE="logs/main.log"
PYTHON="${PWD}/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "Error: venv not found. Run ./install.sh first."
    exit 1
fi

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "PromptMe is already running (PID $PID)"
        exit 1
    fi
    rm -f "$PIDFILE"
fi

mkdir -p logs
# setsid = new session (immune to terminal close)
# nohup = ignore SIGHUP
# < /dev/null = detach stdin
setsid nohup "$PYTHON" main.py >> "$LOGFILE" 2>&1 < /dev/null &
echo $! > "$PIDFILE"
echo "PromptMe started (PID $(cat $PIDFILE)). Logs: $LOGFILE"
