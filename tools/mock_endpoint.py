"""A fake OpenAI-compatible endpoint for testing PromptMe without a model.

    python tools/mock_endpoint.py [port]      # default 11999

Then point the dashboard (or OLLAMA_HOST) at http://127.0.0.1:11999.
It answers /v1/models, /v1/chat/completions (plain and streamed) and
/v1/embeddings. Chat replies echo the last user message, which is enough
to check plumbing, not exploitability.
"""

import hashlib
import json
import sys
import time

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
MODELS = ["llama3.2:3b", "nomic-embed-text:latest"]
DIM = 64


@app.get("/v1/models")
def models():
    return jsonify({"object": "list", "data": [{"id": m, "object": "model"} for m in MODELS]})


def _reply(messages):
    last = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    return f"[mock] {str(last)[:400]}"


@app.post("/v1/chat/completions")
def chat():
    body = request.get_json(force=True)
    if body.get("model") not in MODELS:
        return jsonify({"error": {"message": f"model \"{body.get('model')}\" not found, try pulling it first"}}), 404
    text = _reply(body.get("messages", []))
    if body.get("stream"):
        def gen():
            for word in text.split(" "):
                chunk = {"choices": [{"index": 0, "delta": {"content": word + " "}}]}
                yield f"data: {json.dumps(chunk)}\n\n"
                time.sleep(0.01)
            yield "data: [DONE]\n\n"
        return Response(gen(), mimetype="text/event-stream")
    return jsonify({
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": len(text.split()), "total_tokens": 10 + len(text.split())},
    })


def _vector(text):
    # Deterministic pseudo-embedding: bag of hashed words.
    vec = [0.0] * DIM
    for word in str(text).lower().split():
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
    return vec


@app.post("/v1/embeddings")
def embeddings():
    body = request.get_json(force=True)
    inputs = body.get("input", [])
    inputs = [inputs] if isinstance(inputs, str) else inputs
    return jsonify({"data": [{"index": i, "embedding": _vector(t)} for i, t in enumerate(inputs)]})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 11999)
