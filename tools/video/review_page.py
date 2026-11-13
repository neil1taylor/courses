"""The HTML of the review page: a course page, one page per module, and the outline page.

All script text is escaped. The pages load nothing from outside the server.
"""
from html import escape

import review_state as rs
import script as scripts

STYLE = """
:root{color-scheme:dark;--bg:#111216;--card:#1b1d24;--line:#2d303a;--ink:#e9e9ef;--muted:#9a9ca8;--mark:#6f9bff;--ok:#5ec27f;--warn:#f0b35a;--bad:#ff7b7b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "Red Hat Text",Arial,sans-serif;padding:24px 16px 80px}
main{max-width:1100px;margin:0 auto}
h1{font-family:"Red Hat Display",Arial,sans-serif;font-weight:800;font-size:30px;margin:8px 0 16px}
a{color:var(--mark)}
.nav{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:8px;font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.problems{border-color:var(--bad)}.problems h2{color:var(--bad);margin:0 0 6px;font-size:18px}
.notes h2{color:var(--warn);margin:0 0 6px;font-size:18px}
.cue{display:grid;grid-template-columns:70px 1fr 480px;gap:16px;align-items:start}
.cue.noslide{grid-template-columns:70px 1fr}
.ref{font-family:"Red Hat Mono",monospace;color:var(--mark);font-weight:700}
.say{margin:0 0 6px}
iframe{width:480px;height:270px;border:1px solid var(--line);border-radius:6px;background:#fff;max-width:100%}
.changed{display:inline-block;background:var(--warn);color:#111;border-radius:4px;padding:0 8px;font-size:13px;font-weight:700}
.teach{color:var(--muted);font-size:14px;border-left:3px solid var(--mark);padding-left:10px;margin:6px 0}
.comment{background:#262935;border-radius:6px;padding:6px 10px;margin:6px 0;font-size:14px}
.comment q{color:var(--muted)}
textarea{width:100%;background:#0e0f13;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px;font:inherit}
button{background:var(--mark);color:#0b0b0f;border:0;border-radius:6px;padding:6px 14px;font:inherit;font-weight:700;cursor:pointer}
button.quiet{background:#2d303a;color:var(--ink)}
.status{font-weight:700}.s-approved{color:var(--ok)}.s-changed{color:var(--warn)}.s-open{color:var(--bad)}.s-new{color:var(--muted)}
table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid var(--line);text-align:left}
.foot{display:flex;gap:12px;margin-top:24px;flex-wrap:wrap}
.right{font-weight:700;color:var(--ok)}
@media(max-width:900px){.cue{grid-template-columns:1fr}}
.para{font-size:19px;line-height:1.75;margin:0}
.para .s{cursor:pointer;border-radius:4px;padding:1px 2px}
.para .s:hover{background:#262935}
.para .s.sel{outline:2px solid var(--mark)}
.para sup{font-family:"Red Hat Mono",monospace;color:var(--muted);font-size:11px;margin-right:2px}
.para .has-comment sup{color:var(--bad)}
.picked{color:var(--muted);font-size:14px;margin:6px 0}
"""

SCRIPT = """
function post(url, body) {
  return fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})
    .then(r => r.json().then(j => { if (!r.ok) alert(j.error || "Failed"); else location.reload(); }));
}
document.addEventListener("click", e => {
  const b = e.target.closest("button[data-act]"); if (!b) return;
  if (b.dataset.act === "comment") {
    const box = b.parentElement.querySelector("textarea"); const text = box.value.trim(); if (!text) return;
    post("/api/comment", {ref: b.dataset.ref, say: b.dataset.say, text});
  } else post("/api/" + b.dataset.act, {stem: b.dataset.stem});
});
"""

STATUS_CLASS = {"Approved": "s-approved", "Changed since approved": "s-changed",
                "Has open comments": "s-open", "Not reviewed": "s-new"}


def _page(title, body) -> str:
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>%s</title><style>%s</style></head><body><main>%s</main><script>%s</script></body></html>"
            % (escape(title), STYLE, body, SCRIPT))


def _comment_box(ref, say) -> str:
    return ('<div><textarea rows="2" placeholder="Comment on this sentence" aria-label="Comment"></textarea>'
            '<button class="quiet" data-act="comment" data-ref="%s" data-say="%s">Comment</button></div>'
            % (escape(ref, quote=True), escape(say, quote=True)))


def _comment_html(c) -> str:
    return '<div class="comment"><q>%s</q><br>%s <small>(#%d)</small></div>' % (
        escape(c.get("say", "")), escape(c["text"]), c["id"])


def render_course(slug, title, letter, rows, general_problems=()) -> str:
    """rows: [(stem, number, module title, status)]."""
    out = ["<h1>%s: review</h1>" % escape(title), '<p class="nav"><a href="/outline">Course outline</a></p>']
    if general_problems:
        out.append('<div class="card problems"><h2>Problems</h2><ul>%s</ul></div>'
                   % "".join("<li>%s</li>" % escape(p) for p in general_problems))
    out.append("<table><tr><th>Module</th><th>Title</th><th>Status</th></tr>")
    for stem, number, mtitle, status in rows:
        out.append('<tr><td>%s %d</td><td><a href="/m/%s">%s</a></td><td class="status %s">%s</td></tr>'
                   % (letter, number, escape(stem, quote=True), escape(mtitle), STATUS_CLASS[status], status))
    out.append("</table>")
    return _page(title + " review", "".join(out))


def render_module(slug, letter, number, stem, script, problems, note_lines, state) -> str:
    cue_refs = rs.refs(script, letter, number)
    by_pos = {(r["step"], r["cue"]): r for r in cue_refs}
    status = rs.module_status(state, stem, script, letter, number)
    changed = rs.changed_refs(state, stem, script, letter, number)
    attached, orphans = rs.attach_comments([c for c in state["comments"] if rs.module_number(c["ref"]) == number
                                            and c["ref"].startswith(letter + " ")], cue_refs)
    title = script.get("title", stem) if isinstance(script, dict) else stem
    out = ['<p class="nav"><a href="/">All modules</a><a href="/m/%s/narration">Narration</a>'
           '<a href="/outline">Course outline</a></p>' % escape(stem, quote=True),
           '<h1>%s %d: %s</h1>' % (letter, number, escape(str(title))),
           '<p>Status: <span class="status %s">%s</span></p>' % (STATUS_CLASS[status], status)]
    if problems:
        out.append('<div class="card problems"><h2>This script has problems</h2><ul>%s</ul></div>'
                   % "".join("<li>%s</li>" % escape(p) for p in problems))
    if note_lines:
        out.append('<div class="card notes"><h2>Notes for the reader</h2><ul>%s</ul></div>'
                   % "".join("<li>%s</li>" % escape(n) for n in note_lines))
    if orphans:
        out.append('<div class="card"><h2>Comments on a sentence that is no longer there</h2>%s</div>'
                   % "".join(_comment_html(c) for c in orphans))
    still = "/%s/video/%s.html" % (slug, stem)
    for r in cue_refs:
        cue, slide = r["data"], r["data"].get("slide")
        has_visual = bool(slide) or bool(cue.get("do"))
        parts = ['<div class="card cue%s">' % ("" if has_visual else " noslide"),
                 '<div class="ref">%s</div><div><p class="say">%s</p>' % (escape(r["ref"]), escape(r["say"]))]
        if r["ref"] in changed:
            parts.append('<span class="changed">Changed</span>')
        if isinstance(slide, dict) and slide.get("type") == "q":
            t = scripts.teaching_cue(script, r["step"], r["cue"])
            if t and t in by_pos:
                parts.append('<div class="teach">Teaches this: %s &ldquo;%s&rdquo;</div>'
                             % (escape(by_pos[t]["ref"]), escape(by_pos[t]["say"])))
            else:
                parts.append('<div class="teach">No earlier sentence in this module teaches this answer.</div>')
            try:
                opts = [str(o) for o in slide["opts"]]
                parts.append("<ul>%s</ul>" % "".join(
                    '<li%s>%s</li>' % (' class="right"' if i == slide["ok"] else "", escape(o))
                    for i, o in enumerate(opts)))
            except (KeyError, TypeError):
                pass
        for c in attached.get(r["ref"], []):
            parts.append(_comment_html(c))
        parts.append(_comment_box(r["ref"], r["say"]))
        parts.append("</div>")
        if has_visual:
            parts.append('<iframe src="%s?still=%d.%d" loading="lazy" width="480" height="270" title="Slide for %s"></iframe>'
                         % (escape(still, quote=True), r["step"], r["cue"], escape(r["ref"], quote=True)))
        parts.append("</div>")
        out.append("".join(parts))
    s = escape(stem, quote=True)
    out.append('<div class="foot"><button data-act="approve" data-stem="%s">Approve module</button>'
               '<button class="quiet" data-act="seen" data-stem="%s">Mark as read</button></div>' % (s, s))
    return _page("%s %d" % (letter, number), "".join(out))


PICK = """
const box = document.querySelector("#box button"), picked = document.querySelector("#picked");
document.querySelectorAll(".para .s").forEach(s => {
  s.addEventListener("click", () => {
    document.querySelectorAll(".para .s").forEach(x => x.classList.remove("sel")); s.classList.add("sel");
    box.dataset.ref = s.dataset.ref; box.dataset.say = s.dataset.say; picked.textContent = "Comment on " + s.dataset.ref;
  });
});
"""


def render_narration(slug, letter, number, stem, script, state) -> str:
    """The module's narration as continuous text, one paragraph per step. Read only: click a sentence to comment
    on it. The wording is changed in the module's text file."""
    cue_refs = rs.refs(script, letter, number)
    attached, _ = rs.attach_comments([c for c in state["comments"] if rs.module_number(c["ref"]) == number
                                      and c["ref"].startswith(letter + " ")], cue_refs)
    title = script.get("title", stem) if isinstance(script, dict) else stem
    s = escape(stem, quote=True)
    out = ['<p class="nav"><a href="/">All modules</a><a href="/m/%s">Sentences and slides</a></p>' % s,
           '<h1>%s %d: %s</h1>' % (letter, number, escape(str(title))),
           "<p class=\"picked\">To change the wording, edit this module's text file: "
           "review/%s/%02d-%s.txt in the courses folder.</p>" % (escape(slug), number, escape(stem))]
    steps = script.get("steps", []) if isinstance(script, dict) else []
    for si, step in enumerate(steps, 1):
        spans = []
        for r in (r for r in cue_refs if r["step"] == si):
            cls = "s" + (" has-comment" if attached.get(r["ref"]) else "")
            spans.append('<span class="%s" data-ref="%s" data-say="%s"><sup>%s</sup>%s</span>'
                         % (cls, escape(r["ref"], quote=True), escape(r["say"], quote=True),
                            escape(r["ref"].split(" ")[1]), escape(r["say"])))
        out.append('<div class="card"><h2>%s</h2><p class="para">%s</p>%s</div>' % (
            escape(str(step.get("title", "Step %d" % si))), " ".join(spans),
            "".join(_comment_html(c) for r in cue_refs if r["step"] == si for c in attached.get(r["ref"], []))))
    out.append('<div class="card" id="box"><p class="picked" id="picked">Click a sentence, then comment on it here.</p>%s</div>'
               % _comment_box("", ""))
    return _page("%s %d narration" % (letter, number), "".join(out)).replace(
        "</script></body>", PICK + "</script></body>")


def render_outline(slug, letter, outline, numbers, problems, state) -> str:
    """outline: the loaded outline.json or None. numbers: {unit stem: module number}."""
    out = ['<p class="nav"><a href="/">All modules</a></p>', "<h1>Course outline</h1>"]
    if outline is None:
        out.append("<p>No outline yet.</p>")
        return _page("Outline", "".join(out))
    if problems:
        out.append('<div class="card problems"><h2>The outline has problems</h2><ul>%s</ul></div>'
                   % "".join("<li>%s</li>" % escape(p) for p in problems))
    for n, m in enumerate(outline.get("modules", []), 1):
        stem = m.get("unit", "")
        number = numbers.get(stem, n)
        ref = "%s %d.0" % (letter, number)
        approved = state["outline"].get(stem, {}).get("approved")
        current = rs.outline_hash(m)
        status = ("Approved" if approved == current else "Changed since approved" if approved else "Not reviewed")
        out.append('<div class="card"><h2>%s %d: %s</h2><p>Status: <span class="status %s">%s</span></p>'
                   % (letter, number, escape(str(m.get("title", stem))), STATUS_CLASS[status], status))
        out.append("<h3>Outcomes</h3><ul>%s</ul>" % "".join("<li>%s</li>" % escape(str(o)) for o in m.get("outcomes", [])))
        out.append("<h3>Facts</h3><ul>%s</ul>" % "".join(
            "<li>%s <small>(source: %s)</small></li>" % (escape(str(f.get("text", ""))), escape(str(f.get("source", ""))))
            for f in m.get("facts", [])))
        out.append("<h3>Checks</h3>")
        for c in m.get("checks", []):
            out.append("<p>%s</p><ul>%s</ul>" % (escape(str(c.get("head", ""))), "".join(
                '<li%s>%s</li>' % (' class="right"' if i == c.get("ok") else "", escape(str(o)))
                for i, o in enumerate(c.get("opts", [])))))
        for c in state["comments"]:
            if c["open"] and c["ref"] == ref:
                out.append(_comment_html(c))
        out.append(_comment_box(ref, ""))
        out.append('<div class="foot"><button data-act="approve-outline" data-stem="%s">Approve outline for this module</button></div></div>'
                   % escape(stem, quote=True))
    return _page("Outline", "".join(out))
