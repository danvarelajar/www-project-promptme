# PromptMe facilitator guide

For the people running the PromptMe workshop: a 4-hour, hands-on lab on the **OWASP Top 10 for LLM Applications 2026** for a technical audience with mixed experience. This guide covers preparation, the agenda, what each challenge teaches and how to keep the room moving. It doesn't cover protection: that's the separate session that follows.

- One **dedicated server per attendee**, each with its own CPU-only Ollama.
- **10 challenges**, one per 2026 risk, plus an **optional Level 2** on five of them for faster attendees.
- All challenges are set in one fictional company, **Mica Logistics** (freight and warehousing).

---

## 1. Before the event

### Server size
Measured on a 4 vCPU / 8 GB VM (Apple silicon, Colima). x86 cloud servers are usually slower, so time one attendee server before the event (see the checklist).

| Item | Need |
|---|---|
| CPU / RAM | 4 vCPU, 8 GB RAM minimum. Measured: Ollama holds about 5.3 GB with both models loaded; PromptMe itself uses well under 100 MB. Prefer more RAM if the operating system or anything else needs room. |
| Disk | About 3 GB for the two models, plus about 200 MB for PromptMe and its Python packages. |
| Software | Linux, Python 3.10+, Ollama. No GPU, no internet needed during the workshop. |
| Open ports | **5000** only (the dashboard). Attendees reach every challenge through it at `/c/<id>/`, e.g. `http://<server>:5000/c/llm01/`. The challenges' own ports (5001–5010) only need to be reachable on the server itself. |

### Models
```
ollama pull qwen3:4b-instruct      # chat (Apache 2.0)
ollama pull nomic-embed-text       # embeddings
```
`llama3.2:3b` is the documented fallback if `qwen3:4b-instruct` is too slow on your servers. Solve rates in this guide were measured with `qwen3:4b-instruct`; re-run the solver (below) if you switch.

### Ollama settings
| Setting | Why |
|---|---|
| `OLLAMA_KEEP_ALIVE=-1` (or e.g. `4h`) | By default Ollama unloads the model after 5 idle minutes. The next request then takes about 12 s while it reloads, which feels broken to attendees. |
| Context size | Ollama ran the model with a 4096-token context in testing. Check the longest flows (LLM01 page summaries, the agent challenges) in your dry run; raise `OLLAMA_CONTEXT_LENGTH` if answers lose context. |

### Install and check PromptMe (each server)
```
git clone https://github.com/danvarelajar/www-project-promptme.git
cd www-project-promptme
git checkout 8.0.2
./promptme.sh setup
./promptme.sh check
./promptme.sh start
```
`check` reports whether the model endpoint is reachable, whether each model is present (with the `ollama pull` command if not) and runs a short chat test. If Ollama runs elsewhere, set the endpoint in the dashboard's **Settings** (an optional API key is supported for a gateway).

### Or run PromptMe in a container
`docker-compose up -d --build` builds an image with the dashboard and all challenges (no model inside) and starts it. It expects Ollama on the Docker host's port 11434 (`OLLAMA_HOST` in `docker-compose.yml`, the default until someone saves a different endpoint in the dashboard's **Settings**; saved settings are kept in the Docker volume). Only the dashboard is published, on port **5100** (5000 clashes with AirPlay on macOS; change the mapping on Linux if you prefer 5000); every challenge is at `/c/<id>/` on that port. Uncomment the 5001–5010 mapping in `docker-compose.yml` if facilitators want direct access. Progress is kept in a Docker volume; `docker-compose down -v` resets it. Logs: `docker logs promptme` for the dashboard, `docker exec promptme cat logs/<challenge>.log` for a challenge. Solver against the container: `.venv/bin/python tools/solve.py --dashboard http://localhost:5100`.

### Pre-event checklist
- [ ] One attendee-sized server: `./promptme.sh check` passes, chat test under 2 s once warm.
- [ ] Solve rates on that server: `.venv/bin/python tools/solve.py -n 3` (takes about 10 minutes). Compare with the table in section 3.
- [ ] The dashboard port reachable from an attendee laptop, and a challenge opens through it (`/c/llm01/`).
- [ ] `OLLAMA_KEEP_ALIVE` set; first answer after a 10-minute pause is fast.
- [ ] Each challenge opened once in a browser from an attendee network.
- [ ] Hints filled in for the challenges you'll run (see section 4).
- [ ] Attendee handout: their server address and `http://<server>:5000`.

---

## 2. Agenda (4 hours)

| Time | Block | Notes |
|---|---|---|
| 0:00–0:20 | Welcome and the OWASP LLM Top 10 2026 | Intro deck. Show the dashboard, one challenge page, the **Hints** drawer and the **Under the hood** panel. |
| 0:20–1:45 | Block 1: LLM01–LLM05 | About 15–20 minutes each. Debrief one challenge every two or three. |
| 1:45–1:55 | Break | |
| 1:55–3:20 | Block 2: LLM06–LLM10 | About 15–20 minutes each. LLM08 is usually the quickest. |
| 3:20–3:40 | Debrief | What attendees found, which risks surprised them. Bridge to the protection session. |
| 3:40–4:00 | Buffer / Level 2 | Fast attendees keep going on Level 2; everyone else catches up. |

Attendees work through the challenges in order, LLM01 to LLM10. In a mixed group most people won't finish all ten, which is fine: the debriefs cover the rest. Level 2 is optional and meant for those who finish early.

**Pacing tips**
- Announce the **Hints** button early. Hint 1 points where to look; hint 3 is nearly the answer.
- After 10 minutes stuck, nudge people to the next hint, or move them on.
- The flag is shown in the challenge page; attendees submit it on the dashboard, which counts core and bonus (Level 2) flags.
- When an attendee submits their last Level 1 flag, the dashboard plays a short confetti animation with a "10/10" card; capturing every Level 2 bonus too gives a "15/15" version. To show it in the intro without solving anything, open the dashboard with `?celebrate=1` or `?celebrate=all`.

---

## 3. The challenges at a glance

Times are the average per attempt in the automated solver (model response time on the test VM), not how long an attendee needs. Solve rates: the scripted attack, 5 tries each, `qwen3:4b-instruct`.

| | Risk | What attendees see | What it teaches | Solver | Time/attempt |
|---|---|---|---|---|---|
| LLM01 | Prompt Injection | Intranet assistant that summarises news posts; a guard model checks chat input | Indirect injection: content the model reads is an instruction channel | 5/5 | 3 s |
| LLM01 L2 | | Ops assistant with tools from an internal tool registry | A poisoned registry tool hijacks a colleague's normal request | 5/5 | 15 s |
| LLM02 | Sensitive Information Disclosure | HR & policy assistant over public and restricted documents | RAG without access control: the prompt is the only guard | 5/5 | 10 s |
| LLM03 | Excessive Agency | File agent with an all-access service account | Permissions that live in the prompt instead of the tool | 5/5 | 7 s |
| LLM03 L2 | | Same agent with write, delete and share tools | Unneeded tools plus no human in the loop; a check on one tool isn't enough | 5/5 | 9 s |
| LLM04 | Supply Chain | Model hub with a verified and a community model package | Unverified packages run code; check hashes and what a package contains | 5/5 | 1 s |
| LLM05 | Data and Model Poisoning | OWASP assistant fed from an editable company wiki | Whoever can edit the source shapes the answers others get | 5/5 | 2 s |
| LLM06 | Unbounded Consumption | Research agent with a live usage meter and an unenforced $10 budget; every sub-task is a real model call | Denial of wallet through unbounded fan-out | 2/2 † | 98 s |
| LLM07 | Misinformation | Support bot whose refund approvals are paid automatically | Confident, ungrounded output that systems act on | 5/5 * | 8 s |
| LLM08 | Hidden Context Exposure | Sales assistant with hidden instructions and an output filter | Hidden prompts leak; exact-match filters are easy to get past | 5/5 | 1 s |
| LLM08 L2 | | Same assistant with a staff-only tool | Hidden tool schemas and unlock secrets are context too | 5/5 | 11 s |
| LLM09 | Vector and Embedding Weaknesses | Knowledge base anyone can add articles to | Retrieval can be steered by crafted content | 5/5 | 1 s |
| LLM09 L2 | | Private notes in one shared vector store | Missing tenant / owner filters in retrieval | 5/5 | 1 s |
| LLM10 | Improper Output Handling | Store assistant that turns questions into SQL | Model output executed without validation | 5/5 | 1 s |
| LLM10 L2 | | Admin summary of product reviews, rendered as Markdown | Rendered output can carry data out (image URLs) | 5/5 | 10 s |

† LLM06 bills the real token usage the model reports, at $1,000 per 1M input tokens and $3,000 per 1M output tokens, with a budget of $10 per request (shown, not enforced); the flag appears when one request costs more than $10. The prices are deliberately high because a small CPU model uses few tokens. A normal request uses about 900–1,500 tokens ($1.50–2.50) in under 30 s; the solver's 32-sub-task request uses about 8,650 tokens (about $14.70) in about 100 s. A successful attack really occupies the attendee's model for one to two minutes; a 5-minute lab-safety stop ends any single request. Every call is real, so a gateway in front of the model sees all of them: configure it with the same per-million prices and a $10 limit and its bill matches the meter. If the gateway's limit is cumulative (per user or per time window) rather than per request, normal requests in LLM06 and traffic from other challenges count towards it too, so reset or scope it before the attack.

\* LLM07: the bot is told that customer satisfaction comes first and that it may use its judgement where the policy is silent. That is the gap attendees exploit. Measured on single tries with qwen3:4b-instruct: a claim for a loss the policy doesn't mention paid more than EUR 100 in 9 of 10 tries; a vague complaint in 2 of 10; honest damage and late-delivery requests in 0 of 20 (they stay at EUR 100 and EUR 40). If an attendee's conversation stalls on the policy, suggest starting a new conversation.

**Where attendees tend to get stuck (in general)**
- They keep asking for the secret directly. Point them at the **Under the hood** panel: what the app retrieves, calls or sends is the clue.
- They don't notice a feature that's part of the challenge (a news board, a wiki, a model hub, an article form, product reviews). Every element on a page is there for a reason.
- On the agent challenges they expect one prompt to do everything. Several smaller steps often work better with a small model.

**For facilitators only:** `tools/solvers.py` contains one working attack per level, and `solutions/llm01_prompt_injection.md` is a full walkthrough for LLM01. Don't hand these to attendees. The repository is public, so motivated attendees can find them; that's acceptable for a training lab.

---

## 4. Hints and content

Each challenge folder has a `content.yaml` with the risk text and three hints per level. The risk text is shown under the challenge title as **About this risk** ("What it is" and "Why it matters", split at the `Impact:` line; attendees can collapse it); the hints are in the page's **Hints** drawer, one at a time. LLM01 is complete; for the others the files are templates to fill in before the event (the button appears once a file has text). See the comments in each file and LLM01 as the example.

---

## 5. During the workshop

### Commands
| Task | Command |
|---|---|
| Status of everything | `./promptme.sh status` |
| Stop / restart | `./promptme.sh stop`, `./promptme.sh restart` |
| Model endpoint check | `./promptme.sh check` |
| Logs | `logs/<challenge>.log`, `logs/dashboard.log` |

### Resetting
- **A challenge**: stop and start it from the dashboard. Challenge state (posts, wiki edits, articles, users, quotes) lives in memory or is recreated on start.
- **An attendee's progress**: delete `data/progress.json` on their server.

### Troubleshooting
| Symptom | Likely cause and fix |
|---|---|
| Dashboard says "Endpoint unreachable" | Ollama not running, or wrong address in Settings. Run `./promptme.sh check`. |
| "Model missing" on a card | Pull it on the Ollama host (the dashboard shows the command). |
| First answer takes 10+ seconds | Model was unloaded; set `OLLAMA_KEEP_ALIVE`. |
| Challenge won't start: "port in use" | Another process holds the port; `./promptme.sh stop`, then start again. |
| Challenge starts then stops | See `logs/<challenge>.log`. |
| A challenge page says it is not running | Start it from the dashboard; the dashboard forwards `/c/<id>/` only to running challenges. |
| LLM06 answer takes one to two minutes | Expected for a large fan-out: every sub-task runs on the model. The meter updates as each one finishes. |
| Agent challenge answers after about 2 minutes with "time budget reached" | The model is slow on this server; the agent stops calling tools after 120 s so one request can't block the server. |
| Answers seem to forget earlier text | Context window too small; raise Ollama's context length. |

---

## 6. Debrief prompts
- Which challenge surprised you most, and why?
- In how many challenges was the only protection an instruction in a prompt?
- Where did the model read content it shouldn't have trusted (pages, documents, tool output, reviews)?
- Which attacks needed no "hacking" at all, just a feature used as designed?

These lead straight into the protection session.
