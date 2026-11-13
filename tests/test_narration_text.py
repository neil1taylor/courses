import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "video"))

import narration_text as nt  # noqa: E402

GOOD = json.loads((ROOT / "tests" / "fixtures" / "good.json").read_text())


def cues(script):
    return [c for step in script["steps"] for c in step["cues"]]


def test_export_has_heading_step_headings_and_tags():
    text = nt.export_text(GOOD, "V", 13)
    lines = text.splitlines()
    assert lines[0] == "# V 13: %s" % GOOD["title"]
    assert lines[1].startswith("# Change the words after a tag.")
    for step in GOOD["steps"]:
        assert "## %s" % step["title"] in lines
    for n, c in enumerate(cues(GOOD), 1):
        assert "[13.%d] %s" % (n, c["say"]) in lines
    assert "\n\n## " in text  # a blank line between steps


def test_round_trip_changes_nothing():
    says, comments, problems = nt.parse_text(nt.export_text(GOOD, "V", 13))
    assert problems == [] and comments == {}
    script = copy.deepcopy(GOOD)
    assert nt.apply_text(script, "V", 13, says) == ([], [])
    assert script == GOOD


def test_an_edited_line_changes_only_that_cue():
    text = nt.export_text(GOOD, "V", 13).replace("[13.2] ", "[13.2] Edited:   ")
    says, _, problems = nt.parse_text(text)
    script = copy.deepcopy(GOOD)
    changed, apply_problems = nt.apply_text(script, "V", 13, says)
    assert problems == [] and apply_problems == []
    assert changed == ["V 13.2"]
    assert cues(script)[1]["say"].startswith("Edited: ")
    assert [c["say"] for i, c in enumerate(cues(script)) if i != 1] == [c["say"] for i, c in enumerate(cues(GOOD)) if i != 1]


def test_a_comment_attaches_to_the_sentence_above_it():
    lines = nt.export_text(GOOD, "V", 13).splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("[13.1]"))
    lines.insert(i + 1, "> Say it more plainly.")
    _, comments, problems = nt.parse_text("\n".join(lines))
    assert problems == [] and comments == {1: ["Say it more plainly."]}


def test_comment_before_any_sentence_is_a_problem():
    _, _, problems = nt.parse_text("# V 13: T\n> early\n[13.1] Hello.\n")
    assert any("line 2" in p for p in problems)


def test_stray_line_is_a_problem_naming_the_line_and_previous_tag():
    _, _, problems = nt.parse_text("# V 13: T\n[13.4] Hello.\nand more words\n")
    assert problems == ["line 3: no tag at the start; was this line meant to be part of [13.4]?"]


def test_duplicate_tag_wrong_module_and_empty_text_are_problems():
    text = "# V 13: T\n[13.1] A.\n[13.1] B.\n[12.2] C.\n[13.3]   \n"
    says, _, problems = nt.parse_text(text)
    assert len(problems) == 3
    assert any("13.1" in p and "twice" in p for p in problems)
    assert any("12.2" in p for p in problems)
    assert any("13.3" in p and "empty" in p for p in problems)
    assert says == {1: "A."}


def test_apply_reports_missing_and_unknown_tags_and_leaves_cues_alone():
    script = copy.deepcopy(GOOD)
    total = len(cues(script))
    says = {n: c["say"] for n, c in enumerate(cues(GOOD), 1)}
    del says[total]
    says[total + 5] = "Nowhere."
    changed, problems = nt.apply_text(script, "V", 13, says)
    assert changed == [] and script == GOOD
    assert "[13.%d] is missing from the file; the sentence was left as it was" % total in problems
    assert any("[13.%d]" % (total + 5) in p for p in problems)
