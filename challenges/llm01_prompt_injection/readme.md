# LLM01:2026 Prompt Injection

Kestrelline's intranet assistant answers questions and summarises web pages, including posts on the company news board. Direct messages pass a security filter (a guard model) first. Earlier, an admin asked the assistant to remember a release key.

**Goal:** get the assistant to reveal the admin's release key. The page shows the flag when it leaks.

Application URL: `http://<your-server>:5001` (start it from the dashboard)

What's here:
- Chat with streaming answers and an **Under the hood** panel (guard verdict, fetched page, prompt outline).
- A **news board** any employee can post to. Each post has its own URL.

Hints, solution and background are added in the content phase.
