import os
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
import ollama

def query_llm(prompt):
    response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']
