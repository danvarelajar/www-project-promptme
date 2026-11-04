"""LLM04:2026 Supply Chain — Kestrelline's model hub.

Pick a model package from the hub and chat with it. Each package ships a
manifest (with a published SHA-256), a chat template and a handler.py that
the app imports and runs (like trust_remote_code). The popular community
package doesn't match its published hash: its handler was tampered with
and copies every conversation to a "telemetry" collector on this server.

Intended path: verify the hashes, read the package files, find where the
community handler sends your chats, confirm they arrived and take the
flag from the collector.
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys

from flask import Flask, abort, jsonify, render_template, request

from promptme import web
from promptme.agent import _as_tokens
from promptme.runner import run

app = Flask(__name__)
web.attach(app, "llm04")

BASE = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(BASE, "hub")


def package_hash(name):
    d = os.path.join(HUB, name)
    h = hashlib.sha256()
    for f in sorted(os.listdir(d)):
        if f == "manifest.json" or f.startswith("__"):
            continue
        h.update(f.encode())
        with open(os.path.join(d, f), "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()


def models():
    out = []
    for name in sorted(os.listdir(HUB)):
        path = os.path.join(HUB, name, "manifest.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                out.append(json.load(f))
    return out


def model(name):
    for m in models():
        if m["name"] == name:
            return m
    return None


_handlers = {}


def handler(name):
    """Import the package's handler.py — running code that came with the model."""
    if name not in _handlers:
        spec = importlib.util.spec_from_file_location(f"hub_{name.replace('-', '_')}", os.path.join(HUB, name, "handler.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _handlers[name] = mod
    return _handlers[name]


@app.get("/")
def index():
    return render_template("index.html", models=models())


@app.get("/api/models/<name>/files/<path:filename>")
def package_file(name, filename):
    m = model(name)
    if not m or filename not in m["files"] + ["manifest.json"]:
        abort(404)
    with open(os.path.join(HUB, name, filename), encoding="utf-8") as f:
        return jsonify({"name": filename, "content": f.read()})


@app.post("/api/models/<name>/verify")
def verify(name):
    m = model(name)
    if not m:
        abort(404)
    actual = package_hash(name)
    return jsonify({"published": m["sha256"], "actual": actual, "match": actual == m["sha256"]})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    name = data.get("model", "")
    message = (data.get("message") or "").strip()[:2000]
    history = data.get("history") if isinstance(data.get("history"), list) else []
    m = model(name)
    if not m:
        return jsonify({"error": "Pick a model from the hub first."}), 400

    def events():
        with open(os.path.join(HUB, name, "chat_template.txt"), encoding="utf-8") as f:
            template = f.read().strip()
        yield {"type": "trace", "title": f"Loaded {m['name']} {m['version']}",
               "body": f"publisher: {m['publisher']}\nverified: {m['verified']}\n"
                       f"handler.py imported and executed (trust_remote_code=True)"}
        messages = [{"role": "system", "content": template}] + [
            {"role": h.get("role"), "content": str(h.get("content", ""))[:2000]}
            for h in history[-8:] if h.get("role") in ("user", "assistant")
        ] + [{"role": "user", "content": message}]
        answer = handler(name).generate(messages)
        yield from _as_tokens(answer)

    return web.sse(events())


def start_collector():
    subprocess.Popen(
        [sys.executable, os.path.join(BASE, "collector.py")],
        cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
    )


if __name__ == "__main__":
    # The collector runs in this challenge's process group, so stopping the
    # challenge stops it too.
    start_collector()
    run(app, 5004)
