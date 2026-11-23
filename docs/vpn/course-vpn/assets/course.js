/* Course: behaviour shared by every unit and the home page.
   A unit is plain HTML that reads well without this script. This script adds:
   one step per screen, hand-drawn diagrams, the parts explorer, the terminal, the console tour,
   the questions and the score. Progress is kept in this browser only. */
(() => {
"use strict";
const NS = "http://www.w3.org/2000/svg";
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const el = (t, a, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
// Progress keys carry the course name from <html data-course>, so two courses on one site address keep apart.
const KEY = (document.documentElement.dataset.course || "course") + ":";
const store = {
  get(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v === null ? d : v; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage off: progress is not kept */ } }
};
const sleep = ms => new Promise(r => setTimeout(r, reduce() ? 0 : ms));

/* ---------- hand-drawn drawings ----------
   <svg class="sketch" data-drawing='{"w":560,"h":350,"shapes":[...]}'>
   Shapes: {"box":[x,y,w,h], "title", "detail", "part", "dashed", "fill":"hatch", "tone":"muted|mark"}
           {"line":[x1,y1,x2,y2], "part", "arrow", "tone"}
           {"text":"...", "at":[x,y], "hand", "size", "tone"}
           {"grid":[x,y,cols,rows,w,h,gapx,gapy], "tone"}
   A shape with "part" is clickable when the drawing sits in an explorer. */
const drawings = [];
function tone(t, fallback) { return t === "mark" ? css("--mark") : t === "muted" ? css("--muted") : fallback || css("--ink"); }
function drawSketch(d) {
  const svg = d.svg, spec = d.spec, sel = d.explorer ? d.explorer.sel : null;
  svg.innerHTML = "";
  svg.setAttribute("viewBox", "0 0 " + spec.w + " " + spec.h);
  const rc = window.rough ? window.rough.svg(svg) : null;
  const ink = css("--ink"), mark = css("--mark"), bg = css("--bg"), soft = css("--soft");
  const rect = (g, x, y, w, h, o) => rc ? g.appendChild(rc.rectangle(x, y, w, h, o))
    : el("rect", {x, y, width:w, height:h, fill: o.fillStyle === "hachure" ? css("--marksoft") : (o.fill || "none"), stroke:o.stroke, "stroke-width":o.strokeWidth, "stroke-dasharray": o.strokeLineDash ? o.strokeLineDash.join(" ") : "none"}, g);
  const line = (g, x1, y1, x2, y2, o) => rc ? g.appendChild(rc.line(x1, y1, x2, y2, o))
    : el("line", {x1, y1, x2, y2, stroke:o.stroke, "stroke-width":o.strokeWidth}, g);
  spec.shapes.forEach((s, i) => {
    const seed = i * 13 + 5;
    const on = !!(s.part && s.part === sel);
    if (s.grid) {
      const [x, y, cols, rows, w, h, gx, gy] = s.grid;
      for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++)
        rect(svg, x + c * gx, y + r * gy, w, h, {stroke:tone(s.tone), strokeWidth:1, roughness:1.2, seed:seed + r * 7 + c});
    } else if (s.line) {
      const [x1, y1, x2, y2] = s.line;
      const o = {stroke: on ? mark : tone(s.tone, css("--muted")), strokeWidth: on || s.tone === "mark" ? 2.6 : 1.5, roughness:1.2, seed};
      line(svg, x1, y1, x2, y2, o);
      if (s.arrow) {
        const a = Math.atan2(y2 - y1, x2 - x1), L = 13;
        line(svg, x2, y2, x2 - L * Math.cos(a - 0.5), y2 - L * Math.sin(a - 0.5), o);
        line(svg, x2, y2, x2 - L * Math.cos(a + 0.5), y2 - L * Math.sin(a + 0.5), o);
      }
    } else if (s.text) {
      const t = el("text", {x:s.at[0], y:s.at[1], "font-size":String(s.size || 17), fill:tone(s.tone, ink)}, svg);
      if (s.hand) t.setAttribute("class", "hw");
      if (s.bold) t.setAttribute("font-weight", "700");
      t.textContent = s.text;
    } else if (s.box) {
      const [x, y, w, h] = s.box;
      const interactive = s.part && d.explorer;
      const g = interactive ? el("g", {class:"hit", tabindex: s.dashed ? "-1" : "0", role:"button", "aria-label":s.title, "aria-pressed":String(on)}, svg) : svg;
      const hatch = on || s.fill === "hatch";
      const stroke = on ? mark : tone(s.tone);
      rect(g, x, y, w, h, {stroke, strokeWidth: on || s.tone === "mark" ? 2.8 : (s.heavy ? 2.4 : 1.5), roughness:1.3, seed,
        fill: hatch ? mark : (s.dashed ? soft : bg), fillStyle: hatch ? "hachure" : "solid", hachureGap:6, fillWeight:.7,
        strokeLineDash: s.dashed ? [6, 5] : undefined});
      if (s.title) {
        const big = h > 40;
        if (hatch) {
          el("rect", {x:x + 7, y:y + (big ? 9 : 6), width:Math.min(w - 14, s.title.length * 9 + 12), height:22, fill:bg}, g);
          if (big && s.detail) el("rect", {x:x + 7, y:y + 35, width:Math.min(w - 14, s.detail.length * 8 + 12), height:22, fill:bg}, g);
        }
        el("text", {x:x + 12, y:y + (big ? 25 : 22), "font-size":"15", "font-weight":"700", fill: on ? mark : ink}, g).textContent = s.title;
        if (big && s.detail) el("text", {x:x + 12, y:y + 51, "font-size":"16", class:"hw", fill: on ? ink : css("--muted")}, g).textContent = s.detail;
      }
      if (interactive) {
        el("rect", {class:"focus", x:x - 4, y:y - 4, width:w + 8, height:h + 8, fill:"none", stroke:"none"}, g);
        g.addEventListener("click", () => d.explorer.pick(s.part, true));
        g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); d.explorer.pick(s.part, true); } });
      }
    }
  });
}
function redrawAll() { drawings.forEach(drawSketch); }

/* ---------- parts explorer ----------
   <div class="explorer" data-start="disk" data-map='{"disk":[[8,23],[33,35]], ...}'>
     <svg class="sketch" data-drawing=...>  <div class="parts"><div class="part-info" data-part="disk">...
     <pre class="def">the definition</pre> */
function explorer(root) {
  const map = JSON.parse(root.dataset.map || "{}");
  const pre = root.querySelector("pre.def");
  const lines = pre.textContent.replace(/\n$/, "").split("\n");
  const owner = {};
  for (const [part, ranges] of Object.entries(map)) ranges.forEach(([a, b]) => { for (let i = a; i <= b; i++) owner[i] = part; });
  pre.innerHTML = lines.map((t, i) => '<div class="ln"' + (owner[i + 1] ? ' data-part="' + owner[i + 1] + '"' : "") +
    '><span class="n">' + (i + 1) + "</span><span>" + esc(t) + "</span></div>").join("");
  const ex = {sel: root.dataset.start, pick(p, scroll) {
    ex.sel = p;
    redrawAll();
    root.querySelectorAll(".part-info").forEach(x => x.classList.toggle("current", x.dataset.part === p));
    let first = null;
    pre.querySelectorAll(".ln").forEach(l => { const on = l.dataset.part === p; l.classList.toggle("on", on); if (on && !first) first = l; });
    if (scroll && first) pre.scrollTo({top:first.offsetTop - 12, behavior: reduce() ? "auto" : "smooth"});
  }};
  pre.querySelectorAll(".ln[data-part]").forEach(l => l.addEventListener("click", () => ex.pick(l.dataset.part, false)));
  root.querySelectorAll(".part-info").forEach(x => {
    const n = Object.entries(owner).filter(([, p]) => p === x.dataset.part).length;
    if (n) x.insertAdjacentHTML("beforeend", '<p class="small">' + n + " lines of the definition belong to this part.</p>");
  });
  root.querySelectorAll("svg.sketch").forEach(svg => drawings.push({svg, spec: JSON.parse(svg.dataset.drawing), explorer: ex}));
  return ex;
}

/* ---------- questions ---------- */
const answered = new Map();
function questions(onAnswer) {
  document.querySelectorAll(".q").forEach(q => {
    const opts = q.querySelectorAll(".opt");
    opts.forEach(b => b.addEventListener("click", () => {
      if (answered.has(q)) return;
      const ok = b.hasAttribute("data-ok");
      answered.set(q, ok);
      opts.forEach(o => { o.disabled = true; if (o.hasAttribute("data-ok")) o.classList.add("right"); });
      if (!ok) b.classList.add("wrong");
      const rev = q.querySelector("details.reveal");
      if (rev) { rev.open = true; rev.insertAdjacentHTML("afterbegin", "<p><b>" + (ok ? "Right." : "Not quite.") + "</b></p>"); }
      onAnswer(q);
    }));
  });
}
function score() {
  const checks = [...document.querySelectorAll(".q[data-check]")];
  const out = document.querySelector("[data-score]"), txt = document.querySelector("[data-score-text]");
  if (!out || !checks.length || !checks.every(q => answered.has(q))) return;
  const right = checks.filter(q => answered.get(q)).length;
  out.textContent = right + " / " + checks.length;
  if (txt) txt.textContent = right === checks.length ? "Ready for the next unit." : "Reread the answer under each one you missed, then carry on.";
}

/* ---------- terminal ----------
   <div class="term-block"> <div class="term"> <div class="cmd"><p class="pre">..</p><pre class="in">..</pre><pre class="out">..</pre><p class="hand note">..</p></div> ...
   A .q placed before a .cmd must be answered before that command runs. */
function terminal(block) {
  const term = block.querySelector(".term");
  const cmds = [...term.querySelectorAll(".cmd")];
  const gates = new Map();
  cmds.forEach((c, i) => { const q = c.previousElementSibling; if (q && q.classList.contains("q")) gates.set(i, q); });
  gates.forEach(q => { block.querySelector(".termcol").appendChild(q); q.hidden = true; });
  const notes = block.querySelector(".notes");
  const noteEls = cmds.map(c => [...c.querySelectorAll(".note")].map(n => { n.classList.add("tilt"); n.hidden = true; notes.appendChild(n); return n; }));
  const screen = document.createElement("pre"); screen.className = "screen-out"; screen.setAttribute("aria-live", "polite");
  term.appendChild(screen);
  const counter = block.querySelector("[data-term-count]");
  const run = block.querySelector("[data-run]"), label = run.querySelector("span"), next = run.querySelector("code");
  const caret = '<span class="caret">&nbsp;</span>', prompt = '<span class="p">$</span> ';
  let ti = 0, busy = false, html = "";
  const paint = extra => { screen.innerHTML = html + (extra || ""); screen.scrollTop = screen.scrollHeight; };
  function update() {
    if (counter) counter.textContent = ti + " of " + cmds.length;
    noteEls.forEach((ns, i) => ns.forEach(n => n.hidden = i >= ti));
    gates.forEach((q, i) => q.hidden = ti < i);
    if (ti >= cmds.length) { label.textContent = "All " + cmds.length + " commands run"; next.textContent = ""; run.disabled = true; return; }
    const c = cmds[ti].querySelector(".in").textContent;
    next.textContent = c.length > 30 ? c.slice(0, 28) + "…" : c;
    const gate = gates.get(ti), waiting = gate && !answered.has(gate);
    run.disabled = !!waiting;
    label.textContent = waiting ? "Answer the question below, then run" : "Run";
  }
  async function step() {
    if (busy || ti >= cmds.length) return;
    busy = true; run.disabled = true;
    const c = cmds[ti], pre = c.querySelector(".pre"), out = c.querySelector(".out");
    if (pre) html += '<span class="dim">' + esc(pre.textContent) + "</span>\n";
    html += prompt;
    const text = c.querySelector(".in").textContent;
    if (reduce()) html += esc(text);
    else for (const ch of text) { html += esc(ch); paint(caret); await sleep(16); }
    html += "\n"; paint();
    await sleep(450);
    html += (out.classList.contains("err") ? '<span class="err">' + esc(out.textContent) + "</span>" : esc(out.textContent)) + "\n\n";
    ti++; paint(ti < cmds.length ? prompt + caret : ""); busy = false; update();
  }
  run.addEventListener("click", step);
  block.querySelector("[data-run-reset]").addEventListener("click", () => { if (busy) return; ti = 0; html = ""; paint(prompt + caret); update(); });
  paint(prompt + caret);
  return update;
}

/* ---------- console tour ----------
   <div class="tour"><figure class="tstep" data-hot="left,top,width,height in %" data-width="640px">
     <div class="shot"><img ...></div><figcaption><h3>question</h3><details class="reveal">..</details></figcaption></figure> */
function tour(root) {
  const steps = [...root.querySelectorAll(".tstep")];
  let k = 0;
  steps.forEach((st, i) => {
    const shot = st.querySelector(".shot"), cap = st.querySelector("figcaption"), rev = st.querySelector("details.reveal");
    if (st.dataset.width) shot.style.width = "min(100%, " + st.dataset.width + ")";
    cap.insertAdjacentHTML("afterbegin", '<div class="tsteps">' + steps.map((_, j) => "<i" + (j <= i ? ' class="on"' : "") + "></i>").join("") +
      '</div><span class="tcount">Screen ' + (i + 1) + " of " + steps.length + "</span>");
    const fb = document.createElement("p"); fb.className = "fb"; fb.setAttribute("aria-live", "polite"); rev.before(fb);
    const nextBtn = document.createElement("button"); nextBtn.className = "btn line"; nextBtn.hidden = true;
    nextBtn.textContent = i < steps.length - 1 ? "Next screen" : "Do the tour again";
    cap.appendChild(nextBtn);
    nextBtn.addEventListener("click", () => { k = (i + 1) % steps.length; show(); });
    const [l, t, w, h] = st.dataset.hot.split(",").map(Number);
    const hot = document.createElement("button");
    hot.className = "hot"; hot.setAttribute("aria-label", "The right place to click");
    Object.assign(hot.style, {left:l + "%", top:t + "%", width:w + "%", height:h + "%"});
    shot.appendChild(hot);
    let misses = 0, hit = false;
    st.reset = () => { misses = 0; hit = false; hot.className = "hot"; rev.open = false; fb.textContent = ""; fb.className = "fb"; nextBtn.hidden = true; };
    hot.addEventListener("click", e => {
      e.stopPropagation(); if (hit) return; hit = true;
      hot.className = "hot hit"; fb.textContent = ""; rev.open = true; nextBtn.hidden = false;
    });
    shot.addEventListener("click", e => {
      if (hit) return;
      const r = shot.getBoundingClientRect();
      const m = document.createElement("span"); m.className = "miss"; m.textContent = "✗";
      m.style.left = (e.clientX - r.left) + "px"; m.style.top = (e.clientY - r.top) + "px";
      shot.appendChild(m); setTimeout(() => m.remove(), 1100);
      misses++;
      fb.textContent = misses >= 2 ? "It's marked now. Click inside the dashed outline." : "Not there. Try again.";
      if (misses >= 2) hot.classList.add("show");
    });
  });
  function show() { steps.forEach((s, j) => { s.classList.toggle("current", j === k); if (j === k) s.reset(); }); }
  show();
}

/* ---------- steps ---------- */
function stepper(unit) {
  const screens = [...document.querySelectorAll("main .screen")];
  const last = screens.length - 1, activities = last - 1;
  const segs = document.querySelector(".segs");
  segs.innerHTML = Array.from({length: activities}, () => "<i></i>").join("") + "<span></span>";
  const segI = [...segs.querySelectorAll("i")], segText = segs.querySelector("span");
  const back = document.querySelector("[data-back]"), next = document.querySelector("[data-next]");
  let cur = Math.min(store.get(KEY + unit + ":step", 0), last);
  function show(i, focus) {
    cur = Math.max(0, Math.min(last, i));
    screens.forEach((s, j) => s.classList.toggle("current", j === cur));
    segI.forEach((s, j) => s.classList.toggle("on", j < cur));
    segText.textContent = cur === 0 ? "Start" : cur === last ? "Complete" : "Step " + cur + " of " + activities;
    back.disabled = cur === 0;
    next.textContent = cur === 0 ? "Start" : cur === last - 1 ? "Finish" : cur === last ? "Start the unit again" : "Next";
    store.set(KEY + unit + ":step", cur);
    if (cur === last) { const done = store.get(KEY + "done", {}); done[unit] = true; store.set(KEY + "done", done); }
    redrawAll();
    if (focus) {
      window.scrollTo({top:0, behavior: reduce() ? "auto" : "smooth"});
      const h = screens[cur].querySelector("h1, h2"); h.setAttribute("tabindex", "-1"); h.focus({preventScroll:true});
    }
  }
  back.addEventListener("click", () => show(cur - 1, true));
  next.addEventListener("click", () => show(cur === last ? 0 : cur + 1, true));
  document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => show(+b.dataset.go, true)));
  const all = document.querySelector("[data-all]");
  all.addEventListener("click", () => {
    const stepped = !document.body.classList.toggle("stepped");
    all.setAttribute("aria-pressed", String(!stepped));
    all.textContent = stepped ? "Show all on one page" : "One step at a time";
    redrawAll();
  });
  document.body.classList.add("stepped");
  show(cur, false);
}

/* ---------- home page ticks ---------- */
function home() {
  const done = store.get(KEY + "done", {});
  document.querySelectorAll("[data-unit-link]").forEach(a => {
    const tick = a.closest("li").querySelector(".tick");
    if (tick && done[a.dataset.unitLink]) { tick.textContent = "✓"; tick.setAttribute("aria-label", "finished"); }
  });
}

/* ---------- boot ---------- */
function boot() {
  const unit = document.body.dataset.unit;
  document.querySelectorAll("svg.sketch").forEach(svg => {
    if (!svg.closest(".explorer")) drawings.push({svg, spec: JSON.parse(svg.dataset.drawing)});
  });
  const explorers = [...document.querySelectorAll(".explorer")].map(explorer);
  const terms = [...document.querySelectorAll(".term-block")].map(terminal);
  questions(() => { terms.forEach(u => u()); score(); });
  document.querySelectorAll(".tour").forEach(tour);
  terms.forEach(u => u());
  if (unit) stepper(unit); else home();
  explorers.forEach(ex => ex.pick(ex.sel, false));
  redrawAll();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redrawAll);
  if (document.fonts) document.fonts.ready.then(redrawAll);
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
