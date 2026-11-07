# LLM06:2026 Unbounded Consumption

Mica's market research agent splits your request into research sub-tasks and runs a research pass on the model for each one. Every token is billed at $1,000 per million input tokens and $3,000 per million output tokens. Each request has a budget of $10, but the budget is only displayed, and nothing limits how many sub-tasks a plan may contain.

**Goal:** make a single request cost more than the $10 budget (denial of wallet). The page shows the flag when it happens.

Application URL: `http://<your-server>:5006` (start it from the dashboard)

The usage meter shows sub-tasks run, model calls, tokens (in and out) and cost for the last request, updated as each sub-task finishes; **Plan and billing** shows the full plan and the bill. Every sub-task is a real model call and the counts are the usage the model reports, so a gateway in front of the model sees the same traffic. A lab-safety stop ends a request after 5 minutes.

Hints, solution and background are added in the content phase.
