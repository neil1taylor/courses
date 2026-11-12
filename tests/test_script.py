import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "video"))

import script  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
UNIT = (FIX / "unit.html").read_text()


def check(name, first_module=False):
    return script.check_script(script.load_script(FIX / name), UNIT, first_module)


def has(problems, *needles):
    return any(all(n in p for n in needles) for p in problems)


def test_good_fixture_is_clean():
    assert check("good.json", first_module=True) == []


def test_load_script_reads_json():
    assert script.load_script(FIX / "good.json")["course"] == "Cyber Vault"


def test_more_than_20_words_on_a_slide():
    p = check("bad-too-many-words.json")
    assert has(p, "step 1 cue 1", "21 words")


def test_words_slide_with_5_terms():
    assert has(check("bad-five-terms.json"), "step 2 cue 1", "5 terms")


def test_words_slide_definition_over_10_words():
    assert has(check("bad-long-definition.json"), "step 2 cue 1", "definition")


def test_date_in_narration():
    assert has(check("bad-year.json"), "step 1 cue 2", "date")


def test_month_and_number_in_slide_text():
    assert has(check("bad-month.json"), "step 1 cue 1", "date")


def test_date_in_terminal_output_is_allowed():
    s = script.load_script(FIX / "good.json")
    s["steps"][3]["cues"][1]["slide"]["out"] = ["Created 12 March 2026", "demo  normal"]
    assert script.check_script(s, UNIT, True) == []


def test_beta():
    assert has(check("bad-beta.json"), "step 1 cue 2", "Beta")


def test_region_as_availability():
    assert has(check("bad-region.json"), "step 1 cue 3", "us-south")


def test_in_our_lab():
    assert has(check("bad-our-lab.json"), "step 1 cue 2", "in our lab")


def test_unit_number_in_narration():
    assert has(check("bad-unit-number.json"), "step 1 cue 2", "Unit 1.3")


def test_module_number_in_narration():
    assert has(check("bad-module-number.json"), "step 1 cue 3", "Module 4")


def test_build_names_missing_sketch_part():
    assert has(check("bad-build-part.json"), "step 1 cue 2", "sketch part 7")


def test_show_names_missing_slide_key():
    assert has(check("bad-show-key.json"), "step 1 cue 1", "slide key", "sub")


def test_items_names_missing_term():
    assert has(check("bad-items.json"), "step 2 cue 2", "term 4")


def test_unknown_sketch_name():
    assert has(check("bad-sketch-name.json"), "step 1 cue 1", "sketch", "nowhere")


def test_screen_image_the_unit_does_not_use():
    assert has(check("bad-image.json"), "step 4 cue 1", "image", "assets/missing.png")


def test_box_and_line_out_of_range():
    p = check("bad-box-line.json")
    assert has(p, "step 4 cue 1", "box 3")
    assert has(p, "step 4 cue 2", "line 5")


def test_terminal_with_9_lines():
    assert has(check("bad-terminal.json"), "step 4 cue 2", "9 lines")


def test_unknown_action():
    assert has(check("bad-action.json"), "step 1 cue 2", "action", "wobble")


def test_step_with_no_cues():
    assert has(check("bad-no-cues.json"), "step 2", "no cues")


def test_question_without_ok_option():
    assert has(check("bad-no-ok.json"), "step 3 cue 1", "ok")


def test_narration_on_screen():
    assert has(check("bad-narration-on-screen.json"), "step 1 cue 1", "narration")


def test_first_module_must_say_tested():
    assert has(check("bad-not-tested.json", first_module=True), "tested")


def test_other_modules_need_not_say_tested():
    assert check("bad-not-tested.json", first_module=False) == []


def test_first_cue_of_step_needs_a_slide():
    assert has(check("bad-no-slide.json"), "step 2 cue 1", "slide")


def test_option_over_5_words():
    assert has(check("bad-long-option.json"), "step 3 cue 1", "option")
