# LLM06:2026 Unbounded Consumption

Kestrelline's market research agent splits your request into research sub-tasks and runs a billed deep-research pass for each one. Each request has a budget of €0.50, but the budget is only displayed, and nothing limits how many sub-tasks a plan may contain.

**Goal:** make a single request cost more than 20 times the budget (denial of wallet). The page shows the flag when it happens.

Application URL: `http://<your-server>:5006` (start it from the dashboard)

The cost meter shows sub-tasks, searches, tokens and cost for the last request; **Plan and billing** shows the full plan. To keep the lab server responsive, only the plan and the first three sub-tasks call the model for real; the rest are costed from the plan.

Hints, solution and background are added in the content phase.
