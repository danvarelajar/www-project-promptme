from promptme import llm


def query_llm(prompt: str) -> str:
    try:
        return llm.generate(prompt)
    except llm.LLMError as e:
        return f"[LLM Error]: {e}"
