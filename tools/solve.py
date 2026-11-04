"""Measure how reliably each challenge can be solved with the configured model.

    python tools/solve.py                    # every challenge, 3 runs each
    python tools/solve.py llm01 llm08 -n 10  # chosen challenges, 10 runs
    python tools/solve.py --skip llm06       # LLM06 takes minutes per run

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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from promptme import config, launcher  # noqa: E402
from tools.solvers import SOLVERS, Ctx  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="challenge ids (default: all)")
    ap.add_argument("-n", "--runs", type=int, default=3)
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    chosen = [c for c in config.challenges() if (not args.ids or c["id"] in args.ids) and c["id"] not in args.skip]
    settings = config.settings()
    print(f"Model: {settings['models']['chat']}  Embeddings: {settings['models']['embed']}  Endpoint: {settings['ollama_host']}\n")

    report = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "models": settings["models"], "results": []}
    for ch in chosen:
        started_here = False
        if not launcher.status(ch)["running"]:
            try:
                launcher.start(ch)
                started_here = True
            except launcher.LaunchError as e:
                print(f"{ch['code']:12} could not start: {e}")
                continue
        solver = SOLVERS[ch["id"]]
        wins, runs, times, last = 0, 0, [], ""
        for _ in range(args.runs):
            t0 = time.time()
            try:
                ok, detail = solver(Ctx(ch, args.host))
            except Exception as e:  # a crashed attempt counts as a failure
                ok, detail = False, f"error: {e}"
            if ok is None:
                last = detail
                break
            runs += 1
            wins += bool(ok)
            times.append(time.time() - t0)
            last = detail
        if started_here:
            launcher.stop(ch)
        if not runs:
            print(f"{ch['code']:12} {ch['title']:34} skipped ({last})")
            report["results"].append({"id": ch["id"], "skipped": last})
            continue
        rate = wins / runs * 100
        avg = sum(times) / len(times)
        print(f"{ch['code']:12} {ch['title']:34} {wins}/{runs} ({rate:3.0f}%)  avg {avg:5.1f}s  last: {last[:60]}")
        report["results"].append({"id": ch["id"], "runs": runs, "solved": wins, "rate": rate, "avg_seconds": round(avg, 1), "last_detail": last})

    os.makedirs(config.DATA_DIR, exist_ok=True)
    path = os.path.join(config.DATA_DIR, "solve_report.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {os.path.relpath(path, config.ROOT)}")


if __name__ == "__main__":
    main()
