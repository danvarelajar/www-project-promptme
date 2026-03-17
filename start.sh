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

# Daemonize: setsid (if available) = new session, nohup = ignore SIGHUP
# < /dev/null = detach stdin. Fallback to nohup only if setsid missing.
if command -v setsid >/dev/null 2>&1; then
    setsid nohup "$PYTHON" main.py >> "$LOGFILE" 2>&1 < /dev/null &
else
    nohup "$PYTHON" main.py >> "$LOGFILE" 2>&1 < /dev/null &
fi

PID=$!
echo $PID > "$PIDFILE"

# Verify process is still running (catches immediate crashes)
sleep 2
if ! kill -0 "$PID" 2>/dev/null; then
    echo "Error: Process exited immediately. Check logs:"
    tail -20 "$LOGFILE" 2>/dev/null || echo "(no log output yet)"
    rm -f "$PIDFILE"
    exit 1
fi

echo "PromptMe started (PID $PID). Logs: $LOGFILE"
