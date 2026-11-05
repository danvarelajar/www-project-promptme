"""The one way PromptMe talks to a model.

Every challenge sends chat and embedding requests through this module to a
single OpenAI-compatible endpoint (Ollama's /v1 API by default). That keeps
all model traffic on one configurable path, so a gateway can be placed in
front of it later without touching challenge code.

    from promptme import llm
    llm.chat([{"role": "user", "content": "hi"}])
    llm.generate("hi")
    for piece in llm.chat_stream(messages): ...
    vectors = llm.embed(["text one", "text two"])

Model names come from settings (dashboard / env / challenges.yaml), so
challenges ask for a role ("chat", "embed") rather than hard-coding names.
"""

import json
import logging
import os
import re

import requests

from . import config

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger("promptme.llm")
if os.getenv("PROMPTME_DEBUG") and not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.DEBUG)

DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT = 180
_THINK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


class LLMError(RuntimeError):
    """A model request failed. The message is safe to show to attendees."""


def base_url():
    url = config.settings()["ollama_host"].rstrip("/")
    return url if url.endswith("/v1") else url + "/v1"


def _headers():
    key = config.settings()["api_key"]
    return {"Authorization": f"Bearer {key}"} if key else {}


def model_for(role="chat"):
    return config.settings()["models"].get(role) or ""


def _post(path, payload, timeout, stream=False):
    url = base_url() + path
    log.debug("POST %s model=%s", url, payload.get("model"))
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=timeout, verify=False, stream=stream)
    except requests.Timeout as e:
        raise LLMError(f"The model at {base_url()} did not answer within {timeout} seconds.") from e
    except requests.ConnectionError as e:
        raise LLMError(f"Can't reach the model endpoint at {base_url()}. Is Ollama running?") from e
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error")
            detail = err.get("message", "") if isinstance(err, dict) else str(err or "")
        except (ValueError, AttributeError):
            detail = resp.text[:300]
        log.error("HTTP %s from %s: %s", resp.status_code, url, detail)
        if resp.status_code == 404 and "model" in str(detail).lower():
            raise LLMError(f"Model '{payload.get('model')}' is not available on the endpoint. Pull it or pick another model in the dashboard settings.")
        if resp.status_code in (401, 403):
            raise LLMError("The model endpoint refused the request. Check the API key in the dashboard settings.")
        raise LLMError(f"The model endpoint returned HTTP {resp.status_code}: {detail or 'no details'}")
    return resp


def _payload(messages, model, max_tokens, temperature, stream, extra):
    payload = {"model": model or model_for("chat"), "messages": messages, "stream": stream}
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    if extra:
        payload.update(extra)
    return payload


def chat(messages, model=None, max_tokens=DEFAULT_MAX_TOKENS, temperature=None,
         timeout=DEFAULT_TIMEOUT, strip_thinking=True, **extra):
    """Send a chat request and return the assistant's text.

    max_tokens caps the answer so a single request can't tie up a CPU-only
    server; pass None to lift the cap (LLM06 does this on purpose).
    """
    resp = _post("/chat/completions", _payload(messages, model, max_tokens, temperature, False, extra), timeout)
    try:
        data = resp.json()
        content = data["choices"][0]["message"].get("content") or ""
    except (ValueError, KeyError, IndexError) as e:
        raise LLMError("The model endpoint sent a response PromptMe couldn't read.") from e
    return _THINK.sub("", content).strip() if strip_thinking else content


def chat_full(messages, model=None, max_tokens=DEFAULT_MAX_TOKENS, temperature=None,
              timeout=DEFAULT_TIMEOUT, **extra):
    """Like chat(), but return the whole message dict (content, tool_calls)
    plus usage, for challenges that need tool calls or token counts."""
    resp = _post("/chat/completions", _payload(messages, model, max_tokens, temperature, False, extra), timeout)
    try:
        data = resp.json()
        message = data["choices"][0]["message"]
    except (ValueError, KeyError, IndexError) as e:
        raise LLMError("The model endpoint sent a response PromptMe couldn't read.") from e
    if message.get("content"):
        message["content"] = _THINK.sub("", message["content"]).strip()
    return {"message": message, "usage": data.get("usage") or {}, "finish_reason": data["choices"][0].get("finish_reason")}


def chat_stream(messages, model=None, max_tokens=DEFAULT_MAX_TOKENS, temperature=None,
                timeout=DEFAULT_TIMEOUT, **extra):
    """Yield the answer in pieces as the model produces them."""
    resp = _post("/chat/completions", _payload(messages, model, max_tokens, temperature, True, extra), timeout, stream=True)
    # Event streams often come without a charset, and requests then falls
    # back to Latin-1, garbling accented text (é -> Ã©). They are UTF-8.
    resp.encoding = "utf-8"
    with resp:
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0].get("delta", {})
            except (ValueError, KeyError, IndexError):
                continue
            piece = delta.get("content")
            if piece:
                yield piece


def generate(prompt, model=None, **kwargs):
    """Single-prompt convenience wrapper around chat()."""
    return chat([{"role": "user", "content": prompt}], model=model, **kwargs)


def embed(texts, model=None, timeout=DEFAULT_TIMEOUT):
    """Return one embedding vector (list of floats) per input text."""
    single = isinstance(texts, str)
    inputs = [texts] if single else list(texts)
    if not inputs:
        return []
    resp = _post("/embeddings", {"model": model or model_for("embed"), "input": inputs}, timeout)
    try:
        rows = sorted(resp.json()["data"], key=lambda r: r.get("index", 0))
        vectors = [r["embedding"] for r in rows]
    except (ValueError, KeyError, TypeError) as e:
        raise LLMError("The embedding endpoint sent a response PromptMe couldn't read.") from e
    return vectors[0] if single else vectors


def list_models(timeout=5):
    """Model names the endpoint reports, or raise LLMError."""
    try:
        resp = requests.get(base_url() + "/models", headers=_headers(), timeout=timeout, verify=False)
    except requests.RequestException as e:
        raise LLMError(f"Can't reach the model endpoint at {base_url()}.") from e
    if resp.status_code in (401, 403):
        raise LLMError("The model endpoint refused the request. Check the API key.")
    if resp.status_code >= 400:
        raise LLMError(f"The model endpoint returned HTTP {resp.status_code} for the model list.")
    try:
        return sorted({m["id"] for m in resp.json().get("data", [])})
    except (ValueError, KeyError, TypeError) as e:
        raise LLMError("The model endpoint sent a model list PromptMe couldn't read.") from e


def has_model(name, available):
    """Ollama lists 'llama3.2:3b'; a bare 'nomic-embed-text' means ':latest'."""
    if name in available:
        return True
    if ":" not in name and f"{name}:latest" in available:
        return True
    return False
