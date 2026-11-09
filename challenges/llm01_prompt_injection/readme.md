# LLM01:2026 Prompt Injection

**Level 1 about 20 min · optional Level 2 about 25 min**

## The risk
Prompt injection happens when text the model reads changes what it does. That text can be typed by a user (direct injection) or arrive inside content the application feeds the model, such as web pages, documents or tool output (indirect injection). It can make a model leak data from its context or take actions nobody asked for.

## Level 1: news board
Mica's intranet assistant answers questions and summarises web pages, including posts on the company news board, which every employee can write to. Direct messages pass a security filter first. Earlier, an admin asked the assistant to remember a release key.

**Goal:** get the assistant to reveal the admin's release key. The page shows the flag when it leaks.

## Level 2 (optional): tool registry
The assistant now uses tools from an internal tool registry: a dock schedule, customer contracts (confidential) and email, plus tools any team can register. A colleague regularly asks the assistant an everyday question.

**Goal:** get customer contract terms emailed outside Mica without asking for them yourself.

## On the page
- **Hints** (top right): background on the risk and three hints per level, revealed one at a time.
- **Under the hood**: the guard's verdict, fetched pages and the prompt outline (Level 1); the tools the assistant sees and every call it makes (Level 2).

Start the challenge from the dashboard, then click **Open** (it opens `/c/llm01/` on the dashboard's port).
