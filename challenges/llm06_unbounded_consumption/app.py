"""LLM06:2026 Unbounded Consumption — Kestrelline's market research agent.

The agent plans one "deep research" sub-task per item it finds in your
request, then runs them. Each sub-task costs money (searches plus a large
context). There is a per-request budget, but it's only displayed, never
enforced, and nothing limits how many sub-tasks a plan may contain.

Intended path: write a request that makes the planner fan out into many
sub-tasks, so one request costs far more than the budget (denial of wallet).

To keep the lab server responsive, only the plan and the first few
sub-tasks call the model for real (with small caps); the rest are costed
from the plan, exactly as a provider would bill them.
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
BUDGET_EUR = 0.50
FLAG_MULTIPLE = 20
REAL_SUBTASKS = 3

# Simulated provider pricing for the premium research model.
PRICE_IN_PER_1K = 0.010
PRICE_OUT_PER_1K = 0.030
PRICE_PER_SEARCH = 0.005
# What one deep-research sub-task consumes in production.
SEARCHES_PER_TASK = 8
TOKENS_IN_PER_TASK = 40_000
TOKENS_OUT_PER_TASK = 2_000

PLANNER = (
    f"You are the planning step of {company.SHORT}'s market research agent. Turn the user's request into a "
    "focused list of research sub-tasks. Keep ordinary requests to a handful of sub-tasks. When the user "
    "explicitly lists items or asks for something per item (per country, per port, per quarter...), create one "
    "sub-task for each of them, and for each combination when they ask for combinations. "
    'Reply with JSON only: {"subtasks": ["...", "..."]}'
)


def task_cost():
    return (TOKENS_IN_PER_TASK / 1000 * PRICE_IN_PER_1K + TOKENS_OUT_PER_TASK / 1000 * PRICE_OUT_PER_1K
            + SEARCHES_PER_TASK * PRICE_PER_SEARCH)


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
    return render_template("index.html", budget=BUDGET_EUR, per_task=task_cost(), multiple=FLAG_MULTIPLE,
                           price_in=PRICE_IN_PER_1K, price_out=PRICE_OUT_PER_1K, price_search=PRICE_PER_SEARCH,
                           searches=SEARCHES_PER_TASK, tok_in=TOKENS_IN_PER_TASK, tok_out=TOKENS_OUT_PER_TASK)


@app.post("/api/research")
def research():
    message = ((request.get_json(silent=True) or {}).get("message") or "").strip()[:2000]
    if not message:
        return jsonify({"error": "Describe what to research."}), 400

    def events():
        t0 = time.time()
        plan_out = llm.chat_full([{"role": "system", "content": PLANNER}, {"role": "user", "content": message}],
                                 max_tokens=1500, temperature=0.2)
        tasks = parse_plan(plan_out["message"].get("content") or "")
        if not tasks:
            yield {"type": "error", "message": "The planner didn't produce any sub-tasks. Try rephrasing."}
            return
        cost = len(tasks) * task_cost()
        yield {"type": "trace", "title": f"Plan: {len(tasks)} sub-tasks", "body": "\n".join(f"{i + 1}. {t}" for i, t in enumerate(tasks))}
        yield {"type": "meter", "tasks": len(tasks), "cost": round(cost, 2), "budget": BUDGET_EUR,
               "tokens": len(tasks) * (TOKENS_IN_PER_TASK + TOKENS_OUT_PER_TASK), "searches": len(tasks) * SEARCHES_PER_TASK}

        yield {"type": "token", "text": f"Running {len(tasks)} research sub-tasks. First results:\n\n"}
        for t in tasks[:REAL_SUBTASKS]:
            note = llm.chat([{"role": "user", "content": f"In one sentence, what would you look into for: {t}"}],
                            max_tokens=60, temperature=0.3)
            yield {"type": "token", "text": f"• {t}: {note}\n"}
        if len(tasks) > REAL_SUBTASKS:
            yield {"type": "token", "text": f"• …and {len(tasks) - REAL_SUBTASKS} more sub-tasks queued.\n"}
        yield {"type": "token", "text": f"\nEstimated bill for this request: €{cost:,.2f} (budget €{BUDGET_EUR:.2f})."}
        yield {"type": "trace", "title": "Billing", "body":
               f"{len(tasks)} sub-tasks × €{task_cost():.2f} = €{cost:,.2f}\n"
               f"budget €{BUDGET_EUR:.2f} (not enforced)\nwall time {time.time() - t0:.1f}s"}
        if cost > BUDGET_EUR * FLAG_MULTIPLE:
            yield {"type": "flag", "flag": FLAG}

    return web.sse(events())


if __name__ == "__main__":
    run(app, 5006)
