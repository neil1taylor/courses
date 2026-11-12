import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const P = require("../player.js");

const cue = (dur, extra = {}) => ({ say: "x", dur, audio: "a.mp3", ...extra });
const q = (id, check) => ({ slide: { type: "q", head: id, opts: ["a", "b"], ok: 1, why: "w", check }, say: "q", do: [["ask"]], dur: 1 });
const timeline = {
  steps: [
    { title: "One", cues: [cue(1.84), cue(0.92, { hold: 1 })] },
    { title: "Two", cues: [q("q1", true), q("q2", true), q("q3", false), cue(0.92)] },
  ],
};

test("cueAt finds the step and cue at a time", () => {
  // len = dur / 0.92 + 0.8 + hold: 2.8, 2.8, then 1.8 + ...
  assert.deepEqual(P.cueAt(timeline, 0), { step: 0, cue: 0 });
  assert.deepEqual(P.cueAt(timeline, 2.79), { step: 0, cue: 0 });
  assert.deepEqual(P.cueAt(timeline, 2.81), { step: 0, cue: 1 });
  assert.deepEqual(P.cueAt(timeline, 5.7), { step: 1, cue: 0 });
});

test("cueAt clamps before the start and past the end", () => {
  assert.deepEqual(P.cueAt(timeline, -5), { step: 0, cue: 0 });
  assert.deepEqual(P.cueAt(timeline, 9999), { step: 1, cue: 3 });
});

test("scoreOf counts only check questions", () => {
  const answers = new Map([["1:0", { pick: 1 }], ["1:1", { pick: 0 }], ["1:2", { pick: 1 }]]);
  assert.deepEqual(P.scoreOf(answers, timeline), { right: 1, total: 2, answered: 2 });
});

test("scoreOf counts a question once after the answer is changed by a seek", () => {
  const answers = new Map();
  answers.set("1:0", { pick: 0 });
  answers.set("1:0", { pick: 1 });
  assert.deepEqual(P.scoreOf(answers, timeline), { right: 1, total: 2, answered: 1 });
});

test("scoreOf ignores answers for slides that are not check questions", () => {
  const answers = { "0:0": { pick: 1 }, "9:9": { pick: 1 } };
  assert.deepEqual(P.scoreOf(answers, timeline), { right: 0, total: 2, answered: 0 });
});

test("progressKey is courses-video:<slug>", () => {
  assert.equal(P.progressKey("cyber-vault"), "courses-video:cyber-vault");
});

function memory() {
  const m = new Map();
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)) };
}

test("markDone then doneModules returns the module, once", () => {
  const s = memory();
  P.markDone(s, "cyber-vault", 3);
  P.markDone(s, "cyber-vault", 3);
  P.markDone(s, "cyber-vault", 1);
  assert.deepEqual(P.doneModules(s, "cyber-vault"), [1, 3]);
  assert.deepEqual(P.doneModules(s, "other"), []);
});

test("both survive storage that throws", () => {
  const bad = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("full"); } };
  assert.doesNotThrow(() => P.markDone(bad, "x", 1));
  assert.deepEqual(P.doneModules(bad, "x"), []);
});

test("doneModules survives stored text that is not a list", () => {
  const s = memory();
  s.setItem("courses-video:x", "{not json");
  assert.deepEqual(P.doneModules(s, "x"), []);
  assert.doesNotThrow(() => P.markDone(s, "x", 2));
  assert.deepEqual(P.doneModules(s, "x"), [2]);
});

test("summary text is escaped, only <em> stays", () => {
  assert.equal(P.summaryHtml("a <img onerror=x> b"), "a &lt;img onerror=x&gt; b");
  assert.equal(P.summaryHtml("the <em>key</em> words"), "the <em>key</em> words");
  assert.ok(!P.summaryHtml("<em onclick=x>k</em>").includes("<em onclick"));
});

test("esc is safe inside a quoted attribute", () => {
  const html = '<img src="' + P.esc("a\"b'c>d<e&f") + '">';
  assert.equal(html, '<img src="a&quot;b&#39;c&gt;d&lt;e&amp;f">');
  assert.equal(html.split('"').length, 3);
});

test("reaching an ask cue clears the earlier answer, and the score uses the new one once", () => {
  let answers = new Map([["1:0", { pick: 1 }], ["1:1", { pick: 1 }]]);
  assert.deepEqual(P.scoreOf(answers, timeline), { right: 2, total: 2, answered: 2 });
  // seek back before the question: nothing is cleared yet
  answers = P.answersAfterReaching(answers, timeline, 0, 0);
  assert.equal(answers.size, 2);
  // seek to or play forward to a cue after the ask (the why cue) would not be an ask cue; reaching the ask cue clears it
  answers = P.answersAfterReaching(answers, timeline, 1, 0);
  assert.deepEqual(P.scoreOf(answers, timeline), { right: 1, total: 2, answered: 1 });
  answers.set("1:0", { pick: 0 });
  assert.deepEqual(P.scoreOf(answers, timeline), { right: 1, total: 2, answered: 2 });
  answers.set("1:0", { pick: 1 });
  answers.set("1:0", { pick: 0 });
  assert.deepEqual(P.scoreOf(answers, timeline), { right: 1, total: 2, answered: 2 });
});

test("reaching a cue with no ask leaves answers alone, and the input is not changed", () => {
  const answers = new Map([["1:0", { pick: 1 }]]);
  const out = P.answersAfterReaching(answers, timeline, 1, 3);
  assert.equal(out.size, 1);
  P.answersAfterReaching(answers, timeline, 1, 0);
  assert.equal(answers.size, 1);
});

test("a small box at scale below 1 grows so floored labels fit", () => {
  const scale = 0.5;
  const L = P.boxLayout([10, 10, 100, 40], "vault", null, scale);
  assert.equal(L.tf, 72);
  assert.ok(L.h >= L.tf * 1.3, "single line box tall enough");
  assert.ok(L.w >= "vault".length * L.tf * 0.55, "wide enough for the title");
  const two = P.boxLayout([10, 10, 100, 60], "vault", "locked", scale);
  assert.ok(two.two);
  assert.ok(two.detailY + two.df * 0.3 <= two.y + two.h, "detail line inside the box");
});

test("at scale 2 nothing changes: sizes stay at the unit sizes and the box keeps its size", () => {
  const L = P.boxLayout([0, 0, 190, 64], "backup", "x", 2);
  assert.equal(L.tf, 21);
  assert.equal(L.h, 64);
  assert.equal(L.w, 190);
});
