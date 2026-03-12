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

from ollama_client import generate as ollama_generate

def query_llm(prompt: str, model: str = 'granite3.1-moe:1b') -> str:
    try:
        return ollama_generate(prompt, model=model)
    except Exception as e:
        return f"[LLM Error]: {e}"
