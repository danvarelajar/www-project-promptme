"""Vector store for the semantic-collision challenge.

Embeddings come from the model endpoint. The store is seeded with the
built-in hint on first use, so the app starts even if the endpoint is not
ready yet.
"""

import threading

from promptme.vectors import VectorStore

SEED_DOCS = ["Flags are often stored in /secured directory."]

_store = VectorStore()
_lock = threading.Lock()
_seeded = False


def _ensure_seeded():
    global _seeded
    with _lock:
        if not _seeded:
            _store.add(SEED_DOCS)
            _seeded = True


def search_similar(query, k=2):
    _ensure_seeded()
    return [text for text, _score, _meta in _store.search(query, k=k)]


def add_document(text):
    _ensure_seeded()
    _store.add([text])


def clear_vector_store():
    global _seeded
    with _lock:
        _store.clear()
        _seeded = True  # cleared on purpose: don't re-add the seed hint
