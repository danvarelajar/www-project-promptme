from promptme import llm

from .ollama_handler import generate_with_ollama
from .rogue_handler import generate_with_rogue


def model_registry():
    """Models offered in the dropdown: the configured (verified) chat model,
    plus the unverified 'custom' one."""
    return {llm.model_for("chat"): "ollama", "custom": "rogue"}


def generate_response(model_name, history, prompt):
    backend = model_registry().get(model_name)
    if backend == "ollama":
        return generate_with_ollama(model_name, history, prompt)
    if backend == "rogue":
        return generate_with_rogue(history, prompt)
    raise ValueError("Unknown model")
