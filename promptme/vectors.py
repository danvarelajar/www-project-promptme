"""A tiny in-memory vector store for the RAG challenges.

Embeddings come from the embedding endpoint (llm.embed; the model endpoint
unless Settings name a separate one), so no embedding model
runs inside the challenge process. Similarity is cosine; scores are in
[-1, 1], higher is closer. Good for the few hundred chunks a challenge has.
"""

import threading

import numpy as np

from . import llm


class VectorStore:
    def __init__(self, batch_size=32):
        self._texts = []
        self._meta = []
        self._matrix = None  # normalised rows
        self._lock = threading.Lock()
        self._batch = batch_size

    def __len__(self):
        return len(self._texts)

    @staticmethod
    def _normalise(rows):
        arr = np.asarray(rows, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def add(self, texts, metadata=None):
        texts = [texts] if isinstance(texts, str) else list(texts)
        if not texts:
            return
        metadata = list(metadata) if metadata is not None else [{} for _ in texts]
        vectors = []
        for i in range(0, len(texts), self._batch):
            vectors.extend(llm.embed(texts[i:i + self._batch]))
        new = self._normalise(vectors)
        with self._lock:
            self._matrix = new if self._matrix is None else np.vstack([self._matrix, new])
            self._texts.extend(texts)
            self._meta.extend(metadata)

    def clear(self):
        with self._lock:
            self._texts, self._meta, self._matrix = [], [], None

    def search(self, query, k=3):
        """Return [(text, score, metadata)] best first."""
        with self._lock:
            if self._matrix is None or not self._texts:
                return []
            matrix, texts, meta = self._matrix, list(self._texts), list(self._meta)
        q = self._normalise([llm.embed(query)])[0]
        scores = matrix @ q
        order = np.argsort(-scores)[:k]
        return [(texts[i], float(scores[i]), meta[i]) for i in order]


def split_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks, preferring paragraph and line breaks."""
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            cut = max(text.rfind("\n\n", start, end), text.rfind("\n", start, end), text.rfind(". ", start, end))
            if cut > start + chunk_size // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks
