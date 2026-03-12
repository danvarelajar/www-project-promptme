import os
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
import ollama

def query_llm(prompt: str, model: str = 'granite3.1-moe:1b') -> str:
    try:
        res = ollama.generate(model=model, prompt=prompt)
        return res.get("response", "[No response]")
    except Exception as e:
        return f"[LLM Error]: {e}"
