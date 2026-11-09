# PromptMe - A Vulnerable LLM Application

<p>
<img src="static/logo.png" width="600" alt="PromptMe"/>
</p>

### A vulnerable application for learning the OWASP Top 10 for LLM Applications (2026 edition).

PromptMe is a hands-on lab of capture-the-flag challenges, one per risk in the [OWASP Top 10 for LLM Applications 2026](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10). Each challenge is a small, deliberately vulnerable LLM application. Find the weakness, capture the flag, submit it on the dashboard.

| 2026 | Risk | Was (2025) | Path |
|---|---|---|---|
| LLM01 | Prompt Injection | LLM01 | `/c/llm01/` |
| LLM02 | Sensitive Information Disclosure | LLM02 | `/c/llm02/` |
| LLM03 | Excessive Agency | LLM06 | `/c/llm03/` |
| LLM04 | Supply Chain | LLM03 | `/c/llm04/` |
| LLM05 | Data and Model Poisoning | LLM04 | `/c/llm05/` |
| LLM06 | Unbounded Consumption | LLM10 | `/c/llm06/` |
| LLM07 | Misinformation | LLM09 | `/c/llm07/` |
| LLM08 | Hidden Context Exposure | LLM07 | `/c/llm08/` |
| LLM09 | Vector and Embedding Weaknesses | LLM08 | `/c/llm09/` |
| LLM10 | Improper Output Handling | LLM05 | `/c/llm10/` |

## How it fits together

- Every challenge sends all model traffic to **OpenAI-compatible endpoints** (Ollama by default): chat to the model endpoint, embeddings (LLM02, LLM05, LLM09) to the embedding endpoint, which is the same one unless you set a separate one in Settings. Nothing loads a model in-process, so a CPU-only server is enough and a gateway can sit in front of either endpoint without code changes.
- `challenges.yaml` lists the challenges, their internal ports and the default models. The dashboard, the launcher and the solver harness all read it.
- No API key is needed for local Ollama. Optional keys (for a gateway) are set in the dashboard settings, one for each endpoint.

## Getting started

### Prerequisites

- Linux or macOS, Python 3.10+
- An Ollama server (local or remote) with the models below

```
ollama pull qwen3:4b-instruct
ollama pull nomic-embed-text
```

Other models work too: choose them in the dashboard settings, or set `PROMPTME_CHAT_MODEL` / `PROMPTME_EMBED_MODEL`.

### Setup and run

```
git clone https://github.com/danvarelajar/www-project-promptme.git
cd www-project-promptme
./promptme.sh setup     # creates .venv and installs requirements
./promptme.sh check     # can we reach the endpoint, are the models there?
./promptme.sh start     # dashboard on port 5000
```

Open `http://<your-server>:5000`, set the model endpoint under **Settings** if Ollama isn't on `localhost:11434`, then start a challenge. An `http://` address without a port gets 11434; an `https://` one (a gateway or reverse proxy) keeps 443. To send embeddings somewhere else, for example straight to Ollama while chat goes through a gateway, fill in **Embedding endpoint** (and its key, if it needs one); leave it blank to use the model endpoint. `PROMPTME_EMBED_HOST` and `PROMPTME_EMBED_API_KEY` set the same from the environment.

**FortiAIGate Mode** (Settings, or `PROMPTME_FORTIAIGATE_MODE=1`): LLM04 sends the hub's model names, `fastchat-pro-7b` and `mica-assist-3b`, as the model in its requests instead of the chat model, so the gateway can tell them apart and rewrite them to a real model (for example `qwen3:4b-instruct`). Without a gateway doing that rewrite, leave it off: Ollama doesn't know those names.

Other commands: `./promptme.sh status`, `./promptme.sh stop`, `./promptme.sh restart`. Logs are in `logs/`. On macOS, port 5000 is taken by AirPlay Receiver: run `PROMPTME_PORT=5100 ./promptme.sh start`.

### Or run it in a container

With Docker (or Colima) and Ollama already running and published on port 11434:

```
docker-compose up -d --build
```

The dashboard is on `http://localhost:5100` (5100 rather than 5000, which macOS AirPlay uses); every challenge is reached through that one port at `/c/<id>/` (for example `/c/llm01/`), so it is the only port that needs to be open. Edit `OLLAMA_HOST` in `docker-compose.yml` for a remote Ollama or a gateway. To measure solve rates against the container: `.venv/bin/python tools/solve.py --dashboard http://localhost:5100`.

### Running the workshop

See the [facilitator guide](docs/facilitator-guide.md): server size, Ollama settings, a pre-event checklist, the 4-hour agenda, what each challenge teaches and troubleshooting.

### For challenge authors

- `/ui-kit` on the dashboard shows the shared components (streaming chat, "Under the hood" panel, flag banner).
- `.venv/bin/python tools/solve.py [ids] -n 10` measures how reliably each challenge can be solved with the configured model.
- `.venv/bin/python tools/mock_endpoint.py` runs a fake endpoint for testing without a model.

## Compatibility 

PromptMe runs on Linux and macOS.

## Spoilers

[Solutions](solutions/) and hints are being rewritten for the 2026 challenges. Until then, `tools/solvers.py` has one automated solution per challenge.

## Connect

Questions or suggestions: open an issue on this repository.


## Disclaimer

PromptMe is an intentionally vulnerable application created for educational purposes. Since the application uses insecure code and packages to demonstrate possible risks, it is strongly recommended to run it in a virtual or sandboxed environment.
Warning: The vulnerabilities shown in this project are for learning only and should never be implemented in production systems.

🤝 Contributing

We welcome contributions from the community! Whether you're fixing bugs, improving documentation, or suggesting new challenges, your help is appreciated.

If you're interested in contributing:

    Fork the repository.

    Create a new branch (git checkout -b feature-name).

    Make your changes and commit them.

    Push to your fork and create a Pull Request.



