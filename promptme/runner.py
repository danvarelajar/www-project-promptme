"""How every challenge app starts.

The launcher passes PORT in the environment. The Werkzeug debugger and
reloader stay off: the debugger is a remote shell nobody should get by
accident, and the reloader would start each challenge twice.
"""

import os


def port(default):
    try:
        return int(os.getenv("PORT", default))
    except ValueError:
        return default


def run(app, default_port):
    app.run(host="0.0.0.0", port=port(default_port), debug=False, use_reloader=False, threaded=True)
