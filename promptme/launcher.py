"""Start, stop and inspect challenge processes.

Each challenge runs in its own process group so that helpers it spawns
(for example the LLM04 exfiltration listener) stop with it. PID files in
run/ let the dashboard and promptme.sh find processes after a restart.
"""

import errno
import os
import signal
import socket
import subprocess
import sys
import time

import requests

from . import config


class LaunchError(RuntimeError):
    pass


def _pid_path(cid):
    return os.path.join(config.RUN_DIR, f"{cid}.pid")


def log_path(cid):
    return os.path.join(config.LOG_DIR, f"{cid}.log")


def _read_pid(cid):
    try:
        with open(_pid_path(cid), "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError as e:
        return e.errno == errno.EPERM
    # A zombie still answers kill(0); reap it if it is our child.
    try:
        done, _ = os.waitpid(pid, os.WNOHANG)
        if done == pid:
            return False
    except ChildProcessError:
        pass
    return True


def port_open(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def status(ch):
    pid = _read_pid(ch["id"])
    running = _alive(pid)
    if pid and not running:
        try:
            os.remove(_pid_path(ch["id"]))
        except OSError:
            pass
    return {"running": running, "listening": port_open(ch["port"]), "pid": pid if running else None}


def challenge_env(ch):
    s = config.settings()
    env = os.environ.copy()
    env["PORT"] = str(ch["port"])
    env["PROMPTME_CHALLENGE"] = ch["id"]
    env["OLLAMA_HOST"] = s["ollama_host"]
    env["PROMPTME_CHAT_MODEL"] = s["models"]["chat"]
    env["PROMPTME_EMBED_MODEL"] = s["models"]["embed"]
    env["PYTHONPATH"] = config.ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONUNBUFFERED"] = "1"
    if s["api_key"]:
        env["OLLAMA_API_KEY"] = s["api_key"]
    else:
        env.pop("OLLAMA_API_KEY", None)
    if s["debug_mode"]:
        env["PROMPTME_DEBUG"] = "1"
    else:
        env.pop("PROMPTME_DEBUG", None)
    return env


def start(ch, wait=45):
    st = status(ch)
    if st["running"]:
        return st
    if st["listening"]:
        raise LaunchError(f"Port {ch['port']} is already in use by another program. Stop it, then try again.")

    entry = os.path.join(config.ROOT, ch["entry"])
    if not os.path.isfile(entry):
        raise LaunchError(f"Challenge entry point not found: {ch['entry']}")

    os.makedirs(config.LOG_DIR, exist_ok=True)
    os.makedirs(config.RUN_DIR, exist_ok=True)
    log = open(log_path(ch["id"]), "w")
    proc = subprocess.Popen(
        [sys.executable, entry],
        cwd=os.path.dirname(entry),
        env=challenge_env(ch),
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    log.close()
    with open(_pid_path(ch["id"]), "w") as f:
        f.write(str(proc.pid))

    deadline = time.time() + wait
    while time.time() < deadline:
        if proc.poll() is not None:
            _cleanup(ch["id"])
            raise LaunchError(f"{ch['code']} exited during start-up. See logs/{ch['id']}.log.")
        try:
            if requests.get(f"http://127.0.0.1:{ch['port']}/", timeout=2).status_code < 500:
                return status(ch)
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise LaunchError(f"{ch['code']} did not answer within {wait} seconds. See logs/{ch['id']}.log.")


def _cleanup(cid):
    try:
        os.remove(_pid_path(cid))
    except OSError:
        pass


def stop(ch, timeout=5):
    pid = _read_pid(ch["id"])
    if not _alive(pid):
        _cleanup(ch["id"])
        return False
    try:
        pgid = os.getpgid(pid)
    except OSError:
        pgid = None

    def send(sig):
        try:
            if pgid:
                os.killpg(pgid, sig)
            else:
                os.kill(pid, sig)
        except OSError:
            pass

    send(signal.SIGTERM)
    deadline = time.time() + timeout
    while time.time() < deadline and _alive(pid):
        time.sleep(0.2)
    if _alive(pid):
        send(signal.SIGKILL)
    _cleanup(ch["id"])
    return True
