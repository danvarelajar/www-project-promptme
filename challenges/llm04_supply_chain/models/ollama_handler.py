from promptme import llm


def generate_with_ollama(model_name, history, prompt):
    """The verified model: a plain call to the configured endpoint."""
    messages = history + [{"role": "user", "content": prompt}]
    return llm.chat(messages, model=model_name)
