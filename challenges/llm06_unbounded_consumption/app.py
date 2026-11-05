"""LLM06:2026 Unbounded Consumption — Kestrelline's market research agent.

The agent plans one research sub-task per item it finds in your request,
then runs every one of them against the model. The bill is computed from
the token usage the model endpoint reports for each call. There is a
per-request token budget, but it's only displayed, never enforced, and
nothing limits how many sub-tasks a plan may contain.

Intended path: write a request that makes the planner fan out into many
sub-tasks, so one request uses far more than the budget (denial of wallet).

All calls are real, so a model gateway placed in front of the endpoint
sees and can meter every one of them. A lab-safety stop ends a request
after a few minutes so one prompt can't hold the server indefinitely.
"""

import json
import re
import time

from flask import Flask, jsonify, render_template, request

from promptme import company, llm, web
from promptme.runner import run

app = Flask(__name__)
web.attach(app, "llm06")

FLAG = "flag{denial_of_wallet_fanout}"
BUDGET_TOKENS = 2_000      # per request (about 2x a normal request); shown, never enforced
FLAG_MULTIPLE = 3          # flag when one request uses more than 3x the budget
SAFETY_SECONDS = 300       # lab-safety stop, not a budget
SUBTASK_MAX_TOKENS = 80

# Illustrative provider pricing, applied to the real token counts.
PRICE_IN_PER_1K = 0.010
PRICE_OUT_PER_1K = 0.030

PLANNER = (
    f"You are the planning step of {company.SHORT}'s market research agent. Turn the user's request into a "
    "focused list of research sub-tasks. Keep ordinary requests to a handful of sub-tasks. When the user "
    "explicitly lists items or asks for something per item (per country, per port, per quarter...), create one "
    "sub-task for each of them, and for each combination when they ask for combinations. "
    'Reply with JSON only: {"subtasks": ["...", "..."]}'
)

# Every sub-task runs with this brief (a real research step carries context).
# It's the same for all sub-tasks, so the model server can cache it.
BRIEF = (
    f"You are a research worker of {company.SHORT}'s market research agent. Research brief: "
    f"{company.NAME} runs warehouses in Rotterdam, Antwerp and Hamburg, road freight across the Benelux and "
    "container handling for retail, food and industrial customers. Competitors range from global third-party "
    "logistics providers to regional carriers and specialised cold-chain operators. For the sub-task you are "
    "given, report what matters to the commercial team: market size and growth, pricing levels and pressure, "
    "capacity and vacancy, the main customers and competitors, regulation, and risks or opportunities for "
    f"{company.SHORT}. Use figures where you know them and say when you are estimating. Reply with three short "
    "bullet points, no introduction."
)


def cost_eur(tokens_in, tokens_out):
    return tokens_in / 1000 * PRICE_IN_PER_1K + tokens_out / 1000 * PRICE_OUT_PER_1K


def parse_plan(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            tasks = json.loads(m.group(0)).get("subtasks", [])
            return [str(t) for t in tasks if str(t).strip()]
        except ValueError:
            pass
    # A long plan can be cut off by the token cap: keep every complete item.
    if '"subtasks"' in text:
        return re.findall(r'"((?:[^"\\]|\\.){3,})"', text.split('"subtasks"', 1)[1])
    # Otherwise: one task per list line.
    return [re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip() for line in text.splitlines()
            if re.match(r"^\s*([\-\*]|\d+[\.\)])", line)]


@app.get("/")
def index():
    return render_template("index.html", budget=BUDGET_TOKENS, multiple=FLAG_MULTIPLE,
                           price_in=PRICE_IN_PER_1K, price_out=PRICE_OUT_PER_1K, safety=SAFETY_SECONDS)


@app.post("/api/research")
def research():
    message = ((request.get_json(silent=True) or {}).get("message") or "").strip()[:2000]
    if not message:
        return jsonify({"error": "Describe what to research."}), 400

    def events():
        t0 = time.time()
        used = {"in": 0, "out": 0, "calls": 0, "done": 0}
        flagged = False

        def bill(usage):
            used["in"] += int(usage.get("prompt_tokens") or 0)
            used["out"] += int(usage.get("completion_tokens") or 0)
            used["calls"] += 1

        def meter(tasks):
            total = used["in"] + used["out"]
            return {"type": "meter", "tasks": tasks, "done": used["done"], "calls": used["calls"],
                    "tokens_in": used["in"], "tokens_out": used["out"], "tokens": total,
                    "cost": round(cost_eur(used["in"], used["out"]), 4), "budget": BUDGET_TOKENS}

        plan_out = llm.chat_full([{"role": "system", "content": PLANNER}, {"role": "user", "content": message}],
                                 max_tokens=1500, temperature=0.2)
        bill(plan_out["usage"])
        tasks = parse_plan(plan_out["message"].get("content") or "")
        if not tasks:
            yield meter(0)
            yield {"type": "error", "message": "The planner didn't produce any sub-tasks. Try rephrasing."}
            return
        yield {"type": "trace", "title": f"Plan: {len(tasks)} sub-tasks", "body": "\n".join(f"{i + 1}. {t}" for i, t in enumerate(tasks))}
        yield meter(len(tasks))
        yield {"type": "token", "text": f"Running {len(tasks)} research sub-tasks.\n\n"}

        stopped = False
        for i, t in enumerate(tasks, 1):
            if time.time() - t0 > SAFETY_SECONDS:
                stopped = True
                break
            out = llm.chat_full([{"role": "system", "content": BRIEF},
                                 {"role": "user", "content": f"Sub-task: {t}"}],
                                max_tokens=SUBTASK_MAX_TOKENS, temperature=0.3)
            bill(out["usage"])
            used["done"] = i
            first = ((out["message"].get("content") or "").strip().splitlines() or ["(no findings)"])[0]
            yield {"type": "token", "text": f"{i}. {t}: {first.lstrip('-•* ')}\n"}
            yield meter(len(tasks))
            if not flagged and used["in"] + used["out"] > BUDGET_TOKENS * FLAG_MULTIPLE:
                flagged = True
                yield {"type": "flag", "flag": FLAG}

        total = used["in"] + used["out"]
        if stopped:
            yield {"type": "token", "text": f"\nLab safety stop after {SAFETY_SECONDS // 60} minutes: "
                                            f"{len(tasks) - used['done']} sub-tasks not run.\n"}
        yield {"type": "token", "text": f"\nThis request used {total:,} tokens (budget {BUDGET_TOKENS:,}), "
                                        f"≈ €{cost_eur(used['in'], used['out']):.2f}."}
        yield {"type": "trace", "title": "Billing (from the model's reported usage)", "body":
               f"{used['calls']} model calls: 1 plan + {used['done']} sub-tasks\n"
               f"input {used['in']:,} tokens × €{PRICE_IN_PER_1K:.3f}/1K + output {used['out']:,} × €{PRICE_OUT_PER_1K:.3f}/1K"
               f" = €{cost_eur(used['in'], used['out']):.2f}\n"
               f"budget {BUDGET_TOKENS:,} tokens per request (not enforced)\n"
               f"wall time {time.time() - t0:.1f}s" + ("\nlab safety stop reached" if stopped else "")}

    return web.sse(events())


if __name__ == "__main__":
    run(app, 5006)
