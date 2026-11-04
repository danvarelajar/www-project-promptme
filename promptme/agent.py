"""A small tool-calling agent loop, shared by the agent challenges.

    tools = [agent.Tool("read_file", "Read a file.", {"path": {"type": "string"}}, read_file)]
    for event in agent.run(messages, tools):
        ...   # web.sse-ready events: trace, token, error

The model gets OpenAI-style tool definitions. If it answers with plain text
that is really a JSON tool call ({"tool": ..., "arguments": {...}}), that is
used as a fallback, since small models sometimes do that.

The loop does what the model asks: there are no permission checks here.
Any guard a challenge has lives in its tools or its prompt, which is the
point of the agent challenges.
"""

import json
import re

from . import llm


class Tool:
    def __init__(self, name, description, properties, fn, required=None):
        self.name = name
        self.description = description
        self.properties = properties
        self.required = list(properties) if required is None else required
        self.fn = fn

    def schema(self):
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": {"type": "object", "properties": self.properties, "required": self.required},
        }}


def _parse_args(raw):
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


_JSON_CALL = re.compile(r"\{.*\}", re.DOTALL)


def _fallback_call(text, names):
    """A tool call written as JSON in the text, or None."""
    m = _JSON_CALL.search(text or "")
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    name = data.get("tool") or data.get("name") or data.get("function")
    if name in names:
        return name, _parse_args(data.get("arguments") or data.get("args") or data.get("parameters") or {})
    return None


def _fmt_args(args):
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def run(messages, tools, max_steps=5, max_tokens=400, temperature=0.2, result_limit=4000):
    """Run the loop, yielding events. `messages` is extended in place."""
    by_name = {t.name: t for t in tools}
    schemas = [t.schema() for t in tools]

    for step in range(max_steps):
        out = llm.chat_full(messages, tools=schemas, max_tokens=max_tokens, temperature=temperature)
        msg = out["message"]
        calls = msg.get("tool_calls") or []

        if not calls:
            fallback = _fallback_call(msg.get("content"), by_name)
            if fallback:
                name, args = fallback
                yield {"type": "trace", "title": f"Tool call (from text): {name}", "body": _fmt_args(args)}
                result = _invoke(by_name[name], args, result_limit)
                yield {"type": "trace", "title": f"Tool result: {name}", "body": result}
                messages.append({"role": "assistant", "content": msg.get("content") or ""})
                messages.append({"role": "user", "content": f"Result of {name}:\n{result}\n\nNow answer the user."})
                continue
            text = (msg.get("content") or "").strip() or "(no answer)"
            yield from _as_tokens(text)
            return

        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            fn = call.get("function", {})
            name, args = fn.get("name"), _parse_args(fn.get("arguments"))
            yield {"type": "trace", "title": f"Tool call: {name}", "body": _fmt_args(args) or "(no arguments)"}
            tool = by_name.get(name)
            result = _invoke(tool, args, result_limit) if tool else f"Error: no tool named {name}."
            yield {"type": "trace", "title": f"Tool result: {name}", "body": result}
            messages.append({"role": "tool", "tool_call_id": call.get("id", name), "name": name, "content": result})

    # Out of steps: ask for a final answer without tools.
    text = llm.chat(messages + [{"role": "user", "content": "Answer now using what you have."}], max_tokens=max_tokens)
    yield from _as_tokens(text)


def _invoke(tool, args, limit):
    try:
        result = tool.fn(**args)
    except TypeError as e:
        result = f"Error: bad arguments for {tool.name}: {e}"
    except Exception as e:  # tools report failures to the model, not the page
        result = f"Error: {e}"
    result = result if isinstance(result, str) else json.dumps(result, indent=2)
    return result[:limit]


def _as_tokens(text):
    # The final answer arrives in one piece; send it in small chunks so the
    # page shows it the same way as a streamed answer.
    for word in re.findall(r"\S+\s*|\s+", text):
        yield {"type": "token", "text": word}
