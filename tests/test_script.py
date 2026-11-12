import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "video"))

import script  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
UNIT = (FIX / "unit.html").read_text()
GOOD = json.loads((FIX / "good.json").read_text())


def mutated(fn):
    s = copy.deepcopy(GOOD)
    fn(s)
    return s


def run(fn=None, first_module=True):
    s = mutated(fn) if fn else copy.deepcopy(GOOD)
    return script.check_script(s, UNIT, first_module)


def cue(s, st, c):
    return s["steps"][st - 1]["cues"][c - 1]


def slide(s, st, c):
    return cue(s, st, c)["slide"]


def only(problems, *needles):
    """Exactly one problem, and it holds every needle."""
    assert len(problems) == 1, problems
    assert all(n in problems[0] for n in needles), problems


def has(problems, *needles):
    assert any(all(n in p for n in needles) for p in problems), problems


def say(st, c, text):
    return lambda s: cue(s, st, c).update(say=text)


def test_good_fixture_is_clean():
    assert run(first_module=True) == []


def test_load_script_reads_json():
    assert script.load_script(FIX / "good.json")["course"] == "Cyber Vault"


# ---- whole-script shape ----
def test_no_steps():
    has(run(lambda s: s.pop("steps")), "no steps")


def test_leftover_clips_key():
    def f(s):
        s["clips"] = s["steps"]
    only(run(f), "clips")


def test_missing_top_level_fields():
    for key in ("course", "section", "title", "unit"):
        only(run(lambda s, k=key: s.pop(k)), key)


def test_step_with_no_cues():
    only(run(lambda s: s["steps"][3].update(cues=[])), "step 4", "no cues")


# ---- required fields per type ----
def test_screen_needs_boxes():
    only(run(lambda s: slide(s, 4, 1).pop("boxes")), "step 4 cue 1", "boxes")


def test_question_needs_opts_ok_why():
    for key in ("opts", "ok", "why"):
        has(run(lambda s, k=key: slide(s, 5, 1).pop(k)), "step 5 cue 1", key)


def test_terminal_needs_cmd():
    has(run(lambda s: slide(s, 4, 2).pop("cmd")), "step 4 cue 2", "cmd")


def test_tip_needs_tip():
    def f(s):
        cue(s, 2, 2)["slide"] = {"type": "tip", "head": "Watch out"}
    has(run(f), "step 2 cue 2", "tip")


def test_summary_needs_text_and_next():
    for key in ("text", "next"):
        has(run(lambda s, k=key: slide(s, 6, 2).pop(k)), "step 6 cue 2", key)


def test_diagram_needs_sketch():
    has(run(lambda s: slide(s, 2, 1).pop("sketch")), "step 2 cue 1", "sketch")


# ---- word counts ----
def test_more_than_20_words_on_a_slide():
    def f(s):
        slide(s, 2, 1)["head"] = " ".join(["word"] * 19)
    only(run(f), "step 2 cue 1", "21 words")


def test_exactly_20_words_is_clean():
    def f(s):
        slide(s, 2, 1)["head"] = " ".join(["word"] * 18)
    assert run(f) == []


def test_words_slide_with_5_terms():
    def f(s):
        slide(s, 3, 1)["items"] = [["a", "b"]] * 5
        cue(s, 3, 2)["do"] = [["items", [1]]]
        cue(s, 3, 1)["do"] = [["show", "head"], ["items", [0, 2, 3, 4]]]
    only(run(f), "step 3 cue 1", "5 terms")


def test_words_definition_over_10_words():
    def f(s):
        slide(s, 3, 1)["items"][0][1] = "one two three four five six seven eight nine ten eleven"
    only(run(f), "step 3 cue 1", "definition")


def test_option_over_5_words():
    def f(s):
        slide(s, 5, 1)["opts"][1] = "Apart from the backup system always"
    only(run(f), "step 5 cue 1", "option")


# ---- dates, Beta, regions, lab ----
def test_dates_flagged():
    for text in ("It started in 2019 with a server.", "It ended on May 5 for us.",
                 "Release 2026 is here.", "Since 2015 it works."):
        only(run(say(2, 2, text)), "step 2 cue 2", "date")


def test_month_and_number_in_slide_text():
    def f(s):
        slide(s, 2, 1)["head"] = "Offer ends March 31"
    only(run(f), "step 2 cue 1", "date")


def test_not_dates():
    for text in ("Up to 3 may be enough.", "Step 2 may fail.", "Use port 2049.", "Set 1920 by 1080.",
                 "The alphabet is fine."):
        assert run(say(2, 2, text)) == [], text


def test_date_in_terminal_output_is_allowed():
    def f(s):
        slide(s, 4, 2)["out"] = ["Created 12 March 2026", "demo  normal"]
    assert run(f) == []


def test_beta():
    only(run(say(2, 2, "This feature is in Beta today.")), "step 2 cue 2", "Beta")


def test_region_as_availability():
    only(run(say(2, 3, "It is only in us-south.")), "step 2 cue 3", "us-south")


def test_more_region_codes():
    for r in ("us-east", "eu-gb", "eu-es", "jp-tok", "jp-osa", "au-syd", "ca-tor", "br-sao", "Dallas", "eu-de"):
        only(run(say(2, 3, "It is only in %s." % r)), "step 2 cue 3", "region")


def test_our_lab_and_our_tests():
    for text in ("In our lab the copies stayed.", "Our lab showed it.", "In our tests it held."):
        only(run(say(2, 2, text)), "step 2 cue 2")


# ---- numbers and words in narration ----
def test_unit_and_module_numbers():
    for text in ("Unit 1.3 covers that.", "See Module 4 for more.", "That is unit one."):
        only(run(say(2, 2, text)), "step 2 cue 2", "names")


def test_unit_clip_lesson_words():
    for text in ("That's the unit done.", "This unit covers it.", "Watch the clip.", "A short lesson follows."):
        only(run(say(2, 2, text)), "step 2 cue 2")


def test_tested_sentence_only_in_first_module():
    only(run(first_module=False), "step 1 cue 2", "first module")


def test_first_module_must_say_tested():
    def f(s):
        cue(s, 1, 2)["say"] = "That is the first step."
    only(run(f, first_module=True), "tested")


def test_other_modules_need_not_say_tested():
    def f(s):
        cue(s, 1, 2)["say"] = "That is the first step."
    assert run(f, first_module=False) == []


def test_first_module_saying_tested_once_is_clean():
    assert run(first_module=True) == []


# ---- things that must exist ----
def test_build_names_missing_sketch_part():
    p = run(lambda s: cue(s, 2, 2).update({"do": [["build", [7]]]}))
    has(p, "step 2 cue 2", "sketch part 7")


def test_show_names_missing_slide_key():
    p = run(lambda s: cue(s, 2, 1).update({"do": [["show", "sub"]]}))
    has(p, "step 2 cue 1", "slide key", "sub")


def test_items_names_missing_term():
    has(run(lambda s: cue(s, 3, 2).update({"do": [["items", [4]]]})), "step 3 cue 2", "term 4")


def test_unknown_sketch_name():
    has(run(lambda s: slide(s, 2, 1).update(sketch="nowhere")), "step 2 cue 1", "sketch", "nowhere")


def test_screen_image_the_unit_does_not_use():
    has(run(lambda s: slide(s, 4, 1).update(img="assets/missing.png")), "step 4 cue 1", "image", "assets/missing.png")


def test_box_and_line_out_of_range():
    def f(s):
        cue(s, 4, 1)["do"] = [["show", "head"], ["box", 3]]
        cue(s, 4, 2)["do"] = [["line", 5]]
    p = run(f)
    has(p, "step 4 cue 1", "box 3")
    has(p, "step 4 cue 2", "line 5")


def test_terminal_with_9_lines():
    has(run(lambda s: slide(s, 4, 2).update(out=["l%d" % i for i in range(9)])), "step 4 cue 2", "9 lines")


def test_terminal_out_as_string():
    def f(s):
        slide(s, 4, 2)["out"] = "Name  State\ndemo  normal"
        cue(s, 4, 2)["do"] = [["line", 1]]
    assert run(f) == []
    def g(s):
        f(s)
        cue(s, 4, 2)["do"] = [["line", 2]]
    has(run(g), "line 2")
    def h(s):
        slide(s, 4, 2)["out"] = "\n".join("l%d" % i for i in range(9))
    has(run(h), "9 lines")


def test_unknown_action():
    has(run(lambda s: cue(s, 2, 2).update({"do": [["wobble", 1]]})), "step 2 cue 2", "action", "wobble")


# ---- content never shown ----
def test_head_never_shown():
    only(run(lambda s: cue(s, 2, 1).update({"do": []})), "step 2 cue 1", "head", "never shown")


def test_sketch_part_never_built():
    only(run(lambda s: cue(s, 2, 3).update({"do": [["build", [1]]]})), "step 2 cue 1", "part 2", "never built")


def test_word_item_never_revealed():
    only(run(lambda s: cue(s, 3, 2).update({"do": []})), "step 3 cue 1", "term 1", "never")


def test_question_with_no_ask():
    only(run(lambda s: cue(s, 5, 1).update({"do": []})), "step 5 cue 1", "ask")


def test_question_with_no_why_after_ask():
    only(run(lambda s: cue(s, 5, 2).update({"do": []})), "step 5 cue 1", "why")


def test_summary_next_never_shown():
    only(run(lambda s: cue(s, 6, 2).update({"do": [["show", "head"], ["build", [0]]]})), "step 6 cue 2", "next")


# ---- narration ----
def test_narration_on_screen():
    only(run(say(2, 1, "A second copy goes into a locked vault.")), "step 2 cue 1", "narration")


def test_title_head_in_welcome_is_allowed():
    assert run(say(1, 1, "Welcome to Why backups need a vault. This module shows why.")) == []


def test_first_cue_of_step_needs_a_slide():
    only(run(lambda s: cue(s, 3, 1).pop("slide")), "step 3 cue 1", "slide")


def test_no_cascade_after_missing_slide():
    def f(s):
        cue(s, 3, 1).pop("slide")
        cue(s, 3, 2)["do"] = [["build", [9]]]
    only(run(f), "step 3 cue 1", "slide")


def test_question_mark_off_a_question_slide():
    only(run(say(2, 2, "Why is that?")), "step 2 cue 2", "question")


def test_cue_without_say():
    only(run(say(2, 2, "  ")), "step 2 cue 2", "say")


def test_narration_length():
    def f(s):
        cue(s, 2, 2)["say"] = "word " * 1000
    has(run(f), "4,500")


# ---- questions in the module ----
def test_two_questions_is_too_few():
    def f(s):
        s["steps"][4]["cues"] = s["steps"][4]["cues"][:4]
    has(run(f), "2 questions")


def test_six_questions_is_too_many():
    def f(s):
        s["steps"][4]["cues"] = s["steps"][4]["cues"] * 2
    has(run(f), "6 questions")


def test_exactly_three_checks_and_the_last_three():
    def f(s):
        slide(s, 5, 1)["check"] = False
    has(run(f), "check")
    def g(s):
        extra = copy.deepcopy(s["steps"][4]["cues"][:2])
        extra[0]["slide"]["check"] = False
        s["steps"][4]["cues"] += extra
    has(run(g), "last three")


def test_score_slide_follows_the_check_questions():
    def f(s):
        s["steps"][5]["cues"].pop(0)
        cue(s, 6, 1)["do"] = [["show", "head"], ["show", "next"], ["build", [0]]]
    has(run(f), "score")


# ---- sketches ----
def test_sketch_size_limits():
    def f(s):
        s["sketches"]["parts"]["w"] = 961
    has(run(f), "step 2 cue 1", "960")
    def g(s):
        s["sketches"]["mini"]["w"] = 351
    has(run(g), "step 6 cue 2", "350")


# ---- "read" ----
def test_read_without_pronounce():
    def f(s):
        s.pop("pronounce")
    has(run(f), "step 2 cue 3", "read", "pronounce")


def test_no_read_no_pronounce_needed():
    def f(s):
        s.pop("pronounce")
        cue(s, 2, 3)["say"] = "The cluster runs the backups, and the key opens them."
        cue(s, 5, 1)["say"] = "Where should Northgate keep the recovery key?"
    assert run(f) == []


def test_past_tense_read_even_with_pronounce():
    for text in ("Then we had read it.", "They have read it.", "It was read back.", "First write, then read it."):
        only(run(say(2, 2, text)), "step 2 cue 2", "past tense")


def test_pronounce_values_lower_case():
    only(run(lambda s: s.update(pronounce={"read": "Reed"})), "pronounce", "lower")


# ---- robustness ----
def test_malformed_input_gives_problems_not_exceptions():
    cases = [
        lambda s: cue(s, 2, 2).update({"do": [["build", 3]]}),
        lambda s: cue(s, 3, 2).update({"do": [["items", "x"]]}),
        lambda s: cue(s, 2, 1).update({"do": [["show", ["head"]]]}),
        lambda s: cue(s, 2, 1).update({"slide": "oops"}),
        lambda s: cue(s, 2, 1).update({"do": "oops"}),
        lambda s: s["steps"].__setitem__(0, "oops"),
        lambda s: s["steps"][0]["cues"].__setitem__(0, "oops"),
        lambda s: s.update(steps="oops"),
        lambda s: s.update(sketches=[]),
        lambda s: slide(s, 3, 1).update(items=["x"]),
        lambda s: slide(s, 5, 1).update(opts="abc"),
        lambda s: slide(s, 4, 1).update(boxes=3),
        lambda s: cue(s, 2, 1).update({"do": [[]]}),
    ]
    for fn in cases:
        assert run(fn), fn
