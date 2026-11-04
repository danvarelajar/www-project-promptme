/* PromptMe UI helpers. No dependencies.
 *
 *   PM.theme.toggle()
 *   PM.chat({
 *     root: "#chat",            // element with the .pm-chat markup from pm_base.html macros
 *     endpoint: "/api/chat",    // POST, answers with text/event-stream (promptme.web.sse)
 *     body: text => ({ message: text }),
 *     trace: "#trace",          // optional "Under the hood" panel
 *     suggestions: ["…"],       // optional starter prompts
 *   })
 *
 * Stream events: token, trace, flag, error, done (see promptme/web.py).
 */
(function () {
  "use strict";
  const PM = (window.PM = window.PM || {});

  /* ---------- theme ---------- */
  const THEME_KEY = "pm-theme";
  PM.theme = {
    get() { try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; } },
    apply(t) {
      if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
      else document.documentElement.removeAttribute("data-theme");
    },
    toggle() {
      const cur = document.documentElement.getAttribute("data-theme") ||
        (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
      const next = cur === "light" ? "dark" : "light";
      PM.theme.apply(next);
      try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
    },
  };
  PM.theme.apply(PM.theme.get());

  /* ---------- tiny DOM helper ---------- */
  PM.h = function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat()) if (k != null && k !== false) el.append(k.nodeType ? k : document.createTextNode(String(k)));
    return el;
  };
  const h = PM.h;
  const $ = (sel) => (typeof sel === "string" ? document.querySelector(sel) : sel);

  /* ---------- server-sent events over POST ---------- */
  PM.stream = async function (url, body, onEvent, signal) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok || !res.body) {
      let msg = `Request failed (HTTP ${res.status}).`;
      try { const j = await res.json(); if (j.error) msg = j.error; } catch (e) {}
      onEvent({ type: "error", message: msg });
      return;
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i);
        buf = buf.slice(i + 2);
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data:")) continue;
          try { onEvent(JSON.parse(line.slice(5).trim())); } catch (e) {}
        }
      }
    }
  };

  /* ---------- chat component ---------- */
  PM.chat = function (opts) {
    const root = $(opts.root);
    const log = root.querySelector(".pm-chat-log");
    const form = root.querySelector(".pm-chat-form");
    const input = form.querySelector("textarea");
    const send = form.querySelector("button[type=submit]");
    const traceRoot = opts.trace ? $(opts.trace) : null;
    const traceLog = traceRoot ? traceRoot.querySelector(".pm-trace-log") : null;
    const flagSlot = opts.flag ? $(opts.flag) : null;
    let busy = false;
    let step = 0;

    function emptyState() {
      if (log.children.length) return;
      log.append(h("div", { class: "pm-chat-empty", text: opts.empty || "Ask something to get started." }));
    }
    function clearEmpty() { log.querySelector(".pm-chat-empty")?.remove(); }

    function addMsg(role, text) {
      clearEmpty();
      const who = role === "user" ? "You" : role === "assistant" ? (opts.botName || "Assistant") : role === "error" ? "Error" : "System";
      const body = h("div", { class: "body", text: text || "" });
      const msg = h("div", { class: `pm-msg ${role}` }, h("span", { class: "who", text: who }), body);
      log.append(msg);
      log.scrollTop = log.scrollHeight;
      return body;
    }

    function addTrace(title, text) {
      if (!traceLog) return;
      traceLog.querySelector(".pm-trace-empty")?.remove();
      step += 1;
      const t = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      const item = h("details", { class: "pm-trace-item" },
        h("summary", null, h("span", { text: `${step}. ${title}` }), h("span", { class: "t", text: t })),
        h("pre", { text: text || "" }));
      traceLog.append(item);
      traceLog.scrollTop = traceLog.scrollHeight;
    }

    function showFlag(flag) {
      if (!flagSlot) return;
      flagSlot.hidden = false;
      flagSlot.replaceChildren(
        h("strong", { text: "Flag captured" }),
        h("code", { text: flag }),
        h("span", { class: "muted", text: "Submit it on the dashboard." }));
    }

    async function submit(text) {
      text = (text || "").trim();
      if (!text || busy) return;
      busy = true; send.disabled = true; input.value = "";
      addMsg("user", text);
      const out = addMsg("assistant", "");
      out.classList.add("streaming");
      try {
        await PM.stream(opts.endpoint, opts.body ? opts.body(text) : { message: text }, (ev) => {
          if (ev.type === "token") { out.textContent += ev.text; log.scrollTop = log.scrollHeight; }
          else if (ev.type === "trace") addTrace(ev.title, ev.body);
          else if (ev.type === "flag") showFlag(ev.flag);
          else if (ev.type === "error") { out.parentElement.className = "pm-msg error"; out.textContent = ev.message; }
        });
      } catch (e) {
        out.parentElement.className = "pm-msg error";
        out.textContent = "Lost the connection to the challenge. Is it still running?";
      } finally {
        out.classList.remove("streaming");
        if (!out.textContent) out.textContent = "(no answer)";
        busy = false; send.disabled = false; input.focus();
      }
    }

    form.addEventListener("submit", (e) => { e.preventDefault(); submit(input.value); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(input.value); }
    });
    if (opts.suggestions && opts.suggestions.length) {
      const box = h("div", { class: "pm-suggestions" },
        opts.suggestions.map((s) => h("button", { type: "button", text: s, onclick: () => submit(s) })));
      form.before(box);
    }
    if (traceLog && !traceLog.children.length) {
      traceLog.append(h("div", { class: "pm-trace-empty", text: "Each step the app takes — prompts it builds, documents it retrieves, tools it calls — shows up here." }));
    }
    emptyState();
    return { submit, addMsg, addTrace };
  };
})();
