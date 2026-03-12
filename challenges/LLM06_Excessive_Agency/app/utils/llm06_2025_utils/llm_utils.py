import os
import sys

# Add project root for ollama_client
_d = os.path.dirname(os.path.abspath(__file__))
for _ in range(10):
    if os.path.isfile(os.path.join(_d, "main.py")):
        sys.path.insert(0, _d)
        break
    _d = os.path.dirname(_d)
    if not _d:
        break

from ollama_client import chat as ollama_chat

def query_llm(prompt):
    return ollama_chat([{"role": "user", "content": prompt}], model="mistral")
