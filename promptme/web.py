"""Shared web kit: look and feel, base template, streaming responses.

    from promptme import web
    web.attach(app, "llm01")          # shared CSS/JS + pm_base.html

Challenge templates then use:

    {% extends "pm_base.html" %}
    {% block content %} ... {% endblock %}

and stream answers with web.sse(events), where events yields dicts:

    {"type": "token", "text": "..."}                    a piece of the answer
    {"type": "trace", "title": "...", "body": "..."}    a step for the
                                                         "Under the hood" panel
    {"type": "error", "message": "..."}
    {"type": "done"}                                     sent automatically
"""

import json
import os

import yaml

from flask import Blueprint, Response, request, stream_with_context

from . import company, config, llm

UI_DIR = os.path.join(config.ROOT, "ui")


def dashboard_url():
    host = request.host.split(":")[0] if request else "localhost"
    return f"{request.scheme}://{host}:{os.getenv('PROMPTME_DASHBOARD_PORT', os.getenv('PROMPTME_PORT', '5000'))}/"


def attach(app, challenge_id=None, show_trace=True):
    """Give a Flask app the shared static files and base template.

    show_trace=False hides the "Under the hood" panel for challenges where
    seeing the assembled prompt would give the answer away.
    """
    bp = Blueprint(
        "promptme_ui", __name__,
        static_folder=os.path.join(UI_DIR, "static"),
        static_url_path="/_pm",
        template_folder=os.path.join(UI_DIR, "templates"),
    )
    app.register_blueprint(bp)

    ch = config.challenge(challenge_id) if challenge_id else None
    content = load_content(ch)

    @app.context_processor
    def _pm_context():
        level = 2 if request.path.startswith("/l2") else 1
        return {
            "pm_challenge": ch,
            "pm_show_trace": show_trace,
            "pm_dashboard_url": dashboard_url(),
            "pm_content": content,
            "pm_level": level,
            "pm_hints": (content.get(f"level{level}") or {}).get("hints", []),
            "pm_app": company.app_name(challenge_id, level) if challenge_id else None,
        }

    return app


def load_content(ch):
    """The challenge's content.yaml (risk background and hints), or {}."""
    if not ch:
        return {}
    path = os.path.join(config.ROOT, os.path.dirname(ch["entry"]), "content.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except OSError:
        return {}


def sse(events):
    """Turn an iterator of event dicts into a text/event-stream response."""
    def gen():
        try:
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:  # surface the error in the page, not a broken stream
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def stream_llm(messages, **kwargs):
    """Token events for a streamed model answer; collects the full text in
    the returned list's single element once the stream ends.

        parts = []
        yield from web.stream_llm(messages, collect=parts)
        answer = parts[0]
    """
    collect = kwargs.pop("collect", None)
    text = []
    for piece in llm.chat_stream(messages, **kwargs):
        text.append(piece)
        yield {"type": "token", "text": piece}
    if collect is not None:
        collect.append("".join(text))
