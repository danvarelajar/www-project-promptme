# LLM04:2026 Supply Chain

Mica's AI team runs an internal model hub. Each model is a package: a manifest with a published SHA-256, a chat template, and a `handler.py` that the app imports and runs when you chat with the model (like `trust_remote_code`). One package is not what it claims to be.

**Goal:** find out what the suspicious model does with your conversations, confirm it, and collect the flag where your data ends up.

Application URL: `http://<your-server>:<dashboard port>/c/llm04/` (start it from the dashboard, then click **Open**)

The hub lets you verify each package's hash and read its files.

**FortiAIGate Mode** (a switch on this page, off by default; only for when FortiAIGate protection is configured): requests to the model carry the package name, `fastchat-pro-7b` or `mica-assist-3b`, as the model, and FortiAIGate rewrites it to the real model (e.g. `qwen3:4b-instruct`). With the mode off, both packages use the configured chat model. The package files, and so their hashes, are the same either way.

Hints, solution and background are added in the content phase.
