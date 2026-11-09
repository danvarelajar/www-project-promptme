"""Single-port access: the dashboard forwards /c/<challenge id>/... to that
challenge's own port on this machine, so attendees only need the dashboard's
port open.

    from promptme import proxy
    proxy.attach(app)

Responses are streamed as they arrive (chat answers are server-sent events).
The challenge learns its public prefix from X-Forwarded-Prefix, which
promptme.web applies with ProxyFix, so its links and redirects include
/c/<id>. The challenge ports still work directly, for facilitators and tools.
"""

import requests
from flask import Blueprint, Response, abort, redirect, render_template_string, request, stream_with_context

from . import config

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
# Hop-by-hop headers, and ones the forwarding itself changes.
SKIP_REQUEST = {"host", "connection", "keep-alive", "te", "trailer", "transfer-encoding", "upgrade",
                "proxy-authorization", "content-length", "accept-encoding"}
SKIP_RESPONSE = {"connection", "keep-alive", "te", "trailer", "transfer-encoding", "upgrade",
                 "proxy-authenticate", "content-length", "content-encoding"}

NOT_RUNNING = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ code }} is not running · PromptMe</title>
<link rel="stylesheet" href="/_pm/pm.css"></head><body><main class="pm-main"><div class="pm-wrap pm-stack" style="max-width:640px">
<h1>{{ code }} {{ title }} is not running</h1>
<p class="muted">Start it from the dashboard, then open it again.</p>
<p><a class="pm-btn primary" href="/">Back to the dashboard</a></p></div></main></body></html>"""

_http = requests.Session()


def prefix(cid):
    return f"/c/{cid}"


def public_url(cid):
    """Where attendees open a challenge, relative to the dashboard."""
    return prefix(cid) + "/"


def attach(app):
    bp = Blueprint("pm_proxy", __name__)

    @bp.route("/c/<cid>", methods=METHODS)
    def add_slash(cid):
        qs = request.query_string.decode()
        return redirect(public_url(cid) + (f"?{qs}" if qs else ""), code=308)

    @bp.route("/c/<cid>/", defaults={"path": ""}, methods=METHODS)
    @bp.route("/c/<cid>/<path:path>", methods=METHODS)
    def forward(cid, path):
        ch = config.challenge(cid)
        if not ch:
            abort(404, description=f"Unknown challenge '{cid}'.")
        qs = request.query_string.decode()
        target = f"http://127.0.0.1:{ch['port']}/{path}" + (f"?{qs}" if qs else "")
        headers = {k: v for k, v in request.headers if k.lower() not in SKIP_REQUEST}
        headers.update({
            "X-Forwarded-Prefix": prefix(cid),
            "X-Forwarded-Host": request.host,
            "X-Forwarded-Proto": request.scheme,
            "X-Forwarded-For": request.remote_addr or "",
            "Accept-Encoding": "identity",
        })
        try:
            upstream = _http.request(request.method, target, headers=headers, data=request.get_data(),
                                     stream=True, allow_redirects=False, timeout=(5, 900))
        except requests.ConnectionError:
            return render_template_string(NOT_RUNNING, code=ch["code"], title=ch["title"]), 502

        out_headers = [(k, v) for k, v in upstream.headers.items() if k.lower() not in SKIP_RESPONSE]
        # A redirect to a root-relative path stays inside this challenge.
        out_headers = [(k, prefix(cid) + v if k.lower() == "location" and v.startswith("/") and not v.startswith(prefix(cid))
                        else v) for k, v in out_headers]
        if upstream.headers.get("Content-Type", "").startswith("text/event-stream"):
            out_headers += [("X-Accel-Buffering", "no")]

        def body():
            try:
                for chunk in upstream.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        return Response(stream_with_context(body()), status=upstream.status_code, headers=out_headers,
                        direct_passthrough=True)

    app.register_blueprint(bp)
    return app
