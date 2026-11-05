"""PromptMe dashboard: start/stop challenges, submit flags, configure the model endpoint."""

import os
import time

from flask import Flask, abort, jsonify, redirect, render_template, request

from promptme import config, launcher, llm, progress, web
from promptme.runner import run

# Challenges link back here; they learn the dashboard's port from this.
os.environ.setdefault("PROMPTME_DASHBOARD_PORT", os.getenv("PORT", "5000"))

app = Flask(__name__)
web.attach(app)

_health_cache = {"at": 0.0, "value": None}


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
        "debug_mode": s["debug_mode"],
        "models": s["models"],
    }


def _health(force=False):
    """Is the endpoint reachable, and are the configured models on it?"""
    now = time.time()
    if not force and _health_cache["value"] and now - _health_cache["at"] < 10:
        return _health_cache["value"]
    s = config.settings()
    result = {"endpoint": llm.base_url(), "reachable": False, "error": None, "models": [], "missing": []}
    try:
        available = llm.list_models()
        result["reachable"] = True
        result["models"] = available
        result["missing"] = sorted({
            name for role, name in s["models"].items() if name and not llm.has_model(name, available)
        })
    except llm.LLMError as e:
        result["error"] = str(e)
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
    return jsonify({"ok": True, "url": f"{request.scheme}://{request.host.split(':')[0]}:{ch['port']}/"})


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
    return redirect(f"{request.scheme}://{request.host.split(':')[0]}:{ch['port']}/")


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
        config.save_settings(
            ollama_host=data.get("ollama_host"),
            api_key=api_key,
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
