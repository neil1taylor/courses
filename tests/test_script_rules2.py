"""Rules for scripts that say "rules": 2, written after the owner's review of the VPN course.
Older scripts (no "rules" key) are checked as before."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "video"))

import script  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
UNIT = (FIX / "unit.html").read_text()


def good2():
    s = json.loads((FIX / "good.json").read_text())
    s["rules"] = 2
    step1 = s["steps"][0]["cues"]
    step1.append({
        "say": "By the end of this module, you'll be able to explain the vault.",
        "slide": {"type": "list", "head": "In this module", "items": ["Explain the vault"]},
        "do": [["show", "head"], ["items", [0]]],
    })
    s["steps"][2]["cues"][0]["slide"]["head"] = "Terms used in this module"
    # teach each question's answer before it is asked
    s["steps"][1]["cues"].append({"say": "Keep the read key apart from the backup system, so one attacker cannot reach both."})
    s["steps"][1]["cues"].append({"say": "The object lock stops deletion before the date, and the cluster holds the write key."})
    s["steps"][4]["cues"][0]["slide"]["opts"][2] = "With the cluster"
    s["steps"][4]["cues"][4]["slide"]["opts"][2] = "The lock"
    sm = s["steps"][5]["cues"][1]
    sm["say"] = "One copy stays safe. If you remember one thing, it is this: a vault keeps one copy safe. Next, building the vault."
    return s


def run(fn=None, first_module=True):
    s = good2()
    if fn:
        fn(s)
    return script.check_script(s, UNIT, first_module)


def cue(s, st, c):
    return s["steps"][st - 1]["cues"][c - 1]


def has(problems, *needles):
    assert any(all(n in p for n in needles) for p in problems), problems


def test_good2_is_clean():
    assert run() == []


def test_old_scripts_are_not_held_to_the_new_rules():
    s = json.loads((FIX / "good.json").read_text())
    assert script.check_script(s, UNIT, True) == []


def test_words_slide_head_is_terms_used_in_this_module():
    def f(s):
        s["steps"][2]["cues"][0]["slide"]["head"] = "Four words used in this module"
    has(run(f), "step 3 cue 1", "Terms used in this module")


def test_quiz_opener_is_module_quiz():
    def f(s):
        s["steps"][4]["cues"].insert(0, {"say": "Now, three quick questions.", "slide": {"type": "statement", "head": "Three quick questions"}, "do": [["show", "head"]]})
    has(run(f), "step 5 cue 1", "Module quiz")


def test_summary_may_not_point_at_the_screen():
    def f(s):
        cue(s, 6, 2)["say"] = "One copy stays safe. If you remember one thing, make it the sentence on the screen. Next, building the vault."
    has(run(f), "step 6 cue 2", "on the screen")


def test_summary_must_say_its_sentence():
    def f(s):
        cue(s, 6, 2)["say"] = "One copy stays safe. Next, building the vault."
    has(run(f), "step 6", "summary sentence")


def test_summary_sentence_spoken_is_not_flagged_as_narration_on_screen():
    assert not any("narration on screen" in p for p in run())


def test_step_one_needs_a_list_slide():
    def f(s):
        s["steps"][0]["cues"].pop()
    has(run(f), "step 1", "list slide")


def test_list_items_must_all_be_revealed():
    def f(s):
        s["steps"][0]["cues"][-1]["slide"]["items"].append("Name the parts")
    has(run(f), "step 1", "item 1", "never")


def test_list_has_at_most_four_items():
    def f(s):
        s["steps"][0]["cues"][-1]["slide"]["items"] = ["a b", "c d", "e f", "g h", "i j"]
        s["steps"][0]["cues"][-1]["do"] = [["show", "head"], ["items", [0, 1, 2, 3, 4]]]
    has(run(f), "step 1", "at most 4")


def test_cue_that_changes_the_picture_is_one_sentence():
    def f(s):
        cue(s, 2, 2)["say"] = "It starts with the source. A server you back up."
    has(run(f), "step 2 cue 2", "one sentence")


def test_cue_that_changes_the_picture_is_at_most_30_words():
    def f(s):
        cue(s, 2, 2)["say"] = "It starts with the source " + "and " * 30 + "a server you back up."
    has(run(f), "step 2 cue 2", "30 words")


def test_cue_without_a_picture_change_may_have_two_sentences():
    def f(s):
        cue(s, 6, 1)["say"] = "That is your score. Well done."
    assert not any("one sentence" in p for p in run(f))


def test_question_must_be_taught_first():
    def f(s):
        for step in s["steps"][1:4]:
            for c in step["cues"]:
                c["say"] = "A short remark about something else."
    has(run(f), "step 5 cue 1", "not taught")


def test_every_option_must_have_been_mentioned_before_the_question():
    def f(s):
        cue(s, 5, 1)["slide"]["opts"] = ["On the cluster", "Apart from backups", "Dropping"]
    has(run(f), "step 5 cue 1", "Dropping")


def sketch(shapes, w=660, h=230):
    return lambda s: s["sketches"].update(parts={"w": w, "h": h, "shapes": shapes})


def three(box_extra=None):
    return [{"box": [10, 40, 160, 56], "title": "Source"}, {"line": [174, 68, 226, 68], "arrow": True},
            {"box": [230, 40, 160, 56], "title": "Cluster"}]


def test_sketch_title_must_fit_its_box():
    shapes = three()
    shapes[0] = {"box": [10, 40, 60, 56], "title": "Source server"}
    has(run(sketch(shapes)), "parts", "Source server", "fit")


def test_sketch_boxes_must_not_overlap():
    shapes = three()
    shapes[2] = {"box": [150, 40, 160, 56], "title": "Cluster"}
    has(run(sketch(shapes)), "parts", "overlap")


def test_box_inside_a_larger_box_is_allowed():
    shapes = [{"box": [10, 10, 300, 180], "heavy": True}, {"box": [30, 70, 100, 56], "title": "Server"},
              {"line": [134, 98, 190, 98], "arrow": True}, {"box": [190, 70, 100, 56], "title": "Pool"}]
    def f(s):
        sketch(shapes, 330, 200)(s)
        cue(s, 2, 3)["do"] = [["build", [1, 2, 3]]]
    assert run(f) == []


def test_arrow_must_be_long_enough_to_see():
    shapes = three()
    shapes[1] = {"line": [174, 68, 190, 68], "arrow": True}
    shapes[2] = {"box": [194, 40, 160, 56], "title": "Cluster"}
    has(run(sketch(shapes)), "parts", "arrow")


def test_box_detail_must_fit_its_box():
    shapes = three()
    shapes[0] = {"box": [10, 40, 120, 70], "title": "Source", "detail": "172.16.0.0/22 pool"}
    has(run(sketch(shapes)), "parts", "detail", "fit")


def test_shapes_must_stay_inside_the_sketch():
    shapes = three()
    shapes[2] = {"box": [560, 40, 160, 56], "title": "Cluster"}
    has(run(sketch(shapes)), "parts", "outside")


def test_ca_needs_a_pronounce_entry():
    def f(s):
        cue(s, 2, 2)["say"] = "It starts with the CA, a server you back up."
    has(run(f), "step 2 cue 2", "CA", "pronounce")


def test_ca_with_a_pronounce_entry_is_clean():
    def f(s):
        s["pronounce"]["CA"] = "see ay"
        cue(s, 2, 2)["say"] = "It starts with the CA, a server you back up."
    assert not any("pronounce" in p for p in run(f))


def test_option_that_is_only_a_quantifier_needs_no_earlier_mention():
    def f(s):
        cue(s, 5, 1)["slide"]["opts"][2] = "Neither"
    assert not any("Neither" in p for p in run(f))
