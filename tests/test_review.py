import copy
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "video"))

import review_state as rs  # noqa: E402
import review_page as rp  # noqa: E402

GOOD = json.loads((ROOT / "tests" / "fixtures" / "good.json").read_text())


def changed(say_from="Everything in this course was tested on a real vault.", to="Everything here was tested on a real vault."):
    s = copy.deepcopy(GOOD)
    for step in s["steps"]:
        for cue in step["cues"]:
            if cue["say"] == say_from:
                cue["say"] = to
    return s


def test_state_round_trip(tmp_path):
    path = tmp_path / "review" / "vault.json"
    assert rs.load_state(path) == {"modules": {}, "comments": [], "outline": {}, "edits": []}
    state = rs.load_state(path)
    rs.add_comment(state, "V 1.2", "A sentence.", "Too long")
    rs.approve(state, "m0", GOOD, "V", 1)
    rs.save_state(path, state)
    assert rs.load_state(path) == state


def test_save_is_atomic(tmp_path, monkeypatch):
    path = tmp_path / "vault.json"
    rs.save_state(path, {"modules": {}, "comments": [], "outline": {}})
    seen = []
    real = os.replace

    def spy(src, dst):
        seen.append((Path(src), Path(dst), json.loads(Path(src).read_text()), json.loads(Path(dst).read_text())))
        real(src, dst)

    monkeypatch.setattr(rs.os, "replace", spy)
    new = {"modules": {}, "comments": [{"id": 1, "ref": "V 1.1", "text": "x", "open": True}], "outline": {}}
    rs.save_state(path, new)
    src, dst, written, before = seen[0]
    assert src != dst and src.parent == dst.parent
    assert written == new and before["comments"] == []
    assert json.loads(path.read_text()) == new


def test_hashes_stable_and_sensitive():
    a, b = GOOD["steps"][0]["cues"][0], copy.deepcopy(GOOD["steps"][0]["cues"][0])
    assert rs.cue_hash(a) == rs.cue_hash(b) and len(rs.cue_hash(a)) == 12
    b["say"] = b["say"][:-1] + "!"
    assert rs.cue_hash(a) != rs.cue_hash(b)
    assert rs.module_hash(GOOD) == rs.module_hash(copy.deepcopy(GOOD))
    assert rs.module_hash(GOOD) != rs.module_hash(changed())


def test_refs_number_cues_across_steps():
    refs = rs.refs(GOOD, "V", 13)
    assert refs[0]["ref"] == "V 13.1" and refs[1]["ref"] == "V 13.2"
    assert refs[2]["ref"] == "V 13.3" and refs[2]["step"] == 2 and refs[2]["cue"] == 1
    assert len({r["ref"] for r in refs}) == len(refs)


def test_status_four_states():
    state = rs.load_state(Path("/nonexistent/x.json"))
    assert rs.module_status(state, "m", GOOD, "V", 1) == "Not reviewed"
    rs.add_comment(state, "V 1.1", "s", "c")
    assert rs.module_status(state, "m", GOOD, "V", 1) == "Has open comments"
    state["comments"][0]["open"] = False
    rs.approve(state, "m", GOOD, "V", 1)
    assert rs.module_status(state, "m", GOOD, "V", 1) == "Approved"
    assert rs.module_status(state, "m", changed(), "V", 1) == "Changed since approved"


def test_only_the_changed_sentence_is_marked():
    state = rs.load_state(Path("/nonexistent/x.json"))
    rs.approve(state, "m", GOOD, "V", 1)
    new = changed()
    marked = rs.changed_refs(state, "m", new, "V", 1)
    assert marked == {"V 1.2"}
    assert rs.changed_refs(state, "m", GOOD, "V", 1) == set()


def test_mark_read_updates_seen_without_approving():
    state = rs.load_state(Path("/nonexistent/x.json"))
    rs.mark_seen(state, "m", GOOD, "V", 1)
    assert state["modules"]["m"]["approved"] is None
    assert rs.changed_refs(state, "m", changed(), "V", 1) == {"V 1.2"}


def test_comment_follows_its_sentence_when_cue_moves():
    state = rs.load_state(Path("/nonexistent/x.json"))
    say = GOOD["steps"][0]["cues"][1]["say"]
    rs.add_comment(state, "V 1.2", say, "Say it shorter")
    moved = copy.deepcopy(GOOD)
    first = moved["steps"][0]["cues"]
    first.insert(0, {"say": "A new opening sentence."})
    refs = rs.refs(moved, "V", 1)
    attached, orphans = rs.attach_comments(state["comments"], refs)
    assert [c["text"] for c in attached["V 1.3"]] == ["Say it shorter"]
    assert orphans == []


def test_comment_on_deleted_sentence_is_listed_apart():
    state = rs.load_state(Path("/nonexistent/x.json"))
    rs.add_comment(state, "V 1.2", "A sentence that is gone.", "Hm")
    attached, orphans = rs.attach_comments(state["comments"], rs.refs(GOOD, "V", 1))
    assert not attached and [c["text"] for c in orphans] == ["Hm"]


def test_comments_report_and_close():
    state = rs.load_state(Path("/nonexistent/x.json"))
    i = rs.add_comment(state, "V 13.3", "Here's how.", "Fix this")
    j = rs.add_comment(state, "V 13.4", "Other.", "And this")
    assert rs.comments_report(state) == ['V 13.3  "Here\'s how."  Fix this', 'V 13.4  "Other."  And this']
    rs.close_comments(state, [i])
    assert rs.comments_report(state) == ['V 13.4  "Other."  And this']
    assert j == i + 1


def page(script=GOOD, problems=(), state=None):
    state = state or rs.load_state(Path("/nonexistent/x.json"))
    return rp.render_module("vault", "V", 13, "m3-u4", script, list(problems), ["step 1 cue 1: first mention of 'the read key'"],
                            state)


def test_module_page_has_ref_still_iframe_and_teaching_ref():
    html = page()
    assert "V 13.1" in html
    assert 'src="/vault/video/m3-u4.html?still=1.1"' in html
    assert 'loading="lazy"' in html and 'width="480"' in html and 'height="270"' in html
    # the first question's teaching sentence is the read-key line; it is shown with its ref
    cues = rs.refs(GOOD, "V", 13)
    q = next(r for r in cues if r["data"].get("slide", {}).get("type") == "q")
    assert "Teaches this: V 13." in html
    assert "first mention of" in html


def test_module_page_escapes_script_text():
    s = copy.deepcopy(GOOD)
    s["steps"][0]["cues"][1]["say"] = "Use <script>alert(1)</script> here."
    html = page(s)
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)" in html


def test_module_page_lists_problems_for_a_bad_script():
    bad = copy.deepcopy(GOOD)
    del bad["steps"][1]["cues"]
    html = page(bad, ["step 2 cue 0: step has no cues"])
    assert "step 2 cue 0: step has no cues" in html
    assert html.index("step 2 cue 0") < html.index("V 13.1")


def test_module_page_marks_changed_and_shows_comment_with_sentence():
    state = rs.load_state(Path("/nonexistent/x.json"))
    rs.approve(state, "m3-u4", GOOD, "V", 13)
    rs.add_comment(state, "V 13.2", GOOD["steps"][0]["cues"][1]["say"], "Too vague")
    html = page(changed(), state=state)
    assert html.count('class="changed"') == 1
    assert "Too vague" in html and "Everything in this course was tested" in html


# ---- the server -----------------------------------------------------------------------------------

import threading  # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

import review  # noqa: E402
from test_build_video import make_source  # noqa: E402


def start(tmp_path, scripts):
    video = make_source(tmp_path, scripts)
    r = review.Review("demo", {"title": "Demo course", "source": video, "live": False},
                      tmp_path / "out", tmp_path / "rev" / "demo.json", letter="V")
    server = ThreadingHTTPServer(("127.0.0.1", 0), review.make_handler(r))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return r, server, "http://127.0.0.1:%d" % server.server_address[1]


def get(url):
    return urllib.request.urlopen(url).read().decode()


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def test_server_lists_modules_and_saves_across_restart(tmp_path):
    r, server, base = start(tmp_path, {"a": dict(GOOD, unit="a.html")})
    try:
        assert "Not reviewed" in get(base + "/")
        post(base + "/api/comment", {"ref": "V 1.1", "say": "Welcome.", "text": "Warmer"})
        post(base + "/api/approve", {"stem": "a"})
        assert "No outline yet" in get(base + "/outline")
        assert "?still=1.1" in get(base + "/m/a")
        assert "/demo/video/a.html" in get(base + "/m/a")
        assert "player.js" in get(base + "/demo/video/a.html")
    finally:
        server.shutdown()
        server.server_close()
    again = review.Review("demo", r.cfg, tmp_path / "out", tmp_path / "rev" / "demo.json", letter="V")
    st = again.state()
    assert st["comments"][0]["text"] == "Warmer" and st["modules"]["a"]["approved"]


def test_server_opens_a_script_with_problems_and_refuses_to_approve_it(tmp_path):
    bad = dict(GOOD, unit="a.html")
    bad["steps"] = [dict(bad["steps"][0], title="x"), {"title": "empty", "cues": []}] + bad["steps"][1:]
    r, server, base = start(tmp_path, {"a": bad})
    try:
        html = get(base + "/m/a")
        assert "This script has problems" in html and "step has no cues" in html
        req = urllib.request.Request(base + "/api/approve", json.dumps({"stem": "a"}).encode(),
                                     {"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 400
    finally:
        server.shutdown()
        server.server_close()


def narration(script=GOOD, state=None):
    state = state or rs.load_state(Path("/nonexistent/x.json"))
    return rp.render_narration("vault", "V", 13, "m3-u4", script, state)


def test_narration_view_is_one_paragraph_per_step_with_refs():
    html = narration()
    for step in GOOD["steps"]:
        assert ">%s</h2>" % step["title"] in html
    assert html.count("<p class=\"para\"") == len(GOOD["steps"])
    first = GOOD["steps"][0]["cues"][0]["say"]
    assert 'data-ref="V 13.1"' in html and first in html
    assert 'href="/m/m3-u4"' in html  # back to the sentence view


def test_narration_view_is_editable_and_has_no_speech():
    html = narration()
    assert 'contenteditable="plaintext-only"' in html
    assert "speechSynthesis" not in html and 'id="listen"' not in html
    assert 'data-act="comment"' in html and "/api/edit" in html


def test_narration_view_shows_a_pending_edit_in_place_of_the_sentence():
    st = rs.load_state(Path("/nonexistent/x.json"))
    first = GOOD["steps"][0]["cues"][0]["say"]
    rs.add_edit(st, "m3-u4", "V 13.1", first, "A warmer opening.")
    html = narration(state=st)
    assert "A warmer opening." in html and 'class="s edited"' in html
    assert 'data-say="%s"' % first in html  # the original, so a second edit still finds the cue


def test_edits_replace_report_and_apply():
    st = rs.empty_state()
    first = GOOD["steps"][0]["cues"][0]["say"]
    i = rs.add_edit(st, "m3-u4", "V 13.1", first, "Draft one.")
    assert rs.add_edit(st, "m3-u4", "V 13.1", first, "Draft two.") == i  # one open edit per sentence
    rs.add_edit(st, "m3-u4", "V 13.9", "Not in the script any more.", "Whatever.")
    assert rs.edits_report(st)[0] == 'V 13.1  "%s"  ->  "Draft two."' % first
    s = copy.deepcopy(GOOD)
    applied, skipped = rs.apply_edits(st, "m3-u4", s)
    assert s["steps"][0]["cues"][0]["say"] == "Draft two."
    assert len(applied) == 1 and len(skipped) == 1
    assert [e["open"] for e in st["edits"]] == [False, True]


def test_open_edit_counts_as_open_work_in_the_status():
    st = rs.empty_state()
    rs.add_edit(st, "m3-u4", "V 13.1", GOOD["steps"][0]["cues"][0]["say"], "New.")
    assert rs.module_status(st, "m3-u4", GOOD, "V", 13) == "Has open comments"


def test_narration_view_escapes_script_text():
    s = copy.deepcopy(GOOD)
    s["steps"][0]["cues"][0]["say"] = "Use <b>bold</b> here."
    html = narration(s)
    assert "<b>bold</b>" not in html and "&lt;b&gt;bold&lt;/b&gt;" in html


def test_module_page_links_to_its_narration_view():
    assert 'href="/m/m3-u4/narration"' in page()


def test_server_serves_the_narration_view(tmp_path):
    r, server, base = start(tmp_path, {"a": dict(GOOD, unit="a.html")})
    try:
        assert 'contenteditable="plaintext-only"' in get(base + "/m/a/narration")
    finally:
        server.shutdown()
        server.server_close()


def test_server_saves_an_edit_only_for_a_real_sentence(tmp_path):
    r, server, base = start(tmp_path, {"a": dict(GOOD, unit="a.html")})
    first = GOOD["steps"][0]["cues"][0]["say"]
    try:
        assert post(base + "/api/edit", {"stem": "a", "ref": "V 1.1", "old": first, "new": "Better."})["id"] == 1
        with pytest.raises(urllib.error.HTTPError):
            post(base + "/api/edit", {"stem": "a", "ref": "V 1.1", "old": "No such sentence.", "new": "x"})
    finally:
        server.shutdown()
        server.server_close()
    assert r.state()["edits"][0]["new"] == "Better."
