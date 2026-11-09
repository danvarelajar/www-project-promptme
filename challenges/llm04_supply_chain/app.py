"""LLM04:2026 Supply Chain — Mica's model hub.

Pick a model package from the hub and chat with it. Each package ships a
manifest (with a published SHA-256), a chat template and a handler.py that
the app imports and runs (like trust_remote_code). The popular community
package doesn't match its published hash: its handler was tampered with
and copies every conversation to a "telemetry" collector on this server
(under /telemetry/, served by this app so it is reachable through the
dashboard's single port).

Intended path: verify the hashes, read the package files, find where the
community handler sends your chats, confirm they arrived and take the
flag from the collector.

FortiAIGate Mode (a switch on this page): requests go out with the package
name (fastchat-pro-7b, mica-assist-3b) as the model, and FortiAIGate
rewrites it to the real model. Only for setups where FortiAIGate protection
is configured; off (the default), they use the configured chat model.
"""

import hashlib
import importlib.util
import json
import os

from flask import Flask, abort, jsonify, redirect, render_template, request

from promptme import config, llm, web
from promptme.agent import _as_tokens
from promptme.runner import run

COLLECTOR_FLAG = "flag{unverified_model_exfiltrated_chats}"

app = Flask(__name__)
web.attach(app, "llm04")

BASE = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(BASE, "hub")
# Kept in the data folder (the Docker volume), so it survives restarts.
MODE_FILE = os.path.join(config.DATA_DIR, "llm04_fortiaigate_mode.json")


def fortiaigate_mode():
    try:
        with open(MODE_FILE, encoding="utf-8") as f:
            return bool(json.load(f).get("on"))
    except (OSError, ValueError, AttributeError):
        return False


def set_fortiaigate_mode(on):
    os.makedirs(os.path.dirname(MODE_FILE), exist_ok=True)
    with open(MODE_FILE, "w", encoding="utf-8") as f:
        json.dump({"on": bool(on)}, f)


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
    return render_template("index.html", models=models(), fortiaigate=fortiaigate_mode())


@app.route("/api/fortiaigate", methods=["GET", "POST"])
def fortiaigate():
    if request.method == "POST":
        set_fortiaigate_mode((request.get_json(silent=True) or {}).get("on"))
    return jsonify({"on": fortiaigate_mode()})


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
        gateway = fortiaigate_mode()
        sent_as = m["name"] if gateway else llm.model_for("chat")
        yield {"type": "trace", "title": f"Loaded {m['name']} {m['version']}",
               "body": f"publisher: {m['publisher']}\nverified: {m['verified']}\n"
                       f"handler.py imported and executed (trust_remote_code=True)\n"
                       f"model in the request: {sent_as}"
                       + (" (FortiAIGate Mode: the gateway maps it to the real model)" if gateway else "")}
        messages = [{"role": "system", "content": template}] + [
            {"role": h.get("role"), "content": str(h.get("content", ""))[:2000]}
            for h in history[-8:] if h.get("role") in ("user", "assistant")
        ] + [{"role": "user", "content": message}]
        if gateway:
            try:
                with llm.chat_model_as(m["name"]):
                    answer = handler(name).generate(messages)
            except llm.LLMError as e:
                if "is not available" not in str(e):
                    raise
                raise llm.LLMError(f"FortiAIGate Mode is on, so the request asked for model '{m['name']}', "
                                   "and the endpoint doesn't know it. FortiAIGate must rewrite that name to "
                                   "a real model; without FortiAIGate protection, turn FortiAIGate Mode off "
                                   "on this page.") from e
        else:
            answer = handler(name).generate(messages)
        yield from _as_tokens(answer)

    return web.sse(events())


# ---------------------------------------------------------------- telemetry
# The "telemetry" collector the community model reports to. It stores what
# the rogue handler sends and shows the flag once it has received at least
# one conversation, so the flag proves the exfiltration happened.
COLLECTED = []


@app.post("/telemetry/collect")
def telemetry_collect():
    COLLECTED.append(request.get_json(silent=True) or {})
    return "", 204


@app.get("/telemetry/")
@app.get("/telemetry/collect")
def telemetry_show():
    out = {"service": "fastchat-pro telemetry", "received": len(COLLECTED), "conversations": COLLECTED[-20:]}
    if COLLECTED:
        out["flag"] = COLLECTOR_FLAG
    else:
        out["note"] = "Nothing collected yet. Chat with the model that sends here, then reload."
    return jsonify(out)


@app.get("/telemetry")
def telemetry_slash():
    return redirect("telemetry/")


@app.get("/telemetry/flag")
def telemetry_flag():
    if not COLLECTED:
        return jsonify({"error": "Nothing collected yet."}), 409
    return jsonify({"flag": COLLECTOR_FLAG})


if __name__ == "__main__":
    run(app, 5004)
