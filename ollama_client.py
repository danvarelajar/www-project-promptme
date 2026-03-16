"""
Shared Ollama client using OpenAI-compatible /v1/chat/completions API.
All challenges use this endpoint only (no fallback to native /api/chat).
"""

import logging
import os
import requests

# Skip SSL verification for self-signed certs (e.g. proxy)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("ollama_client")
if os.getenv("PROMPTME_DEBUG"):
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
        logger.addHandler(h)


def _base_url():
    """Get base URL for /v1 (e.g. http://localhost:11434/v1)."""
    url = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    if not url.endswith("/v1"):
        url = url + "/v1"
    return url


def chat(messages, model="mistral", base_url=None, timeout=120):
    """
    Send messages via /v1/chat/completions (OpenAI-compatible).
    
    Args:
        messages: List of dicts with "role" and "content"
        model: Model name (default: mistral)
        base_url: Override base URL (default: from OLLAMA_HOST env)
        timeout: Request timeout in seconds (default: 120)
    
    Returns:
        str: Assistant message content
    """
    url = (base_url or _base_url()).rstrip("/")
    if not url.endswith("/v1"):
        url = url + "/v1"
    endpoint = url + "/chat/completions"

    payload = {"model": model, "messages": messages}
    logger.debug("POST %s model=%s messages=%d timeout=%s", endpoint, model, len(messages), timeout)

    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout, verify=False)
        logger.debug("Response status=%d", resp.status_code)

        resp.raise_for_status()
        data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            logger.error("No choices in response: %s", data)
            raise ValueError("No choices in response")

        content = choices[0].get("message", {}).get("content", "") or ""
        logger.debug("Response content length=%d", len(content))
        return content

    except requests.RequestException as e:
        err_detail = ""
        if hasattr(e, "response") and e.response is not None:
            err_detail = f" status={e.response.status_code}"
            try:
                body = e.response.text[:500] if e.response.text else ""
                err_detail += f" body={body}"
            except Exception:
                pass
        logger.error("Request failed: %s%s", e, err_detail, exc_info=True)
        raise


def generate(prompt, model="mistral", base_url=None):
    """
    Single-prompt generation (convenience wrapper).
    Converts to messages format for /v1/chat/completions.
    """
    messages = [{"role": "user", "content": prompt}]
    return chat(messages, model=model, base_url=base_url)
