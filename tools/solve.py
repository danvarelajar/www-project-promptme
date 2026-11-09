"""Measure how reliably each challenge can be solved with the configured model.

    python tools/solve.py                    # every challenge, 3 runs each
    python tools/solve.py llm01 llm08 -n 10  # chosen challenges, 10 runs
    python tools/solve.py --skip llm06       # LLM06 takes minutes per run
    python tools/solve.py --dashboard http://localhost:5100   # challenges in a container

Starts challenges that aren't running (and stops them afterwards), prints a
table and writes data/solve_report.json. Run it on an attendee-sized server:
the numbers depend on the model and the hardware.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from promptme import config, launcher  # noqa: E402
from tools.solvers import SOLVERS, SOLVERS_L2, Ctx  # noqa: E402


def run_solver(ch, suffix, solver, args, report):
    wins, runs, times, last = 0, 0, [], ""
    for _ in range(args.runs):
        t0 = time.time()
        try:
            ok, detail = solver(Ctx(ch, args.host, args.dashboard))
        except Exception as e:  # a crashed attempt counts as a failure
            ok, detail = False, f"error: {e}"
        if ok is None:
            last = detail
            break
        runs += 1
        wins += bool(ok)
        times.append(time.time() - t0)
        last = detail
    label = ch["code"] + suffix
    title = (ch.get("level2") or {}).get("title", ch["title"]) if suffix else ch["title"]
    if not runs:
        print(f"{label:15} {title[:34]:34} skipped ({last})")
        report["results"].append({"id": ch["id"] + ("-l2" if suffix else ""), "skipped": last})
        return
    rate = wins / runs * 100
    avg = sum(times) / len(times)
    print(f"{label:15} {title[:34]:34} {wins}/{runs} ({rate:3.0f}%)  avg {avg:5.1f}s  last: {last[:60]}")
    report["results"].append({"id": ch["id"] + ("-l2" if suffix else ""), "runs": runs, "solved": wins,
                              "rate": rate, "avg_seconds": round(avg, 1), "last_detail": last})


def ensure_running(ch, dashboard):
    """Start the challenge if needed; True if this run started it."""
    if dashboard:
        state = requests.get(dashboard.rstrip("/") + "/api/state", timeout=10).json()
        if next(c for c in state["challenges"] if c["id"] == ch["id"])["running"]:
            return False
        r = requests.post(f"{dashboard.rstrip('/')}/api/challenges/{ch['id']}/start", timeout=120).json()
        if not r.get("ok"):
            raise RuntimeError(r.get("error", "dashboard refused to start it"))
        return True
    if launcher.status(ch)["running"]:
        return False
    launcher.start(ch)
    return True


def stop(ch, dashboard):
    if dashboard:
        requests.post(f"{dashboard.rstrip('/')}/api/challenges/{ch['id']}/stop", timeout=30)
    else:
        launcher.stop(ch)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="challenge ids (default: all)")
    ap.add_argument("-n", "--runs", type=int, default=3)
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--level", choices=["1", "2", "both"], default="both", help="which levels to run")
    ap.add_argument("--dashboard", help="start/stop challenges through this dashboard's API (e.g. a container) "
                                        "instead of as local processes")
    args = ap.parse_args()

    chosen = [c for c in config.challenges() if (not args.ids or c["id"] in args.ids) and c["id"] not in args.skip]
    settings = config.settings()
    print(f"Model: {settings['models']['chat']}  Embeddings: {settings['models']['embed']}  Endpoint: {settings['ollama_host']}\n")

    report = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "models": settings["models"], "results": []}
    for ch in chosen:
        try:
            started_here = ensure_running(ch, args.dashboard)
        except (launcher.LaunchError, RuntimeError) as e:
            print(f"{ch['code']:12} could not start: {e}")
            continue
        jobs = []
        if args.level in ("1", "both"):
            jobs.append(("", SOLVERS[ch["id"]]))
        if args.level in ("2", "both") and ch["id"] in SOLVERS_L2 and ch.get("level2"):
            jobs.append((" L2", SOLVERS_L2[ch["id"]]))
        for suffix, solver in jobs:
            run_solver(ch, suffix, solver, args, report)
        if started_here:
            stop(ch, args.dashboard)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    path = os.path.join(config.DATA_DIR, "solve_report.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {os.path.relpath(path, config.ROOT)}")


if __name__ == "__main__":
    main()
