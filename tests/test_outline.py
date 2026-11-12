import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "video"))

import outline  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "outline.json"
GOOD = json.loads(FIX.read_text())
STEMS = ["m1-u1-first", "m1-u2-second"]


def run(fn=None, stems=STEMS):
    o = copy.deepcopy(GOOD)
    if fn:
        fn(o)
    return outline.check_outline(o, stems)


def module(o, n=0):
    return o["modules"][n]


def named(problems, stem):
    assert problems, "expected a problem"
    assert all(stem in p for p in problems), problems


def test_a_good_outline_gives_no_problems():
    assert run() == []


def test_load_outline_reads_the_file():
    assert outline.load_outline(FIX) == GOOD


def test_fewer_than_two_outcomes():
    named(run(lambda o: module(o).update(outcomes=["Only one"])), "m1-u1-first")


def test_no_facts():
    named(run(lambda o: module(o).update(facts=[])), "m1-u1-first")


def test_a_fact_with_an_empty_source():
    named(run(lambda o: module(o)["facts"][0].update(source="  ")), "m1-u1-first")


def test_not_exactly_three_checks():
    named(run(lambda o: module(o, 1).update(checks=module(o, 1)["checks"][:2])), "m1-u2-second")
    named(run(lambda o: module(o, 1)["checks"].append(copy.deepcopy(module(o, 1)["checks"][0]))), "m1-u2-second")


def test_a_check_whose_ok_is_out_of_range():
    named(run(lambda o: module(o)["checks"][1].update(ok=2)), "m1-u1-first")
    named(run(lambda o: module(o)["checks"][1].update(ok=-1)), "m1-u1-first")


def test_a_unit_stem_with_no_unit_page():
    problems = run(stems=["m1-u1-first"])
    named(problems, "m1-u2-second")


def test_a_unit_page_with_no_module():
    problems = run(stems=STEMS + ["m1-u3-third"])
    named(problems, "m1-u3-third")


def test_option_and_why_limits_are_the_script_limits():
    named(run(lambda o: module(o)["checks"][0].update(why="one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen")), "m1-u1-first")
    named(run(lambda o: module(o)["checks"][0]["opts"].__setitem__(0, "one two three four five six")), "m1-u1-first")


def test_dates_and_beta_are_caught_in_any_text():
    named(run(lambda o: module(o)["facts"][0].update(text="It changed in March 2026.")), "m1-u1-first")
    named(run(lambda o: module(o).update(outcomes=["Know it is Beta", "Name the parts"])), "m1-u1-first")
    named(run(lambda o: module(o)["checks"][0].update(head="Which region, us-south?")), "m1-u1-first")
