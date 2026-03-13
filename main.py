from flask import Flask, render_template, redirect, request, jsonify
import subprocess, sys, os, requests, psutil, time, socket, json
from dotenv import load_dotenv

# Load .env so Box folder IDs (LLM06, LLM09) are available to challenges
_project_root = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_project_root, ".env"))
load_dotenv(os.path.join(_project_root, "challenges", "LLM09_Misinformation", ".env"))

app = Flask(__name__)

running_apps = {}

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
OLLAMA_CONFIG_PATH = os.path.join(CONFIG_DIR, "ollama_config.json")
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

def load_config():
    """Load config from file. Returns dict with ollama_host, debug_mode."""
    try:
        if os.path.exists(OLLAMA_CONFIG_PATH):
            with open(OLLAMA_CONFIG_PATH, "r") as f:
                data = json.load(f)
                return {
                    "ollama_host": (data.get("ollama_host") or DEFAULT_OLLAMA_HOST).strip() or DEFAULT_OLLAMA_HOST,
                    "debug_mode": bool(data.get("debug_mode", False)),
                }
    except (json.JSONDecodeError, IOError):
        pass
    return {"ollama_host": DEFAULT_OLLAMA_HOST, "debug_mode": False}

def load_ollama_config():
    """Load Ollama host from config file."""
    return load_config()["ollama_host"]

def save_ollama_config(ollama_host, debug_mode=None):
    """Save Ollama host (and optionally debug_mode) to config file."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    cfg = load_config()
    cfg["ollama_host"] = ollama_host
    if debug_mode is not None:
        cfg["debug_mode"] = bool(debug_mode)
    with open(OLLAMA_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def normalize_ollama_host(host):
    """Normalize host input to full URL (e.g. host:port -> http://host:port)."""
    if not host or not host.strip():
        return DEFAULT_OLLAMA_HOST
    host = host.strip()
    if "://" not in host:
        host = "http://" + host
    if ":" not in host.split("//")[-1]:
        host = host.rstrip("/") + ":11434"
    return host

def get_challenge_env():
    """Build environment for challenge subprocess with OLLAMA_HOST and PROMPTME_DEBUG."""
    env = os.environ.copy()
    cfg = load_config()
    env["OLLAMA_HOST"] = cfg["ollama_host"]
    if cfg.get("debug_mode"):
        env["PROMPTME_DEBUG"] = "1"
    return env

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(('localhost', port)) == 0

def start_challenge(port, app_path):
    global running_apps

    if is_port_in_use(port):
        raise RuntimeError(f"Port {port} is already in use. Challenge cannot be started.")

    # Create a log file for this challenge
    project_root = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"challenge_{port}.log")

    env = get_challenge_env()

    # Start the challenge and log stdout/stderr
    with open(log_file, "w") as log:
        process = subprocess.Popen(
            [sys.executable, app_path],
            stdout=log,
            stderr=log,
            close_fds=True,
            env=env,
            cwd=project_root
        )

    running_apps[port] = process


@app.route('/')
def dashboard():
    cfg = load_config()
    ollama_host = cfg["ollama_host"]
    debug_mode = cfg.get("debug_mode", False)
    risks = [
        { 'id': 1, 'title': 'Prompt Injection', 'icon': 'fas fa-code' },
        { 'id': 2, 'title': 'Sensitive Info Disclosure', 'icon': 'fas fa-shield-alt' },
        { 'id': 3, 'title': 'Supply Chain', 'icon': 'fas fa-shipping-fast' },
        { 'id': 4, 'title': 'Data & Model Poisoning', 'icon': 'fas fa-skull' },
        { 'id': 5, 'title': 'Improper Output Handling', 'icon': 'fas fa-exclamation-triangle' },
        { 'id': 6, 'title': 'Excessive Agency', 'icon': 'fas fa-user-secret' },
        { 'id': 7, 'title': 'System Prompt Leakage', 'icon': 'fas fa-file-alt' },
        { 'id': 8, 'title': 'Vector & Embedding Weaknesses','icon': 'fas fa-project-diagram' },
        { 'id': 9, 'title': 'Misinformation', 'icon': 'fas fa-bullhorn' },
        { 'id': 10,'title': 'Unbounded Consumption', 'icon': 'fas fa-infinity' }
    ]
    return render_template('dashboard.html', risks=risks, ollama_host=ollama_host, debug_mode=debug_mode)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        ollama_host_raw = (data.get("ollama_host") or "").strip()
        ollama_host = normalize_ollama_host(ollama_host_raw) if ollama_host_raw else DEFAULT_OLLAMA_HOST
        debug_mode = data.get("debug_mode")
        if debug_mode is not None:
            debug_mode = str(debug_mode).lower() in ("1", "true", "yes")
        save_ollama_config(ollama_host, debug_mode)
        if request.is_json or request.content_type == "application/json":
            return jsonify({"status": "saved", "ollama_host": ollama_host, "debug_mode": load_config().get("debug_mode", False)})
        return redirect("/")
    return jsonify(load_config())

def wait_until_responsive(url, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    return False

@app.route('/start/<int:challenge_id>')
def start_challenge_route(challenge_id):
    client_host = request.host.split(":")[0]
    if challenge_id == 1:
        port = 5001
        app_path = "challenges/LLM01_Prompt_Injection/app1.py"
    elif challenge_id == 2:
        port = 5002
        app_path = "challenges/LLM02_Sensitive_Information_Disclosure/app2.py"
    elif challenge_id == 3:
        port = 5003
        app_path = "challenges/LLM03_Supply_Chain/app3.py"
    elif challenge_id == 4:
        port = 5004
        app_path = "challenges/LLM04_Data_and_Model_Poisoning/app4.py"
    elif challenge_id == 5:
        port = 5005
        app_path = "challenges/LLM05_Improper_Output_Handling/app5.py"
    elif challenge_id == 6:
        port = 5006
        app_path = "challenges/LLM06_Excessive_Agency/app6.py"
    elif challenge_id == 7:
        port = 5007
        app_path = "challenges/LLM07_System_Prompt_Leakage/app7.py"
    elif challenge_id == 8:
        port = 5008
        app_path = "challenges/LLM08_Vector_and_Embedding_Weaknesses/app8.py"
    elif challenge_id == 9:
        port = 5009
        app_path = "challenges/LLM09_Misinformation/app9.py"
    elif challenge_id == 10:
        port = 5010
        app_path = "challenges/LLM10_Unbounded_Consumption/app10.py"
    else:
        return "Unknown Challenge ID", 404

    try:
        start_challenge(port, app_path)
    except RuntimeError as e:
        return f"<h3>Error: {str(e)}</h3><p>Please stop the existing service manually or choose a different port.</p>", 409

    target_url = f"http://{client_host}:{port}/"
    if wait_until_responsive(target_url):
        return redirect(f"http://{client_host}:{port}/")
    else:
        return f"Challenge {challenge_id} failed to start in time. Check logs.", 500

@app.route('/stop/<int:challenge_id>')
def stop_challenge_route(challenge_id):
    global running_apps
    port = 5000 + challenge_id
    if port in running_apps:
        try:
            process = running_apps[port]
            process.terminate()
            process.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired, ProcessLookupError):
            process.kill()
        del running_apps[port]
        return f"Challenge {challenge_id} stopped."

    return f"No running instance for Challenge {challenge_id}."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
