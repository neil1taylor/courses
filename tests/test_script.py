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


def test_summary_must_say_the_closing_line():
    only(run(say(6, 2, "Remember, one copy stays safe. Next, building the vault.")), "step 6 cue 2", "If you remember one thing")


def test_summary_closing_line_shortened_is_refused():
    only(run(say(6, 2, "One copy stays safe. Remember the sentence on screen.")), "If you remember one thing")


def test_summary_closing_line_said_on_screen_is_accepted():
    assert run(say(6, 2, "One copy stays safe. If you remember one thing, make it the sentence on screen.")) == []


def test_closing_line_outside_the_summary_does_not_count():
    def f(s):
        cue(s, 6, 2)["say"] = "One copy stays safe."
        cue(s, 6, 1)["say"] = "That is your score. If you remember one thing, make it the sentence on the screen."
    only(run(f), "If you remember one thing")


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


# ---- table slide ----
def as_table(s, rows=None, cols=None, do=None):
    slide(s, 4, 2).clear()
    slide(s, 4, 2).update(type="table", head="What each key got",
                          cols=cols or ["request", "outside", "inside"],
                          rows=rows or [["list, write key", "403", "200"], ["list, read key", "403", "200"]])
    cue(s, 4, 2)["do"] = do if do is not None else [["show", "head"], ["show", "table"], ["row", 1]]


def test_good_table_is_clean():
    assert run(as_table) == []


def test_table_needs_cols_and_rows():
    for key in ("cols", "rows", "head"):
        def f(s, k=key):
            as_table(s)
            slide(s, 4, 2).pop(k)
        has(run(f), "step 4 cue 2", key)


def test_table_row_of_wrong_length():
    has(run(lambda s: as_table(s, rows=[["a", "b", "c"], ["a", "b"]])), "step 4 cue 2", "row 1", "3 columns")


def test_table_with_5_columns():
    has(run(lambda s: as_table(s, cols=list("abcde"), rows=[list("abcde"), list("abcde")])), "step 4 cue 2", "5 columns")


def test_table_with_1_column():
    has(run(lambda s: as_table(s, cols=["a"], rows=[["x"], ["y"]])), "step 4 cue 2", "1 column")


def test_table_with_7_rows():
    has(run(lambda s: as_table(s, rows=[["a", "b", "c"]] * 7)), "step 4 cue 2", "7 rows")


def test_table_with_1_row():
    has(run(lambda s: as_table(s, rows=[["a", "b", "c"]])), "step 4 cue 2", "1 row")


def test_table_cells_must_be_strings():
    has(run(lambda s: as_table(s, rows=[["a", "b", 3], ["a", "b", "c"]])), "step 4 cue 2", "strings")


def test_table_row_out_of_range():
    has(run(lambda s: as_table(s, do=[["show", "head"], ["show", "table"], ["row", 2]])), "step 4 cue 2", "row 2")


def test_row_on_a_slide_that_is_not_a_table():
    has(run(lambda s: cue(s, 4, 2).update(do=[["row", 0]])), "step 4 cue 2", "not a table")


def test_table_never_shown():
    has(run(lambda s: as_table(s, do=[["show", "head"]])), "step 4 cue 2", "table", "never shown")


def test_table_head_never_shown():
    has(run(lambda s: as_table(s, do=[["show", "table"]])), "step 4 cue 2", "head", "never shown")


def test_table_head_counts_toward_20_words_cells_do_not():
    has(run(lambda s: (as_table(s), slide(s, 4, 2).update(head=" ".join(["w"] * 21)))), "step 4 cue 2", "21 words")
    assert run(lambda s: as_table(s, rows=[["word " * 15, "b", "c"], ["a", "b", "c"]])) == []


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


def test_terminal_with_8_lines_and_last_box_are_allowed():
    def f(s):
        slide(s, 4, 2)["out"] = ["l%d" % i for i in range(8)]
        cue(s, 4, 2)["do"] = [["line", 7]]
        n = len(slide(s, 4, 1)["boxes"])
        cue(s, 4, 1)["do"] = [["show", "head"], ["box", n - 1]]
    assert run(f) == []


def test_opts_given_as_a_number_is_a_problem_not_a_crash():
    has(run(lambda s: slide(s, 3, 1).update(opts=5)), "opts")


def test_shapes_given_as_a_number_is_a_problem_not_a_crash():
    def f(s):
        s["sketches"]["parts"]["shapes"] = 5
    has(run(f), "shapes")


def test_question_mark_after_missing_first_slide_adds_no_second_problem():
    def f(s):
        c = cue(s, 2, 1)
        del c["slide"]
        c["say"] = "Which one is it?"
    problems = run(f)
    assert not any("question" in p for p in problems if "outside a question slide" in p), problems
    has(problems, "first cue of a step needs a slide")


# ---- review checks: rejected wording, first mentions, the teaching cue ----

PREFIX = FIX / "prefix"
VAULT = Path.home() / "Projects" / "cohesity" / "course" / "vault"


def prefix_problems(stem):
    s = json.loads((PREFIX / (stem + ".json")).read_text())
    return script.check_script(s, (PREFIX / (stem + ".html")).read_text(), False)


def test_rejected_wording_is_reported_in_slide_text():
    found = [p for p in prefix_problems("m4-u4-final-scenario") if "rejected wording" in p]
    assert found and "Four items stay out of the plan" in found[0]


def test_rejected_wording_is_reported_in_narration():
    def f(s):
        cue(s, 2, 1)["say"] = "Here is the idea. Three things are true about keys."
    only(run(f), "step 2 cue 1", "rejected wording")


def test_rejected_wording_only_matches_at_sentence_start():
    def f(s):
        cue(s, 2, 1)["say"] = "We note that three things are true about keys."
    assert not [p for p in run(f, first_module=False) if "rejected wording" in p]


def test_no_current_vault_script_gains_a_problem():
    folder = VAULT / "video"
    if not folder.is_dir():
        import pytest
        pytest.skip("cohesity course folder not present")
    for path in sorted(folder.glob("m*.json")):
        unit = (VAULT / (path.stem + ".html")).read_text()
        found = script.check_script(json.loads(path.read_text()), unit, path.stem.startswith("m0-u1"))
        assert not [p for p in found if "rejected wording" in p], (path.name, found)


def test_teaching_cue_is_earlier_than_each_question():
    path = VAULT / "video" / "m1-u4-two-products-one-name.json"
    if not path.is_file():
        import pytest
        pytest.skip("cohesity course folder not present")
    s = json.loads(path.read_text())
    asked = [(si, ci) for si, st in enumerate(s["steps"], 1) for ci, c in enumerate(st["cues"], 1)
             if (c.get("slide") or {}).get("type") == "q"]
    assert asked
    for si, ci in asked:
        found = script.teaching_cue(s, si, ci)
        assert found is not None and found < (si, ci), (si, ci, found)


def test_teaching_cue_is_none_when_nothing_earlier_matches():
    s = {"steps": [{"cues": [
        {"say": "Hello there."},
        {"say": "Which colour?", "slide": {"type": "q", "head": "h", "opts": ["Purple elephants", "b"], "ok": 0, "why": "Purple elephants dance."}},
    ]}]}
    assert script.teaching_cue(s, 1, 2) is None


def test_first_mention_notes_the_first_use_of_a_new_the_x_key():
    s = {"steps": [{"cues": [
        {"say": "Welcome. Use the write key to send data."},
        {"say": "Keep the write key safe. Then check the log setting."},
    ]}]}
    got = script.notes(s)
    assert got == ["step 1 cue 1: first mention of 'the write key'",
                   "step 1 cue 2: first mention of 'the log setting'"]


def test_first_mention_is_not_a_note_when_an_earlier_sentence_names_the_word():
    s = {"steps": [{"cues": [
        {"say": "The window is daily. Now the window ends."},
        {"say": "Use the window setting."},
    ]}]}
    assert script.notes(s) == []


def test_teaching_cue_skips_the_opening_step_for_later_questions():
    # The opening step lists what the learner will be able to do; it names topics, it doesn't teach them.
    path = VAULT / "video" / "m3-u4-write-window-and-network.json"
    if not path.is_file():
        import pytest
        pytest.skip("cohesity course folder not present")
    s = json.loads(path.read_text())
    asked = [(si, ci) for si, st in enumerate(s["steps"], 1) for ci, c in enumerate(st["cues"], 1)
             if (c.get("slide") or {}).get("type") == "q" and si > 1]
    for si, ci in asked:
        found = script.teaching_cue(s, si, ci)
        assert found is None or found[0] > 1, (si, ci, found)
