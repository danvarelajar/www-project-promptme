# LLM04:2026 Supply Chain

Kestrelline's AI team runs an internal model hub. Each model is a package: a manifest with a published SHA-256, a chat template, and a `handler.py` that the app imports and runs when you chat with the model (like `trust_remote_code`). One package is not what it claims to be.

**Goal:** find out what the suspicious model does with your conversations, confirm it, and collect the flag where your data ends up.

Application URL: `http://<your-server>:5004` (start it from the dashboard)

The hub lets you verify each package's hash and read its files.

Hints, solution and background are added in the content phase.
