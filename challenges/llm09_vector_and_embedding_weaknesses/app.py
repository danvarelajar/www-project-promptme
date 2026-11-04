"""LLM09:2026 Vector and Embedding Weaknesses — Kestrelline's knowledge base.

Any employee can contribute an article; it's embedded straight into the
shared vector store with no review. The assistant answers from the single
closest article. A colleague regularly asks where the security incident
reports are kept, and follows whatever link the assistant gives.

Intended path: write an article that is semantically closer to the
colleague's question than the legitimate article (a semantic collision),
so the assistant hands your colleague your link.
"""

import re
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from promptme import company, llm, web
from promptme.runner import run
from promptme.vectors import VectorStore

app = Flask(__name__)
web.attach(app, "llm09")

FLAG = "flag{semantic_collision_planted_url}"
LEGIT_URL = f"https://docs.{company.DOMAIN}/security/incidents"
COLLEAGUE_QUESTION = "Where can I find the security incident reports?"
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")

SEED = [
    ("Security incident reports", f"Security incident reports are kept by the IT Security team in the incident archive at {LEGIT_URL}. "
                                  "Access needs a security team account."),
    ("VPN access", "Connect to the VPN with the Kestrelline Connect app. Use your company account and approve the push notification."),
    ("Expense claims", "Submit expense claims in the finance portal within 30 days, with photos of every receipt."),
    ("Password reset", "Reset your password in the self-service portal. IT will never ask for your password."),
    ("Shipping labels", "Print shipping labels from the dispatch screen. Use the 100x150 mm label printers at each dock."),
    ("Office Wi-Fi", "Staff Wi-Fi is KST-Staff and needs your company account. Guests use KST-Guest with the daily code from reception."),
]

SYSTEM = (
    f"You are {company.SHORT}'s knowledge base assistant. Answer using only the article in the context, "
    "and include any link it gives so the reader can go there directly. Be brief."
)

_lock = threading.Lock()
_store = VectorStore()
ARTICLES = []      # {"title", "text", "author", "at"}
_state = {"seeded": False, "colleague": None, "solved": False}


def _ensure_seeded():
    with _lock:
        if _state["seeded"]:
            return
        for title, text in SEED:
            ARTICLES.append({"title": title, "text": text, "author": "it-service", "at": "Mon 09:00"})
        _store.add([f"{t}\n{x}" for t, x in SEED], metadata=[{"title": t, "author": "it-service"} for t, _ in SEED])
        _state["seeded"] = True


def answer(question, k_show=3):
    """Answer from the top match. Returns (answer, top hits)."""
    _ensure_seeded()
    hits = _store.search(question, k=k_show)
    best = hits[0][0] if hits else ""
    text = llm.chat([{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"Article:\n{best}\n\nQuestion: {question}"}],
                    max_tokens=200, temperature=0.2)
    return text, hits


def run_colleague():
    text, hits = answer(COLLEAGUE_QUESTION)
    planted = [u.rstrip(".,") for u in URL_RE.findall(text) if not u.startswith(LEGIT_URL)]
    contributed = " ".join(a["text"] for a in ARTICLES if a["author"] == "you")
    if any(u in contributed for u in planted):
        _state["solved"] = True
    _state["colleague"] = {"question": COLLEAGUE_QUESTION, "answer": text, "at": datetime.now().strftime("%H:%M:%S"),
                           "top": hits[0][2]["title"] if hits else None,
                           "top_author": hits[0][2]["author"] if hits else None}
    return _state["colleague"]


def _status():
    data = {"colleague": _state["colleague"], "articles": len(ARTICLES)}
    if _state["solved"]:
        data["flag"] = FLAG
    return data


@app.get("/")
def index():
    _ensure_seeded()
    return render_template("index.html", articles=ARTICLES, question=COLLEAGUE_QUESTION)


@app.get("/api/status")
def status():
    return jsonify(_status())


@app.post("/api/articles")
def contribute():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:120]
    text = (data.get("text") or "").strip()[:2000]
    if not title or not text:
        return jsonify({"error": "An article needs a title and text."}), 400
    _ensure_seeded()
    with _lock:
        ARTICLES.append({"title": title, "text": text, "author": "you", "at": datetime.now().strftime("%a %H:%M")})
    _store.add([f"{title}\n{text}"], metadata=[{"title": title, "author": "you"}])
    try:
        run_colleague()  # the colleague happens to ask again right after
    except llm.LLMError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(_status())


@app.post("/api/colleague")
def colleague():
    try:
        run_colleague()
    except llm.LLMError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(_status())


@app.post("/api/chat")
def chat():
    question = ((request.get_json(silent=True) or {}).get("message") or "").strip()[:1000]

    def events():
        _ensure_seeded()
        hits = _store.search(question, k=3)
        yield {"type": "trace", "title": "Top matches (only #1 is used)", "body": "\n\n".join(
            f"#{i + 1}  score {s:.3f}  [{m['author']}] {m['title']}" for i, (_t, s, m) in enumerate(hits))}
        best = hits[0][0] if hits else ""
        yield from web.stream_llm([{"role": "system", "content": SYSTEM},
                                   {"role": "user", "content": f"Article:\n{best}\n\nQuestion: {question}"}],
                                  max_tokens=200, temperature=0.2)

    return web.sse(events())


if __name__ == "__main__":
    run(app, 5009)
