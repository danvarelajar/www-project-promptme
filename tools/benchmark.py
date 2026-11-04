"""Compare chat models on what PromptMe needs from them, on this hardware.

    .venv/bin/python tools/benchmark.py llama3.2:3b qwen2.5:3b granite3.3:2b
    .venv/bin/python tools/benchmark.py llama3.2:3b -n 10

Measures, per model:
  speed      time to first token and tokens per second on a ~150-word answer
  tools      native tool calling: picks the right tool with valid arguments
  json       strict JSON output (the fallback when tool calling is weak)
and the embedding model's time for a batch of 20 texts.

Writes data/benchmark.json. Solve rates come from tools/solve.py.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from promptme import config, llm  # noqa: E402

TOOLS = [
    {"type": "function", "function": {
        "name": "list_files", "description": "List the files in a folder.",
        "parameters": {"type": "object", "properties": {"folder": {"type": "string"}}, "required": ["folder"]}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a file and return its text.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]
TOOL_CASES = [
    ("What files are in the /public folder?", "list_files", "folder", "/public"),
    ("Please open /public/welcome.txt and tell me what it says.", "read_file", "path", "/public/welcome.txt"),
]
JSON_PROMPT = (
    "Decide the action for this request and answer ONLY with JSON of the form "
    '{"action": "LIST" or "READ", "path": "<path>"}.\n'
    "Request: show me what is inside /docs/handbook.txt"
)


def speed(model, runs):
    msgs = [{"role": "user", "content": "In about 150 words, explain what a vector database is."}]
    llm.chat(msgs, model=model, max_tokens=8)  # warm-up / load
    ttfts, rates = [], []
    for _ in range(runs):
        t0 = time.time()
        first, pieces = None, 0
        for _piece in llm.chat_stream(msgs, model=model, max_tokens=250):
            if first is None:
                first = time.time() - t0
            pieces += 1
        total = time.time() - t0
        ttfts.append(first or total)
        # Streamed pieces are roughly one token each on Ollama.
        rates.append(pieces / max(total - (first or 0), 0.001))
    return round(sum(ttfts) / runs, 2), round(sum(rates) / runs, 1)


def tool_calling(model, runs):
    ok = total = 0
    for _ in range(runs):
        for prompt, name, arg, value in TOOL_CASES:
            total += 1
            try:
                out = llm.chat_full(
                    [{"role": "system", "content": "You are a file assistant. Use the tools to answer."},
                     {"role": "user", "content": prompt}],
                    model=model, max_tokens=200, temperature=0, tools=TOOLS)
            except llm.LLMError:
                continue
            for call in out["message"].get("tool_calls") or []:
                fn = call.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else fn.get("arguments", {})
                except ValueError:
                    args = {}
                if fn.get("name") == name and str(args.get(arg, "")).rstrip("/") == value.rstrip("/"):
                    ok += 1
                    break
    return ok, total


def strict_json(model, runs):
    ok = 0
    for _ in range(runs):
        try:
            text = llm.chat([{"role": "user", "content": JSON_PROMPT}], model=model, max_tokens=60, temperature=0)
            start, end = text.find("{"), text.rfind("}")
            data = json.loads(text[start:end + 1])
            ok += data.get("action") == "READ" and data.get("path") == "/docs/handbook.txt"
        except (ValueError, llm.LLMError):
            pass
    return ok, runs


def embed_speed():
    texts = [f"Shipment {i} left the Rotterdam warehouse on schedule." for i in range(20)]
    llm.embed(texts[:1])
    t0 = time.time()
    llm.embed(texts)
    return round(time.time() - t0, 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="*", help="chat models (default: configured chat model)")
    ap.add_argument("-n", "--runs", type=int, default=5)
    args = ap.parse_args()
    models = args.models or [config.settings()["models"]["chat"]]

    print(f"Endpoint: {llm.base_url()}  runs: {args.runs}\n")
    print(f"{'model':18} {'1st token':>9} {'tok/s':>7} {'tools':>9} {'json':>7}")
    results = []
    for m in models:
        ttft, rate = speed(m, max(1, args.runs // 2))
        t_ok, t_all = tool_calling(m, args.runs)
        j_ok, j_all = strict_json(m, args.runs)
        print(f"{m:18} {ttft:>8.2f}s {rate:>7.1f} {t_ok:>4}/{t_all:<4} {j_ok:>3}/{j_all:<3}")
        results.append({"model": m, "ttft_s": ttft, "tokens_per_s": rate,
                        "tool_calls_ok": t_ok, "tool_calls_total": t_all, "json_ok": j_ok, "json_total": j_all})
    emb = embed_speed()
    print(f"\nEmbeddings ({config.settings()['models']['embed']}): 20 texts in {emb}s")

    os.makedirs(config.DATA_DIR, exist_ok=True)
    report = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "endpoint": llm.base_url(),
              "runs": args.runs, "chat": results, "embed_20_texts_s": emb}
    with open(os.path.join(config.DATA_DIR, "benchmark.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("Report: data/benchmark.json")


if __name__ == "__main__":
    main()
