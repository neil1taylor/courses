/* The narrated module player: 1920x1080 slides that build with the voice.
   Pure helpers first (tested with node --test), then the browser player. */
"use strict";

const GAP = 0.8, BASE = 0.92, LABEL_FLOOR = 36;

const cueLen = q => q.dur / BASE + GAP + (q.hold || 0);

/* The step and cue playing `seconds` into the module, clamped to both ends. */
function cueAt(timeline, seconds) {
  const steps = timeline.steps;
  let acc = 0;
  for (let s = 0; s < steps.length; s++) {
    for (let c = 0; c < steps[s].cues.length; c++) {
      acc += cueLen(steps[s].cues[c]);
      if (seconds < acc) return { step: s, cue: c };
    }
  }
  const last = steps.length - 1;
  return { step: Math.max(0, last), cue: Math.max(0, steps[last].cues.length - 1) };
}

const answerFor = (answers, id) => (answers instanceof Map ? answers.get(id) : answers[id]);

/* Score from the check questions in the timeline only. An answer is keyed by its
   slide ("step:cue"), so answering again after a seek replaces it: each question counts once. */
function scoreOf(answers, timeline) {
  let right = 0, total = 0, answered = 0;
  timeline.steps.forEach((step, s) => step.cues.forEach((cue, c) => {
    if (!cue.slide || cue.slide.type !== "q" || !cue.slide.check) return;
    total++;
    const a = answerFor(answers, s + ":" + c);
    if (a === undefined || a === null) return;
    answered++;
    if (a.pick === cue.slide.ok) right++;
  }));
  return { right, total, answered };
}

const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/* The summary sentence is escaped whole; only <em> and </em> (the blue key words) are let back in. */
const summaryHtml = text => esc(text).replace(/&lt;em&gt;/g, "<em>").replace(/&lt;\/em&gt;/g, "</em>");

/* Reaching a question's ask cue, by playing or by seeking, clears the earlier answer to that question. */
function answersAfterReaching(answers, timeline, step, cue) {
  const out = new Map(answers instanceof Map ? answers : Object.entries(answers));
  const cues = timeline.steps[step].cues;
  if (!(cues[cue].do || []).some(a => a[0] === "ask")) return out;
  let first = cue;
  while (first > 0 && !cues[first].slide) first--;
  out.delete(step + ":" + first);
  return out;
}

/* Label size in sketch units so the label shows at 36px or more on the canvas at this scale. */
const labelSize = (scale, units) => Math.max(units, LABEL_FLOOR / scale);

/* Where a box and its text go at this scale. The box grows when the floored text would not fit. */
function boxLayout([x, y, w, h], title, detail, scale) {
  const tf = labelSize(scale, 21), df = labelSize(scale, 20), two = !!detail && h > 44;
  const need = two ? tf + df + 9 + df * 0.3 + 6 : tf * 1.35;
  const nh = Math.max(h, need), nw = Math.max(w, title ? title.length * tf * 0.55 + 24 : w);
  return {x, y, w: nw, h: nh, tf, df, two,
    titleY: y + (two ? tf + 4 : nh / 2 + tf * 0.35), detailY: y + tf + df + 9};
}

const progressKey = slug => "courses-video:" + slug;

function doneModules(storage, slug) {
  try {
    const list = JSON.parse(storage.getItem(progressKey(slug)) || "[]");
    return Array.isArray(list) ? list : [];
  } catch (e) { return []; }
}

function markDone(storage, slug, module) {
  const list = doneModules(storage, slug);
  if (!list.includes(module)) list.push(module);
  list.sort((a, b) => a - b);
  try { storage.setItem(progressKey(slug), JSON.stringify(list)); } catch (e) { /* storage blocked: progress is not kept */ }
}

/* A box in image pixels, as percentages of the image. The player puts the boxes inside a wrapper the exact size of the image. */
function boxPercent([x, y, w, h], img) {
  return { left: x / img.w * 100, top: y / img.h * 100, width: w / img.w * 100, height: h / img.h * 100 };
}

/* The largest size that fits the frame with the image's shape kept. */
function fitSize(img, frame) {
  if (!img.w || !img.h) return { w: 0, h: 0 };
  const s = Math.min(frame.w / img.w, frame.h / img.h);
  return { w: Math.round(img.w * s), h: Math.round(img.h * s) };
}

function browserStorage() {
  try { return window.localStorage; } catch (e) { return { getItem() { throw e; }, setItem() { throw e; } }; }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { cueAt, cueLen, scoreOf, esc, summaryHtml, answersAfterReaching, labelSize, boxLayout, boxPercent, fitSize, progressKey, markDone, doneModules };
}

/* ---- the contents page: show which modules are done ---- */
function markContents() {
  const root = document.querySelector("[data-contents]");
  if (!root) return;
  const done = doneModules(browserStorage(), root.dataset.course);
  root.querySelectorAll("[data-module]").forEach(a => {
    const d = done.includes(+a.dataset.module);
    a.classList.toggle("done", d);
    const mark = a.querySelector(".tick");
    if (mark) mark.textContent = d ? "Done" : "";
  });
  const n = root.querySelector("[data-count]");
  if (n) n.textContent = done.length + " of " + root.querySelectorAll("[data-module]").length + " modules done";
}

function startPlayer() {
const TL = window.TIMELINE, steps = TL.steps, SK = TL.sketches || {};
const $ = s => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
const store = browserStorage();
const audio = new Audio(); audio.preservesPitch = true;
let si = 0, qi = 0, playing = false, waiting = null, rate = BASE, timer = null, started = false;
const stepsDone = new Set(), answers = new Map();
const gapOf = q => GAP + (q.hold || 0);
steps.forEach(c => { c.total = c.cues.reduce((t, q) => t + cueLen(q), 0); });
const moduleTotal = steps.reduce((t, c) => t + c.total, 0);
const fmt = s => Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");

/* ---- stage ---- */
const stage = $("#stage"), canvas = $("#canvas");
function fit() { const r = stage.getBoundingClientRect(); canvas.style.transform = "scale(" + Math.min(r.width / 1920, r.height / 1080) + ")"; }
addEventListener("resize", fit);

/* ---- hand-drawn sketches: each shape is a group with a state: off, cur (blue) or past (grey) ---- */
const COL = {ink: "#111", cur: "#1F4FA8", past: "#9a9a9a"};
function el(t, a, p) { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; }
function makeSketch(name) {
  const spec = SK[name], svg = el("svg", {class: "sk", viewBox: "0 0 " + spec.w + " " + spec.h, preserveAspectRatio: "xMidYMid meet"});
  svg.spec = spec; svg.state = spec.shapes.map(() => "off");
  spec.shapes.forEach((_, i) => el("g", {"data-i": i}, svg));
  return svg;
}
/* Size a label in sketch units so that it shows at 36px or more on the 1920x1080 canvas.
   The svg's layout size is in canvas pixels, so the scale does not depend on the window. */
function sketchScale(svg) {
  const w = svg.clientWidth, h = svg.clientHeight;
  return w && h ? Math.min(w / svg.spec.w, h / svg.spec.h) : 1;
}
function paintShape(svg, i, animate) {
  const s = svg.spec.shapes[i], g = svg.querySelector('g[data-i="' + i + '"]'), st = svg.state[i];
  g.innerHTML = ""; g.style.opacity = st === "off" ? 0 : 1;
  if (st === "off") return;
  const rc = rough.svg(svg), c = st === "cur" ? COL.cur : st === "past" ? COL.past : COL.ink, w = st === "cur" ? 3 : 2, seed = i * 13 + 5;
  if (s.line) {
    const [x1, y1, x2, y2] = s.line, o = {stroke: c, strokeWidth: w, roughness: 1.2, seed};
    g.appendChild(rc.line(x1, y1, x2, y2, o));
    if (s.arrow) { const a = Math.atan2(y2 - y1, x2 - x1), L = 13; g.appendChild(rc.line(x2, y2, x2 - L * Math.cos(a - .5), y2 - L * Math.sin(a - .5), o)); g.appendChild(rc.line(x2, y2, x2 - L * Math.cos(a + .5), y2 - L * Math.sin(a + .5), o)); }
  } else if (s.text) {
    el("text", {x: s.at[0], y: s.at[1], "font-size": labelSize(sketchScale(svg), 22), class: s.hand ? "hw" : "", fill: c}, g).textContent = s.text;
  } else if (s.box) {
    const L = boxLayout(s.box, s.title, s.detail, sketchScale(svg));
    g.appendChild(rc.rectangle(L.x, L.y, L.w, L.h, {stroke: c, strokeWidth: s.heavy || st === "cur" ? w + .6 : w, roughness: 1.3, seed,
      fill: st === "cur" ? "#E8EEF9" : "#fff", fillStyle: "solid", strokeLineDash: s.dashed ? [6, 5] : undefined}));
    if (s.title) el("text", {x: L.x + 12, y: L.titleY, "font-size": L.tf, "font-weight": 700, fill: c === COL.past ? COL.past : COL.ink}, g).textContent = s.title;
    if (s.detail && L.two) el("text", {x: L.x + 12, y: L.detailY, "font-size": L.df, class: "hw", fill: c === COL.past ? COL.past : "#444"}, g).textContent = s.detail;
  }
  if (animate) {
    const paths = [...g.querySelectorAll("path")], texts = [...g.querySelectorAll("text")];
    paths.forEach(p => { const L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; });
    texts.forEach(t => t.style.opacity = 0);
    g.getBoundingClientRect();
    paths.forEach((p, k) => { p.style.transition = "stroke-dashoffset .7s ease-in-out " + k * 60 + "ms"; p.style.strokeDashoffset = 0; });
    texts.forEach(t => { t.style.transition = "opacity .5s ease .5s"; t.style.opacity = 1; });
  }
}
function build(svg, idx, animate) {
  svg.state = svg.state.map(s => s === "cur" ? "past" : s);
  idx.forEach(i => svg.state[i] = "cur");
  svg.spec.shapes.forEach((_, i) => paintShape(svg, i, animate && idx.includes(i)));
}

/* ---- slides ---- */
let slide = null, slideId = null;
function k(html, key, cls) { return '<div class="k off ' + (cls || "") + '" data-k="' + key + '">' + html + "</div>"; }
function renderSlide(spec, id) {
  slideId = id; canvas.innerHTML = ""; setAnswerBar(null);
  const d = document.createElement("div"); d.className = "sl t-" + spec.type; slide = d; d.spec = spec;
  const head = '<h2 class="head">' + esc(spec.head || "") + "</h2>";
  if (spec.type === "title") d.innerHTML = '<div class="left">' + k(head, "head") + k('<p class="sub">' + esc(spec.sub) + "</p>", "sub") + "</div>";
  if (spec.type === "diagram" || spec.type === "statement") { d.innerHTML = k(head, "head"); if (spec.sketch) d.classList.add("has-sk"); }
  if (spec.type === "q") {
    d.innerHTML = k(head, "head") + '<div class="k off opts" data-k="opts">' + spec.opts.map((o, j) => '<button class="opt" data-j="' + j + '"><span class="l">' + "ABCD"[j] + "</span>" + esc(o) + "</button>").join("") + "</div>" +
      k('<p class="askhint">Pick an answer to carry on</p>', "hint") + k('<p class="why">' + esc(spec.why) + "</p>", "why");
    d.querySelectorAll(".opt").forEach(b => b.onclick = () => answer(d, +b.dataset.j, true));
  }
  if (spec.type === "tip") d.innerHTML = k('<p class="tag">Watch for this</p>' + head, "head") + k('<p class="tip">' + esc(spec.tip) + "</p>", "tip");
  if (spec.type === "words") d.innerHTML = k(head, "head") + '<div class="grid">' + spec.items.map((it, j) => '<div class="cell k off" data-k="i' + j + '"><b>' + esc(it[0]) + "</b><span>" + esc(it[1]) + "</span></div>").join("") + "</div>";
  if (spec.type === "summary") d.innerHTML = '<div class="left">' + k('<p class="big">' + summaryHtml(spec.text) + "</p>", "head") + k('<p class="next">' + esc(spec.next) + "</p>", "next") + "</div>";
  if (spec.type === "screen") {
    d.innerHTML = k(head, "head") + k('<div class="shot"><div class="pic"><img alt="" src="' + esc(spec.img) + '">' + spec.boxes.map((_, j) => '<i class="bx off" data-b="' + j + '"></i>').join("") + "</div></div>", "img");
    const img = d.querySelector("img"), shot = d.querySelector(".shot"), pic = d.querySelector(".pic");
    const place = () => {
      const size = { w: img.naturalWidth, h: img.naturalHeight }, fit = fitSize(size, { w: shot.clientWidth, h: shot.clientHeight });
      pic.style.width = fit.w + "px"; pic.style.height = fit.h + "px";
      d.querySelectorAll(".bx").forEach((b, j) => { const r = boxPercent(spec.boxes[j], size);
        b.style.left = r.left + "%"; b.style.top = r.top + "%"; b.style.width = r.width + "%"; b.style.height = r.height + "%"; });
    };
    d.place = place;
    if (img.complete && img.naturalWidth) place(); else img.addEventListener("load", place);
  }
  if (spec.type === "terminal") {
    const out = Array.isArray(spec.out) ? spec.out : String(spec.out).split("\n");
    d.innerHTML = '<div class="term"><div class="cmd">$ ' + esc(spec.cmd) + "</div>" + out.map((l, j) => '<div class="ol" data-l="' + j + '">' + esc(l) + "</div>").join("") + "</div>";
  }
  if (spec.type === "score") {
    const sc = scoreOf(answers, TL), known = sc.answered === sc.total && sc.total > 0;
    d.innerHTML = k('<div class="num">' + (known ? sc.right + "<small> of " + sc.total + "</small>" : "Module done") + '</div><p class="means">' +
      (!known ? "Answer the questions to see your score." : sc.right === sc.total ? "You got every one right." : "Go back over the ones you missed.") + "</p>", "head");
  }
  if (spec.sketch) { const svg = makeSketch(spec.sketch); d.svg = svg; d.appendChild(svg); }
  canvas.appendChild(d);
  if (d.place) d.place();
  const prev = answers.get(id);
  if (prev && spec.type === "q") answer(d, prev.pick, false);
}

/* On a phone the cards on the slide are small, so the same answers also sit below the stage as big buttons. */
function setAnswerBar(d) {
  const bar = $("#answerbar"); bar.innerHTML = "";
  if (!d) { bar.hidden = true; return; }
  d.spec.opts.forEach((o, j) => {
    const b = document.createElement("button"); b.dataset.j = j;
    b.innerHTML = '<span class="l">' + "ABCD"[j] + "</span>" + esc(o); b.onclick = () => answer(d, j, true); bar.appendChild(b);
  });
  bar.hidden = false;
}
function answer(d, j, user) {
  const spec = d.spec, opts = d.querySelector(".opts");
  if (opts.classList.contains("answered")) return;
  opts.classList.add("answered");
  opts.querySelectorAll(".opt").forEach((b, x) => { b.disabled = true; if (x === spec.ok) b.classList.add("right"); if (x === j) b.classList.add("picked"); });
  d.querySelector('[data-k="hint"]').classList.add("off");
  setAnswerBar(null);
  if (user) {
    answers.set(slideId, {pick: j});
    if (waiting === d) { waiting = null; clearTimeout(timer); timer = setTimeout(() => { if (playing) advance(); }, 1300); }
  }
}
function act([a, v], animate) {
  const d = slide; if (!d) return;
  const show = key => { const e = d.querySelector('[data-k="' + key + '"]'); if (e) { if (!animate) e.style.transition = "none"; e.classList.remove("off"); } };
  if (a === "show") { show(v); if (v === "head" && d.spec.type === "screen") show("img"); }
  if (a === "build" && d.svg) build(d.svg, v, animate);
  if (a === "items") { d.querySelectorAll(".cell.cur").forEach(c => { c.classList.remove("cur"); c.classList.add("past"); }); v.forEach(j => { show("i" + j); d.querySelector('[data-k="i' + j + '"]').classList.add("cur"); }); }
  if (a === "box") { d.querySelectorAll(".bx.cur").forEach(b => { b.classList.remove("cur"); b.classList.add("past"); }); const b = d.querySelector('.bx[data-b="' + v + '"]'); if (b) { if (!animate) b.style.transition = "none"; b.classList.remove("off"); b.classList.add("cur"); } }
  if (a === "line") { d.querySelectorAll(".ol.cur").forEach(l => { l.classList.remove("cur"); l.classList.add("past"); }); const l = d.querySelector('.ol[data-l="' + v + '"]'); if (l) l.classList.add("cur"); }
  if (a === "ask") { show("head"); show("opts"); if (!d.querySelector(".opts.answered")) setAnswerBar(d); }
  if (a === "why") { if (!d.querySelector(".opts.answered")) answer(d, -1, false); show("why"); }
}

/* ---- playback ---- */
const cuesOf = s => steps[s].cues;
function slideStart(s, q) { let x = q; while (x > 0 && !cuesOf(s)[x].slide) x--; return x; }
function goto(s, q, keep) {
  audio.pause(); clearTimeout(timer); waiting = null;
  si = s; qi = q;
  const first = slideStart(si, qi), spec = cuesOf(si)[first].slide, id = si + ":" + first;
  reach(si, qi);
  renderSlide(spec, id);
  for (let x = first; x < qi; x++) (cuesOf(si)[x].do || []).forEach(a => act(a, false));
  if (!(keep && playing)) (cuesOf(si)[qi].do || []).forEach(a => act(a, false));
  $("#cc").textContent = cuesOf(si)[qi].say;
  render();
  if (keep && playing) playCue();
}
function reach(s, q) { const next = answersAfterReaching(answers, TL, s, q); answers.clear(); next.forEach((v, key) => answers.set(key, v)); }
function playCue() {
  const cue = cuesOf(si)[qi];
  reach(si, qi);
  if ((cue.do || []).some(a => a[0] === "ask") && slide && slide.querySelector(".opts.answered")) {
    const first = slideStart(si, qi);
    renderSlide(cuesOf(si)[first].slide, si + ":" + first);
    for (let x = first; x < qi; x++) (cuesOf(si)[x].do || []).forEach(a => act(a, false));
  }
  if (cue.slide && slideId !== si + ":" + qi) renderSlide(cue.slide, si + ":" + qi);
  (cue.do || []).forEach(a => act(a, true));
  $("#cc").textContent = cue.say;
  audio.src = cue.audio; audio.playbackRate = rate;
  const p = audio.play();
  if (p && p.catch) p.catch(() => { playing = false; $("#bigplay").hidden = false; render(); });
  render();
}
audio.addEventListener("ended", () => {
  const cue = cuesOf(si)[qi];
  if ((cue.do || []).some(a => a[0] === "ask") && !slide.querySelector(".opts.answered")) {
    waiting = slide; slide.querySelector('[data-k="hint"]').classList.remove("off"); render(); return;
  }
  clearTimeout(timer); timer = setTimeout(advance, gapOf(cue) * 1000);
});
function advance() {
  if (qi + 1 < cuesOf(si).length) { qi++; playCue(); return; }
  stepsDone.add(si); $("#cc").textContent = "";
  if (si + 1 < steps.length) { si++; qi = 0; playCue(); return; }
  playing = false; finishModule(); render();
}
function finishModule() {
  markDone(store, TL.courseSlug, TL.moduleIndex);
  if (TL.nextHref && $("#autoplay").checked) location.href = TL.nextHref + "#play";
}
function play() {
  if (!started) { started = true; goto(si, qi, false); }
  playing = true; $("#bigplay").hidden = true;
  if (waiting) { render(); return; }
  if (audio.src && !audio.ended && audio.currentTime > 0) audio.play(); else playCue();
  render();
}
function pause() { playing = false; audio.pause(); clearTimeout(timer); render(); }

/* ---- controls ---- */
const go = (s, q) => { started = true; $("#bigplay").hidden = true; goto(s, q, true); };
function stepBy(n) {
  const target = n < 0 ? (qi > 0 ? si : Math.max(0, si - 1)) : si + 1;
  if (target >= steps.length) return;
  if (n > 0) stepsDone.add(si);
  go(target, 0);
}
function cueBy(n) {
  let s = si, q = qi + n;
  if (q < 0) { if (s === 0) return go(0, 0); s--; q = cuesOf(s).length - 1; }
  else if (q >= cuesOf(s).length) { if (s + 1 >= steps.length) return; stepsDone.add(s); s++; q = 0; }
  go(s, q);
}
$("#play").onclick = () => playing ? pause() : play();
$("#bigplay").onclick = play;
$("#prevstep").onclick = () => stepBy(-1);
$("#nextstep").onclick = () => stepBy(1);
$("#backline").onclick = () => cueBy(-1);
$("#fwdline").onclick = () => cueBy(1);
$("#speed").onclick = () => { rate = rate < 1 ? 1.25 : rate >= 1.5 ? BASE : rate + 0.25; audio.playbackRate = rate; $("#speed").textContent = (rate < 1 ? 1 : rate / BASE).toFixed(2).replace(/\.?0+$/, "") + "x"; };
$("#ccbtn").onclick = () => { const on = $("#ccbtn").classList.toggle("on"); $("#cc").classList.toggle("off", !on); $("#ccbtn").setAttribute("aria-pressed", on); };
$("#seek").onclick = e => {
  const r = e.currentTarget.getBoundingClientRect(), p = cueAt(TL, (e.clientX - r.left) / r.width * moduleTotal);
  go(p.step, p.cue);
};
document.addEventListener("keydown", e => {
  if (e.target.closest("button, input")) return;
  if (e.code === "Space") { e.preventDefault(); $("#play").onclick(); }
  if (e.code === "ArrowLeft") { e.preventDefault(); cueBy(-1); }
  if (e.code === "ArrowRight") { e.preventDefault(); cueBy(1); }
});
document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll(".tabs button").forEach(x => x.classList.toggle("on", x === b));
  $("#toc").hidden = b.dataset.tab !== "toc"; $("#tr").hidden = b.dataset.tab !== "tr";
});

/* ---- side panel ---- */
$("#toc").innerHTML = steps.map((c, i) => '<div class="step" data-c="' + i + '"><span class="ic">' + (i + 1) + "</span><span><b>" + esc(c.title) + "</b><small>" + fmt(c.total) + "</small></span></div>").join("");
$("#toc").querySelectorAll(".step").forEach(e => e.onclick = () => go(+e.dataset.c, 0));
$("#tr").innerHTML = '<div class="trc">' + steps.map((c, i) => "<h4>" + esc(c.title) + "</h4>" + c.cues.map((q, x) => '<p data-c="' + i + '" data-q="' + x + '">' + esc(q.say) + "</p>").join("")).join("") + "</div>";
$("#tr").querySelectorAll("p").forEach(p => p.onclick = () => go(+p.dataset.c, +p.dataset.q));
function elapsed() { let t = 0; for (let s = 0; s < si; s++) t += steps[s].total; for (let x = 0; x < qi; x++) t += cueLen(cuesOf(si)[x]); return t + (audio.src ? audio.currentTime / BASE : 0); }
function render() {
  $("#play").innerHTML = playing ? "&#10074;&#10074;" : "&#9654;";
  $("#play").setAttribute("aria-label", playing ? "Pause" : "Play");
  $("#toc").querySelectorAll(".step").forEach((e, i) => { e.classList.toggle("cur", i === si); e.classList.toggle("done", stepsDone.has(i)); e.querySelector(".ic").textContent = stepsDone.has(i) ? "✓" : i + 1; });
  $("#tr").querySelectorAll("p").forEach(p => p.classList.toggle("now", +p.dataset.c === si && +p.dataset.q === qi));
  const earlier = doneModules(store, TL.courseSlug), pct = earlier.includes(TL.moduleIndex) ? 100 : Math.round(stepsDone.size / steps.length * 100);
  $("#cfill").style.width = pct + "%"; $("#cpct").textContent = pct + "%";
  $("#modsdone").textContent = earlier.length + " of " + TL.moduleTotal + " modules done";
  $("#donebadge").hidden = !earlier.includes(TL.moduleIndex);
}
setInterval(() => {
  const t = Math.min(elapsed(), moduleTotal), f = t / moduleTotal * 100;
  $("#fill").style.width = f + "%"; $("#knob").style.left = f + "%";
  $("#time").textContent = fmt(t) + " / " + fmt(moduleTotal);
}, 200);

/* poster: the title slide, complete */
fit();
const boot = () => {
  goto(0, 0, false); cuesOf(0).forEach(c => (c.do || []).forEach(a => act(a, false))); qi = 0;
  if (slide.svg) { slide.svg.state = slide.svg.state.map(() => "on"); slide.svg.spec.shapes.forEach((_, i) => paintShape(slide.svg, i, false)); }
  $("#cc").textContent = "";
  if (location.hash === "#play") play();
};
if (document.fonts) document.fonts.ready.then(boot); else boot();
}

if (typeof document !== "undefined") {
  if (window.TIMELINE) startPlayer(); else markContents();
}
