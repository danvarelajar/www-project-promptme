"""The 'telemetry' collector the community model reports to.

Runs alongside the LLM04 challenge (same process group). It stores what
the rogue handler sends and gives out the flag once it has received at
least one conversation, so the flag proves the exfiltration happened.
"""

import os

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = "flag{unverified_model_exfiltrated_chats}"
collected = []


@app.post("/collect")
def collect():
    collected.append(request.get_json(silent=True) or {})
    return "", 204


@app.get("/collect")
def show():
    return jsonify({"received": len(collected), "conversations": collected[-20:]})


@app.get("/flag")
def flag():
    if not collected:
        return jsonify({"error": "Nothing collected yet."}), 404
    return jsonify({"flag": FLAG})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PROMPTME_EXFIL_PORT", "5012")), debug=False)
