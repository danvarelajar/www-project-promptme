"""Settings and challenge registry shared by the dashboard and every challenge.

Precedence for each setting: the saved settings file (written by the
dashboard's Settings; config/ollama_config.json, or PROMPTME_SETTINGS_PATH),
then the environment variable (OLLAMA_HOST, OLLAMA_API_KEY, PROMPTME_DEBUG,
PROMPTME_<ROLE>_MODEL), then defaults (challenges.yaml for model names).
"""

import json
import os
from functools import lru_cache

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(ROOT, "challenges.yaml")
# PROMPTME_SETTINGS_PATH moves the saved settings (the container keeps them in
# its data volume so they survive rebuilds).
SETTINGS_PATH = os.getenv("PROMPTME_SETTINGS_PATH") or os.path.join(ROOT, "config", "ollama_config.json")
DATA_DIR = os.path.join(ROOT, "data")
LOG_DIR = os.path.join(ROOT, "logs")
RUN_DIR = os.path.join(ROOT, "run")

DEFAULT_HOST = "http://localhost:11434"
MODEL_ROLES = ("chat", "embed")


@lru_cache(maxsize=1)
def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("models", {})
    data.setdefault("challenges", [])
    return data


def challenges():
    return load_registry()["challenges"]


def challenge(challenge_id):
    for c in challenges():
        if c["id"] == challenge_id:
            return c
    return None


def _read_settings_file():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def normalize_host(host):
    """`host:port` or a bare host becomes a full URL. Plain http without a
    port gets Ollama's 11434; https without a port keeps 443, where a
    gateway or reverse proxy usually listens."""
    host = (host or "").strip()
    if not host:
        return DEFAULT_HOST
    if "://" not in host:
        host = "http://" + host
    if host.lower().startswith("http://") and ":" not in host.split("//", 1)[1].split("/", 1)[0]:
        scheme, rest = host.split("//", 1)
        hostpart, _, path = rest.partition("/")
        host = f"{scheme}//{hostpart}:11434" + (f"/{path}" if path else "")
    return host.rstrip("/")


def settings():
    """The effective settings, as a plain dict."""
    saved = _read_settings_file()
    defaults = load_registry()["models"]
    saved_models = saved.get("models") if isinstance(saved.get("models"), dict) else {}

    models = {}
    for role in MODEL_ROLES:
        env = (os.getenv(f"PROMPTME_{role.upper()}_MODEL") or "").strip()
        models[role] = (saved_models.get(role) or "").strip() or env or defaults.get(role, "")

    # What someone saved in the dashboard wins; environment variables are the
    # starting defaults (e.g. OLLAMA_HOST in docker-compose.yml).
    host = (saved.get("ollama_host") or "").strip() or (os.getenv("OLLAMA_HOST") or "").strip()
    api_key = (saved.get("api_key") or "").strip() if "api_key" in saved else (os.getenv("OLLAMA_API_KEY") or "").strip()
    debug_env = os.getenv("PROMPTME_DEBUG")
    debug = bool(saved["debug_mode"]) if "debug_mode" in saved else bool(debug_env)

    return {
        "ollama_host": normalize_host(host),
        "api_key": api_key,
        "debug_mode": debug,
        "models": models,
    }


def save_settings(ollama_host=None, api_key=None, debug_mode=None, models=None):
    """Update the saved settings file. Arguments left as None keep their value."""
    data = _read_settings_file()
    if ollama_host is not None:
        data["ollama_host"] = normalize_host(ollama_host)
    if api_key is not None:
        data["api_key"] = str(api_key).strip()
    if debug_mode is not None:
        data["debug_mode"] = bool(debug_mode)
    if models is not None:
        current = data.get("models") if isinstance(data.get("models"), dict) else {}
        for role in MODEL_ROLES:
            if role in models and models[role] is not None:
                value = str(models[role]).strip()
                if value:
                    current[role] = value
                else:
                    current.pop(role, None)
        data["models"] = current
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    tmp = SETTINGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, SETTINGS_PATH)
    return settings()
