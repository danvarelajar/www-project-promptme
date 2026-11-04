"""Command line behind promptme.sh.

    python -m promptme.cli start      start the dashboard in the background
    python -m promptme.cli stop       stop the dashboard and every challenge
    python -m promptme.cli restart
    python -m promptme.cli status     what is running
    python -m promptme.cli check      can we reach the endpoint, are the models there?
"""

import os
import sys
import time

from . import config, launcher, llm

# PROMPTME_PORT moves the dashboard off 5000 (on macOS, AirPlay Receiver uses 5000).
DASHBOARD = {"id": "dashboard", "code": "Dashboard", "port": int(os.getenv("PROMPTME_PORT", "5000")), "entry": "main.py"}


def _print_status():
    rows = [("Dashboard", DASHBOARD)] + [(f"{c['code']} {c['title']}", c) for c in config.challenges()]
    for label, ch in rows:
        st = launcher.status(ch)
        state = "running" if st["running"] else ("port busy" if st["listening"] else "stopped")
        print(f"  {label:48} :{ch['port']:<5} {state}")


def check():
    s = config.settings()
    print(f"Endpoint:   {llm.base_url()}")
    print(f"API key:    {'set' if s['api_key'] else 'not set'}")
    try:
        available = llm.list_models()
    except llm.LLMError as e:
        print(f"Result:     FAIL. {e}")
        return 1
    print(f"Reachable:  yes ({len(available)} models)")
    ok = True
    for role, name in s["models"].items():
        present = llm.has_model(name, available)
        ok &= present
        print(f"  {role:6} {name:32} {'ok' if present else 'MISSING (ollama pull ' + name + ')'}")
    if ok:
        start = time.time()
        try:
            llm.chat([{"role": "user", "content": "Reply with the word ready."}], max_tokens=5)
            print(f"Chat test:  ok ({time.time() - start:.1f}s)")
        except llm.LLMError as e:
            print(f"Chat test:  FAIL. {e}")
            ok = False
    return 0 if ok else 1


def start():
    st = launcher.status(DASHBOARD)
    if st["running"]:
        print(f"Dashboard is already running on port {DASHBOARD['port']}.")
        return 0
    try:
        launcher.start(DASHBOARD, wait=30)
    except launcher.LaunchError as e:
        print(f"Couldn't start the dashboard: {e}")
        return 1
    print(f"Dashboard running: http://<this-server>:{DASHBOARD['port']}/")
    return 0


def stop():
    stopped = [c["code"] for c in config.challenges() if launcher.stop(c)]
    if launcher.stop(DASHBOARD):
        stopped.append("Dashboard")
    print("Stopped: " + (", ".join(stopped) if stopped else "nothing was running"))
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    os.chdir(config.ROOT)
    if cmd == "start":
        return start()
    if cmd == "stop":
        return stop()
    if cmd == "restart":
        stop()
        return start()
    if cmd == "status":
        _print_status()
        return 0
    if cmd == "check":
        return check()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
