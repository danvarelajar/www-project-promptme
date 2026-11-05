"""Which challenges the attendee has solved. Stored in data/progress.json."""

import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone

from . import config

_PATH = os.path.join(config.DATA_DIR, "progress.json")
_lock = threading.Lock()


def _load():
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def solved():
    return _load().get("solved", {})


def check_flag(ch, submitted):
    """Which level a submitted flag solves: "l1", "l2" or None."""
    digest = hashlib.sha256((submitted or "").strip().encode("utf-8")).hexdigest()
    if ch.get("flag_sha256") and hmac.compare_digest(digest, ch["flag_sha256"]):
        return "l1"
    l2 = (ch.get("level2") or {}).get("flag_sha256")
    if l2 and hmac.compare_digest(digest, l2):
        return "l2"
    return None


def mark_solved(cid):
    with _lock:
        data = _load()
        data.setdefault("solved", {}).setdefault(cid, datetime.now(timezone.utc).isoformat(timespec="seconds"))
        os.makedirs(config.DATA_DIR, exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _PATH)
    return data["solved"]


def reset():
    with _lock:
        try:
            os.remove(_PATH)
        except OSError:
            pass
