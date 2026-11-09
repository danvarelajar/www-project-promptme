/* Completion celebration for the dashboard. No dependencies; remove this
 * file and its <script> tag in templates/dashboard.html to turn it off.
 *
 *   PM.celebrate({ kind: "core", bonusLeft: 3 })   // all Level 1 flags
 *   PM.celebrate({ kind: "all" })                  // every flag, bonuses too
 *
 * Confetti on a canvas for about three seconds, then a card. People who ask
 * their system for reduced motion get the card only.
 */
(function () {
  "use strict";
  const PM = (window.PM = window.PM || {});

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  function confetti(pieces, ms) {
    const canvas = document.createElement("canvas");
    canvas.className = "pm-confetti";
    canvas.setAttribute("aria-hidden", "true");
    document.body.append(canvas);
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const resize = () => {
      canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    addEventListener("resize", resize);

    const colors = [cssVar("--mica", "#2ec4b0"), cssVar("--accent", "#f0b43c"), cssVar("--ok", "#4cc38a"),
                    cssVar("--info", "#7aa7ff"), "#ffffff"];
    const W = () => innerWidth, H = () => innerHeight;
    // Two bursts from the lower corners, plus a light fall from the top.
    const parts = [];
    for (let i = 0; i < pieces; i++) {
      const side = i % 3;
      const fromTop = side === 2;
      const x = fromTop ? Math.random() * W() : side === 0 ? -10 : W() + 10;
      const y = fromTop ? -20 - Math.random() * H() * 0.5 : H() * (0.7 + Math.random() * 0.2);
      const angle = fromTop ? Math.PI / 2 : (side === 0 ? -1.15 : -Math.PI + 1.15) + (Math.random() - 0.5) * 0.7;
      const speed = fromTop ? 1 + Math.random() * 2 : 16 + Math.random() * 12;
      parts.push({
        x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
        w: 6 + Math.random() * 6, h: 8 + Math.random() * 10, r: Math.random() * Math.PI,
        vr: (Math.random() - 0.5) * 0.3, color: colors[i % colors.length], wobble: Math.random() * 10,
      });
    }
    const start = performance.now();
    const STEP = 1000 / 60;   // physics runs in 60 Hz steps, whatever the screen's frame rate
    let frame, simulated = 0;
    function tick(now) {
      const t = now - start;
      // Catch up in fixed steps, so a slow or busy browser shows the same
      // flight, just with fewer frames.
      let steps = Math.min(Math.floor((t - simulated) / STEP), 60);
      for (; steps > 0; steps--) {
        simulated += STEP;
        for (const p of parts) {
          p.vy += 0.22; p.vx *= 0.985; p.vy *= 0.985;
          p.x += p.vx + Math.sin((simulated / 200) + p.wobble) * 0.6; p.y += p.vy; p.r += p.vr;
        }
      }
      ctx.clearRect(0, 0, W(), H());
      const fade = t > ms - 600 ? Math.max(0, (ms - t) / 600) : 1;
      ctx.globalAlpha = fade;
      for (const p of parts) {
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r);
        ctx.fillStyle = p.color; ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h * Math.abs(Math.cos(p.r * 2)) + 2);
        ctx.restore();
      }
      if (t < ms) frame = requestAnimationFrame(tick);
      else { removeEventListener("resize", resize); canvas.remove(); }
    }
    frame = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(frame); removeEventListener("resize", resize); canvas.remove(); };
  }

  function showCard(opts) {
    document.querySelector(".pm-celebrate")?.remove();
    const h = PM.h;
    const all = opts.kind === "all";
    const title = all ? "Full house: every risk, every bonus" : "All 10 OWASP LLM risks captured";
    const lines = all
      ? ["You captured all ten Level 1 flags and every Level 2 bonus.",
         "Each of these weaknesses is one you can now spot in a real LLM application."]
      : ["You broke all ten applications, one OWASP Top 10 for LLMs risk each.",
         opts.bonusLeft ? `${opts.bonusLeft} optional Level 2 ${opts.bonusLeft === 1 ? "challenge is" : "challenges are"} still open if you want more.`
                        : "Nicely done."];
    const close = h("button", { class: "pm-btn primary", type: "button", text: all ? "Back to the dashboard" : "Keep going" });
    const card = h("div", { class: "pm-celebrate-card", role: "dialog", "aria-modal": "true", "aria-labelledby": "pm-celebrate-title" },
      h("div", { class: "pm-celebrate-badge", "aria-hidden": "true", text: all ? "15/15" : "10/10" }),
      h("h2", { id: "pm-celebrate-title", text: title }),
      ...lines.map((t) => h("p", { class: "muted", text: t })),
      close);
    const overlay = h("div", { class: "pm-celebrate" }, card);
    const previous = document.activeElement;
    const dismiss = () => { overlay.remove(); document.removeEventListener("keydown", onKey); previous?.focus?.(); };
    const onKey = (e) => { if (e.key === "Escape") dismiss(); };
    close.addEventListener("click", dismiss);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) dismiss(); });
    document.addEventListener("keydown", onKey);
    document.body.append(overlay);
    close.focus();
  }

  PM.celebrate = function (opts) {
    opts = opts || {};
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduced) confetti(opts.kind === "all" ? 260 : 160, opts.kind === "all" ? 4200 : 3200);
    // Let the first burst play before the card covers the page.
    setTimeout(() => showCard(opts), reduced ? 0 : 700);
  };
})();
