#!/bin/bash
# Stop PromptMe server
cd "$(dirname "$0")"

PIDFILE=".pid"

stop_pid() {
    local pid=$1
    if kill -0 "$pid" 2>/dev/null; then
        kill -TERM "$pid" 2>/dev/null
        for _ in 1 2 3 4 5; do
            kill -0 "$pid" 2>/dev/null || break
            sleep 1
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill -KILL "$pid" 2>/dev/null
        fi
        echo "PromptMe stopped (PID $pid)"
        return 0
    fi
    return 1
}

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if stop_pid "$PID"; then
        :
    else
        echo "Process $PID not running (stale PID file)"
    fi
    rm -f "$PIDFILE"
else
    PIDS=$(pgrep -f "python.*main\.py" 2>/dev/null)
    if [ -n "$PIDS" ]; then
        for pid in $PIDS; do
            stop_pid "$pid" || true
        done
    else
        echo "PromptMe is not running"
    fi
fi
