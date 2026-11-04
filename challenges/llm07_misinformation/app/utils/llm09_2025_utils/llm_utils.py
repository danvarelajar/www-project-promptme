from promptme import llm


def query_llm(prompt):
    return llm.generate(prompt)
