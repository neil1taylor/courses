import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "video"))

import outline_text as ot  # noqa: E402

OUTLINE = json.loads((ROOT / "tests" / "fixtures" / "outline.json").read_text())


def test_export_lists_every_part_of_every_module_with_tags():
    text = ot.export_outline(OUTLINE, "B")
    lines = text.splitlines()
    assert lines[0] == "# B outline: Cyber Vault"
    assert "## B 1: The first module" in lines and "## B 2: The second module" in lines
    assert "[1.title] The first module" in lines
    assert "[1.o2] Say which one the course teaches" in lines
    assert "[1.f2] The read key cannot read outside the write window." in lines
    assert "source: cyber-vault/test-record.md" in [l.strip() for l in lines]
    assert "[1.q2] Where does the vault sit?" in lines
    assert "[1.q2a] In your account" in lines
    assert "[1.q2b] * In IBM's account" in lines
    assert "[1.q2why] IBM manages that account." in lines


def test_round_trip_changes_nothing():
    values, comments, problems = ot.parse_outline(ot.export_outline(OUTLINE, "B"))
    assert problems == [] and comments == {}
    data = copy.deepcopy(OUTLINE)
    assert ot.apply_outline(data, "B", values) == ([], [])
    assert data == OUTLINE


def test_edits_change_text_and_the_starred_answer():
    text = ot.export_outline(OUTLINE, "B")
    text = text.replace("[1.f1] The vault", "[1.f1] Now the vault")
    text = text.replace("[1.q2a] In your account", "[1.q2a] * In your account")
    text = text.replace("[1.q2b] * In IBM's account", "[1.q2b] In IBM's account")
    values, _, problems = ot.parse_outline(text)
    data = copy.deepcopy(OUTLINE)
    changed, apply_problems = ot.apply_outline(data, "B", values)
    assert problems == [] and apply_problems == []
    assert changed == ["B 1 fact 1", "B 1 check 2"]
    assert data["modules"][0]["facts"][0]["text"].startswith("Now the vault")
    assert data["modules"][0]["facts"][0]["source"] == OUTLINE["modules"][0]["facts"][0]["source"]
    assert data["modules"][0]["checks"][1]["ok"] == 0
    assert data["modules"][0]["checks"][1]["opts"] == ["In your account", "In IBM's account"]


def test_a_comment_attaches_to_the_line_above_it():
    text = ot.export_outline(OUTLINE, "B").replace(
        "[2.o1] Name the four parts\n", "[2.o1] Name the four parts\n> Which four?\n")
    _, comments, problems = ot.parse_outline(text)
    assert problems == [] and comments == {(2, "o1"): ["Which four?"]}


def test_two_stars_or_none_is_a_problem_and_leaves_the_question_alone():
    text = ot.export_outline(OUTLINE, "B").replace("[1.q1b] The architecture", "[1.q1b] * The architecture")
    text = text.replace("[2.q1a] * The write window", "[2.q1a] The write window")
    values, _, problems = ot.parse_outline(text)
    data = copy.deepcopy(OUTLINE)
    changed, apply_problems = ot.apply_outline(data, "B", values)
    assert problems == [] and changed == [] and data == OUTLINE
    assert any("B 1 check 1" in p and "2 answers" in p for p in apply_problems)
    assert any("B 2 check 1" in p and "no answer" in p for p in apply_problems)


def test_stray_line_unknown_tag_and_missing_tag_are_problems():
    text = ot.export_outline(OUTLINE, "B")
    _, _, problems = ot.parse_outline(text.replace("[1.o1] ", "", 1))
    assert any("no tag at the start" in p for p in problems)
    values, _, _ = ot.parse_outline(text.replace("[1.o1] Name", "[1.o9] Name"))
    data = copy.deepcopy(OUTLINE)
    _, apply_problems = ot.apply_outline(data, "B", values)
    assert any("[1.o1] is missing" in p for p in apply_problems)
    assert any("[1.o9]" in p and "no such" in p for p in apply_problems)
    assert data == OUTLINE
