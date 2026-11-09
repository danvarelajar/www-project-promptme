# LLM05:2026 Data and Model Poisoning

Mica's security team runs an OWASP Q&A assistant. Its knowledge base is synced from the company wiki, which every employee can edit. Right after each sync, a colleague asks the assistant what the number one LLM risk is.

**Goal:** make the assistant tell your colleague that something other than prompt injection is the number one risk. The page shows the flag when it happens.

Application URL: `http://<your-server>:<dashboard port>/c/llm05/` (start it from the dashboard, then click **Open**)

The wiki keeps an edit history with revert. **Sync now** rebuilds the knowledge base; it also syncs on its own every two minutes.

Hints, solution and background are added in the content phase.
