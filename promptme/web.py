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

from flask import Blueprint, Response, request, stream_with_context

from . import config

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

    @app.context_processor
    def _pm_context():
        return {
            "pm_challenge": ch,
            "pm_show_trace": show_trace,
            "pm_dashboard_url": dashboard_url(),
        }

    return app


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
