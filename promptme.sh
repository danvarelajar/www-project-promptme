#!/usr/bin/env bash
# PromptMe control script.
#
#   ./promptme.sh setup     create .venv and install requirements
#   ./promptme.sh start     start the dashboard (port 5000, or $PROMPTME_PORT) in the background
#   ./promptme.sh stop      stop the dashboard and all challenges
#   ./promptme.sh restart
#   ./promptme.sh status
#   ./promptme.sh check     test the model endpoint and the configured models
#
# Logs go to logs/, process IDs to run/.
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv/bin/python"

if [[ "${1:-}" == "setup" ]]; then
  python3 -m venv .venv
  "$PY" -m pip install --upgrade pip >/dev/null
  "$PY" -m pip install -r requirements.txt
  echo "Setup done. Next: ./promptme.sh check, then ./promptme.sh start"
  exit 0
fi

if [[ ! -x "$PY" ]]; then
  echo "No virtual environment yet. Run: ./promptme.sh setup" >&2
  exit 1
fi

export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
exec "$PY" -m promptme.cli "${1:-status}"
