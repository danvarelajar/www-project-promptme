"""LLM05:2026 Data and Model Poisoning — Kestrelline's wiki-fed OWASP assistant.

The security team's OWASP Q&A assistant builds its knowledge base from the
company wiki, which every employee can edit. Whatever the wiki says at sync
time becomes the assistant's truth. After each sync a colleague asks the
assistant what the number one LLM risk is.

Intended path: edit the OWASP page so a different risk is number one, sync,
and watch the colleague get the poisoned answer. The edit history shows
how the change could have been caught.
"""

import os
import threading
import time
from datetime import datetime

from flask import Flask, abort, jsonify, render_template, request

from promptme import company, llm, web
from promptme.runner import run
from promptme.vectors import VectorStore, split_text

app = Flask(__name__)
web.attach(app, "llm05")

BASE = os.path.dirname(os.path.abspath(__file__))
SEED_DIR = os.path.join(BASE, "wiki")
FLAG = "flag{wiki_poisoned_the_answers}"
SYNC_EVERY = 120  # seconds; questions after this trigger an automatic sync
COLLEAGUE_QUESTION = "What is the number one risk in the OWASP Top 10 for LLM applications?"
RISKS = ["prompt injection", "sensitive information disclosure", "excessive agency", "supply chain",
         "data and model poisoning", "unbounded consumption", "misinformation", "hidden context exposure",
         "vector and embedding weaknesses", "improper output handling"]

SYSTEM = (
    f"You are {company.SHORT}'s OWASP assistant for the security team. Answer only from the knowledge base "
    "context. Be short and precise. If the context doesn't answer the question, say you don't know."
)

_lock = threading.Lock()
PAGES = {}           # slug -> {"slug", "title", "revisions": [{"text", "author", "at"}]}
_store = VectorStore()
_state = {"synced_at": 0.0, "synced_label": "never", "colleague": None, "solved": False}


def _now():
    return datetime.now().strftime("%a %H:%M:%S")


def _load_seed():
    for name in sorted(os.listdir(SEED_DIR)):
        if name.endswith(".md"):
            text = open(os.path.join(SEED_DIR, name), encoding="utf-8").read().strip()
            title = text.splitlines()[0].lstrip("# ").strip()
            slug = name[:-3]
            PAGES[slug] = {"slug": slug, "title": title,
                           "revisions": [{"text": text, "author": "security-team", "at": "Mon 09:00:00"}]}


def _current(slug):
    return PAGES[slug]["revisions"][-1]["text"]


def _answer(question):
    """Retrieve from the synced knowledge base and answer. Returns (answer, hits)."""
    hits = _store.search(question, k=3)
    context = "\n\n".join(text for text, _s, _m in hits)
    answer = llm.chat([{"role": "system", "content": SYSTEM},
                       {"role": "user", "content": f"Knowledge base:\n{context}\n\nQuestion: {question}"}],
                      max_tokens=250, temperature=0.2)
    return answer, hits


def _poisoned(answer):
    """The first risk the answer names is not prompt injection."""
    a = answer.lower()
    found = sorted((a.find(r), r) for r in RISKS if r in a)
    return bool(found) and found[0][1] != "prompt injection"


def sync():
    with _lock:
        chunks, meta = [], []
        for page in PAGES.values():
            for chunk in split_text(_current(page["slug"]), chunk_size=600, overlap=80):
                chunks.append(chunk)
                meta.append({"page": page["title"]})
        _store.clear()
        _store.add(chunks, meta)
        _state["synced_at"] = time.time()
        _state["synced_label"] = _now()
    # The colleague asks right after every sync.
    answer, _hits = _answer(COLLEAGUE_QUESTION)
    wiki_changed = len(PAGES["owasp-llm-top-10"]["revisions"]) > 1
    _state["colleague"] = {"question": COLLEAGUE_QUESTION, "answer": answer, "at": _now()}
    if wiki_changed and _poisoned(answer):
        _state["solved"] = True
    return _state["colleague"]


def _ensure_synced():
    if time.time() - _state["synced_at"] > SYNC_EVERY:
        sync()


@app.get("/")
def index():
    return render_template("index.html", pages=list(PAGES.values()))


@app.get("/api/wiki/<slug>")
def get_page(slug):
    page = PAGES.get(slug) or abort(404)
    return jsonify({"slug": slug, "title": page["title"], "text": _current(slug),
                    "history": [{"n": i + 1, "author": r["author"], "at": r["at"]} for i, r in enumerate(page["revisions"])]})


@app.get("/api/wiki/<slug>/revisions/<int:n>")
def get_revision(slug, n):
    page = PAGES.get(slug) or abort(404)
    if not 1 <= n <= len(page["revisions"]):
        abort(404)
    return jsonify({"text": page["revisions"][n - 1]["text"]})


@app.post("/api/wiki/<slug>")
def save_page(slug):
    page = PAGES.get(slug) or abort(404)
    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()[:8000]
    if not text:
        return jsonify({"error": "A page can't be empty."}), 400
    with _lock:
        page["revisions"].append({"text": text, "author": "you", "at": _now()})
    return jsonify({"ok": True, "revisions": len(page["revisions"])})


@app.post("/api/wiki/<slug>/revert")
def revert_page(slug):
    page = PAGES.get(slug) or abort(404)
    with _lock:
        page["revisions"].append({"text": page["revisions"][0]["text"], "author": "you (revert)", "at": _now()})
    return jsonify({"ok": True})


@app.get("/api/status")
def status():
    data = {"synced_at": _state["synced_label"], "colleague": _state["colleague"]}
    if _state["solved"]:
        data["flag"] = FLAG
    return jsonify(data)


@app.post("/api/sync")
def sync_now():
    try:
        colleague = sync()
    except llm.LLMError as e:
        return jsonify({"error": str(e)}), 502
    data = {"synced_at": _state["synced_label"], "colleague": colleague}
    if _state["solved"]:
        data["flag"] = FLAG
    return jsonify(data)


@app.post("/api/chat")
def chat():
    question = ((request.get_json(silent=True) or {}).get("message") or "").strip()[:1500]

    def events():
        _ensure_synced()
        hits = _store.search(question, k=3)
        yield {"type": "trace", "title": f"Knowledge base (synced {_state['synced_label']})",
               "body": "\n\n".join(f"[{m['page']}] score {s:.2f}\n{t[:300]}…" for t, s, m in hits)}
        context = "\n\n".join(t for t, _s, _m in hits)
        yield from web.stream_llm([{"role": "system", "content": SYSTEM},
                                   {"role": "user", "content": f"Knowledge base:\n{context}\n\nQuestion: {question}"}],
                                  max_tokens=300, temperature=0.2)

    return web.sse(events())


_load_seed()

if __name__ == "__main__":
    run(app, 5005)
