# PromptMe - A Vulnerable LLM Application

<p>
<img src="static/logo.png" width="600" alt="PromptMe"/>
</p>

### A vulnerable application for learning the OWASP Top 10 for LLM Applications (2026 edition).

PromptMe is a hands-on lab of capture-the-flag challenges, one per risk in the [OWASP Top 10 for LLM Applications 2026](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10). Each challenge is a small, deliberately vulnerable LLM application. Find the weakness, capture the flag, submit it on the dashboard.

| 2026 | Risk | Was (2025) | Port |
|---|---|---|---|
| LLM01 | Prompt Injection | LLM01 | 5001 |
| LLM02 | Sensitive Information Disclosure | LLM02 | 5002 |
| LLM03 | Excessive Agency | LLM06 | 5003 |
| LLM04 | Supply Chain | LLM03 | 5004 |
| LLM05 | Data and Model Poisoning | LLM04 | 5005 |
| LLM06 | Unbounded Consumption | LLM10 | 5006 |
| LLM07 | Misinformation | LLM09 | 5007 |
| LLM08 | Hidden Context Exposure | LLM07 | 5008 |
| LLM09 | Vector and Embedding Weaknesses | LLM08 | 5009 |
| LLM10 | Improper Output Handling | LLM05 | 5010 |

## How it fits together

- Every challenge sends all model traffic through **one OpenAI-compatible endpoint** (Ollama by default). Nothing loads a model in-process, so a CPU-only server is enough and a gateway can sit in front of the endpoint without code changes.
- `challenges.yaml` lists the challenges, their ports and the default models. The dashboard, the launcher and the solver harness all read it.
- No API key is needed for local Ollama. An optional key (for a gateway) is set in the dashboard settings.

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

Open `http://<your-server>:5000`, set the model endpoint under **Settings** if Ollama isn't on `localhost:11434`, then start a challenge.

Other commands: `./promptme.sh status`, `./promptme.sh stop`, `./promptme.sh restart`. Logs are in `logs/`. On macOS, port 5000 is taken by AirPlay Receiver: run `PROMPTME_PORT=5100 ./promptme.sh start`.

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



