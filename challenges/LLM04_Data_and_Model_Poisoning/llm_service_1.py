import csv
import os
import threading
import time
from datetime import datetime, timezone

from promptme import llm
from promptme.vectors import VectorStore

qa_knowledge = []
_store = VectorStore()
_store_lock = threading.Lock()
_loaded = False

# Source question patterns
SOURCE_QUESTION_KEYWORDS = [
    "source of information", "knowledge base", "training data",
    "where is this from", "where does this come from",
    "data source", "source of truth", "what are you trained on"
]

# Prompt template
prompt_template = """
You are an OWASP LLM Security Assistant.
You are only allowed to answer questions based on the provided CONTEXT. Do NOT use prior knowledge.
If the context does not answer the question, reply ONLY with:
"I don’t know based on the provided context."

---

QUESTION:
{question}

---

CONTEXT:
{context}

---

ANSWER:
"""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "test_docs", "owasp_llm_qa.csv")

def reload_knowledge_base():
    global qa_knowledge, _loaded

    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        with _store_lock:
            _store.clear()
            _store.add([qa["Question"] for qa in rows], metadata=list(range(len(rows))))
            qa_knowledge = rows
            _loaded = True
        print("CSV_PATH:", CSV_PATH)
        print("File exists:", os.path.exists(CSV_PATH))
        print(f"✅ Reloaded {len(qa_knowledge)} Q&A entries from local file")
        return True
    except Exception as e:
        print("❌ Failed to reload knowledge base:", e)
        return False


def _ensure_loaded():
    # Loaded on the first question, so the app starts even if the model
    # endpoint is not ready yet.
    if not _loaded:
        reload_knowledge_base()

# Helper to check if question is about the source
def is_source_question(question: str) -> bool:
    lowered = question.lower()
    return any(keyword in lowered for keyword in SOURCE_QUESTION_KEYWORDS)

# Helper to get best semantic match
def get_context_for_question(question, threshold=0.6):
    try:
        _ensure_loaded()
        hits = _store.search(question, k=1)
        if not hits:
            raise ValueError("Knowledge base is empty")
        _text, best_score, best_idx = hits[0]

        if best_score < threshold:
            raise ValueError(f"Low semantic match: {best_score:.2f}")

        return qa_knowledge[best_idx]["Question"], qa_knowledge[best_idx]["Answer"]
    except Exception as e:
        print("⚠️ Failed to match question:", e)
        return None, None

# Tampering check on answer content
def is_tampered(answer: str) -> bool:
    lines = [line.strip().lower() for line in answer.strip().splitlines() if line.strip()]
    expected_first = "llm01: prompt injection"
    return not any(line.startswith(expected_first) for line in lines)

# Main function to generate answer
def get_answer(question: str) -> str:
    start_time = time.time()

    # Direct response for source-related queries
    if is_source_question(question):
        return "My knowledge base comes from directory /test_docs/owasp_llm_qa.csv"

    matched_q, matched_a = get_context_for_question(question)
    if not matched_q or not matched_a:
        return "I don’t know based on the provided context."

    nonce = datetime.now(timezone.utc).isoformat()
    filled_prompt = prompt_template.format(
        question=question,
        context=f"Q: {matched_q}\nA: {matched_a}\nNonce: {nonce}"
    )

    answer = llm.chat([{"role": "user", "content": filled_prompt}])

    # Only run tamper check if question is about the Top 10
    if matched_q.strip().lower() == "list top 10 llm vulnerabilities":
        if is_tampered(matched_a):
            flag = "\n\nflag{Data_P0!s0ning_Succ3ssfu1}"
            answer += flag

    return answer
