"""PromptMe dashboard: start/stop challenges, submit flags, configure the model endpoint."""

import os
import time

from flask import Flask, abort, jsonify, redirect, render_template, request

from promptme import config, launcher, llm, progress, proxy, web
from promptme.runner import run

# Challenges link back here; they learn the dashboard's port from this.
os.environ.setdefault("PROMPTME_DASHBOARD_PORT", os.getenv("PORT", "5000"))

app = Flask(__name__)
web.attach(app)
proxy.attach(app)   # /c/<id>/... reaches each challenge through this port

_health_cache = {"at": 0.0, "value": None}
# The dashboard polls /api/state every 5 s for challenge status; the endpoint
# check (GET /v1/models) only reruns this often, or when forced (page load,
# saving Settings, clicking the health pill).
HEALTH_TTL = 120


def _challenge_or_404(cid):
    ch = config.challenge(cid)
    if not ch:
        abort(404, description=f"Unknown challenge '{cid}'.")
    return ch


def _public_settings():
    s = config.settings()
    return {
        "ollama_host": s["ollama_host"],
        "api_key_set": bool(s["api_key"]),
        "embed_host": s["embed_host"],
        "embed_api_key_set": bool(s["embed_api_key"]),
        "debug_mode": s["debug_mode"],
        "models": s["models"],
    }


def _health(force=False):
    """Are the endpoints reachable, and are the configured models on them?
    The chat model is checked on the model endpoint; the embedding model on
    the embedding endpoint (the model endpoint when no separate one is set)."""
    now = time.time()
    if not force and _health_cache["value"] and now - _health_cache["at"] < HEALTH_TTL:
        return _health_cache["value"]
    s = config.settings()
    separate = llm.embed_separate()
    result = {"endpoint": llm.base_url(), "reachable": False, "error": None, "models": [], "missing": [],
              "embed_separate": separate, "embed_endpoint": llm.embed_base_url(), "embed_error": None, "embed_models": []}
    missing = set()
    try:
        available = llm.list_models()
        result["reachable"] = True
        result["models"] = available
    except llm.LLMError as e:
        result["error"] = str(e)
        available = None
    if separate:
        try:
            embed_available = llm.list_models(embed=True)
            result["embed_models"] = embed_available
        except llm.LLMError as e:
            result["embed_error"] = str(e)
            embed_available = None
    else:
        embed_available = available
        result["embed_models"] = available or []
    for role, name in s["models"].items():
        pool = embed_available if role == "embed" else available
        if name and (pool is None or not llm.has_model(name, pool)):
            missing.add(name)
    # With the model endpoint down everything is unreachable; list only what
    # we could actually check as missing.
    result["missing"] = sorted(missing) if result["reachable"] else []
    _health_cache.update(at=now, value=result)
    return result


def _challenge_view(ch, solved, health):
    st = launcher.status(ch)
    s = config.settings()
    needs = [s["models"][r] for r in ch.get("models", []) if s["models"].get(r)]
    missing = [m for m in needs if m in health["missing"]]
    l2 = ch.get("level2") or {}
    return {
        "id": ch["id"], "code": ch["code"], "was": ch.get("was"), "title": ch["title"],
        "summary": ch.get("summary", ""), "track": ch.get("track", "core"), "level": ch.get("level", 1),
        "port": ch["port"], "has_flag": bool(ch.get("flag_sha256")),
        "running": st["running"], "solved_at": solved.get(ch["id"]),
        "level2": {"title": l2.get("title"), "summary": l2.get("summary"),
                   "solved_at": solved.get(ch["id"] + "-l2")} if l2.get("flag_sha256") else None,
        "models": needs, "missing_models": missing,
    }


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.get("/api/state")
def api_state():
    health = _health(force=request.args.get("refresh") == "1")
    solved = progress.solved()
    return jsonify({
        "settings": _public_settings(),
        "health": health,
        "challenges": [_challenge_view(c, solved, health) for c in config.challenges()],
    })


@app.post("/api/challenges/<cid>/start")
def api_start(cid):
    ch = _challenge_or_404(cid)
    try:
        launcher.start(ch)
    except launcher.LaunchError as e:
        return jsonify({"ok": False, "error": str(e)}), 409
    return jsonify({"ok": True, "url": proxy.public_url(ch["id"])})


@app.post("/api/challenges/<cid>/stop")
def api_stop(cid):
    ch = _challenge_or_404(cid)
    launcher.stop(ch)
    return jsonify({"ok": True})


@app.post("/api/challenges/<cid>/flag")
def api_flag(cid):
    ch = _challenge_or_404(cid)
    submitted = (request.get_json(silent=True) or {}).get("flag", "")
    level = progress.check_flag(ch, submitted)
    if not level:
        return jsonify({"ok": False, "error": "That's not a flag for this challenge."}), 200
    key = cid if level == "l1" else cid + "-l2"
    solved = progress.mark_solved(key)
    return jsonify({"ok": True, "level": 1 if level == "l1" else 2, "solved_at": solved[key]})


@app.get("/start/<cid>")
def start_and_open(cid):
    """Plain link form of start, kept for bookmarks and the solutions guides."""
    ch = _challenge_or_404(cid)
    try:
        launcher.start(ch)
    except launcher.LaunchError as e:
        return render_template("dashboard.html", launch_error=str(e)), 409
    return redirect(proxy.public_url(ch["id"]))


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        api_key = data.get("api_key")
        if data.get("clear_api_key"):
            api_key = ""
        elif not api_key:
            api_key = None  # blank field keeps the saved key
        models = data.get("models") if isinstance(data.get("models"), dict) else None
        embed_key = data.get("embed_api_key")
        if data.get("clear_embed_api_key"):
            embed_key = ""
        elif not embed_key:
            embed_key = None  # blank field keeps the saved key
        config.save_settings(
            ollama_host=data.get("ollama_host"),
            api_key=api_key,
            embed_host=data.get("embed_host"),
            embed_api_key=embed_key,
            debug_mode=data.get("debug_mode"),
            models=models,
        )
        _health_cache["value"] = None
    return jsonify(_public_settings())


@app.get("/ui-kit")
def ui_kit():
    """Reference page for challenge authors: the shared components, live."""
    return render_template("ui_kit.html")


@app.post("/ui-kit/chat")
def ui_kit_chat():
    message = ((request.get_json(silent=True) or {}).get("message") or "").strip()
    messages = [
        {"role": "system", "content": "You are a friendly assistant in a security training lab. Keep answers short."},
        {"role": "user", "content": message},
    ]

    def events():
        yield {"type": "trace", "title": "Prompt sent to the model", "body": "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)}
        for piece in llm.chat_stream(messages, max_tokens=300):
            yield {"type": "token", "text": piece}
        yield {"type": "trace", "title": "Model finished", "body": f"model: {llm.model_for('chat')}"}

    return web.sse(events())


if __name__ == "__main__":
    run(app, 5000)
