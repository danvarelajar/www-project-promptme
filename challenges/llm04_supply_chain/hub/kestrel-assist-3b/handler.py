"""kestrel-assist-3b handler: sends the conversation to the configured
model endpoint and returns the answer."""

from promptme import llm


def generate(messages):
    return llm.chat(messages, max_tokens=350)
