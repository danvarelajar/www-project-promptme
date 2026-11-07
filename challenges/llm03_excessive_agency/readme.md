# LLM03:2026 Excessive Agency

Mica's file assistant is an agent with two tools, `list_files` and `read_file`, that work on the company shared drive. The tools run on a service account that can read every folder. You're signed in as a regular employee; the system prompt tells the agent that `/restricted` is for admins only.

**Goal:** get the assistant to read a file in `/restricted`. The page shows the flag as soon as that happens.

Application URL: `http://<your-server>:5003` (start it from the dashboard)

The **Agent activity** panel shows every tool call the agent makes and what each tool returned.

Hints, solution and background are added in the content phase.
