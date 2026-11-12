"""Load and check a course outline before any script is written.

check_outline returns one string per problem, each naming its module by unit stem:
"module <unit>: <what>". A unit page with no module and a module with no unit page are
reported by stem too. It never raises on a malformed outline: it reports the malformation.
The limits on options and why lines, and the date, Beta, region and "in our lab" checks on
all text, are script.py's.
"""
import json
from pathlib import Path

import script

MIN_OUTCOMES = 2
CHECKS = 3


def load_outline(path) -> dict:
    return json.loads(Path(path).read_text())


def _text_problems(text, at, what):
    return script.check_text(text, at, what)


def _check_module(m, at) -> list:
    problems = []
    if not isinstance(m.get("title"), str) or not m["title"].strip():
        problems.append("%s: no title" % at)
    outcomes = m.get("outcomes")
    if not isinstance(outcomes, list) or not all(isinstance(o, str) and o.strip() for o in outcomes):
        problems.append("%s: outcomes must be a list of sentences" % at)
        outcomes = []
    elif len(outcomes) < MIN_OUTCOMES:
        problems.append("%s: has %d outcome%s, needs at least %d" % (at, len(outcomes), "" if len(outcomes) == 1 else "s", MIN_OUTCOMES))
    for o in outcomes:
        problems += _text_problems(o, at, "outcome")
    if isinstance(m.get("title"), str):
        problems += _text_problems(m["title"], at, "title")

    facts = m.get("facts")
    if not isinstance(facts, list) or not facts:
        problems.append("%s: has no facts" % at)
        facts = []
    for i, f in enumerate(facts, 1):
        if not isinstance(f, dict) or not isinstance(f.get("text"), str) or not f["text"].strip():
            problems.append("%s: fact %d has no text" % (at, i))
            continue
        if not isinstance(f.get("source"), str) or not f["source"].strip():
            problems.append("%s: fact %d has no source" % (at, i))
        problems += _text_problems(f["text"], at, "fact %d" % i)

    checks = m.get("checks")
    if not isinstance(checks, list):
        problems.append("%s: checks must be a list" % at)
        checks = []
    elif len(checks) != CHECKS:
        problems.append("%s: has %d checks, needs exactly %d" % (at, len(checks), CHECKS))
    for i, c in enumerate(checks, 1):
        problems += _check_question(c, at, i)
    return problems


def _check_question(c, at, i) -> list:
    where = "check %d" % i
    if not isinstance(c, dict):
        return ["%s: %s is not an object" % (at, where)]
    opts, ok = c.get("opts"), c.get("ok")
    if not isinstance(c.get("head"), str) or not c["head"].strip():
        return ["%s: %s has no head" % (at, where)]
    if not isinstance(opts, list) or not all(isinstance(o, str) for o in opts):
        return ["%s: %s options must be a list of strings" % (at, where)]
    if not isinstance(c.get("why"), str):
        return ["%s: %s has no why" % (at, where)]
    problems = []
    if not 2 <= len(opts) <= 4:
        problems.append("%s: %s needs 2 to 4 options, has %d" % (at, where, len(opts)))
    if isinstance(ok, bool) or not isinstance(ok, int) or not 0 <= ok < len(opts):
        problems.append("%s: %s has no ok option (ok is %r for %d options)" % (at, where, ok, len(opts)))
    for j, o in enumerate(opts):
        if len(script.words(o)) > script.MAX_OPTION:
            problems.append("%s: %s option %d is %d words, at most %d" % (at, where, j, len(script.words(o)), script.MAX_OPTION))
    if len(script.words(c["why"])) > script.MAX_WHY:
        problems.append("%s: %s why line is over %d words" % (at, where, script.MAX_WHY))
    for text in [c["head"], c["why"]] + opts:
        problems += _text_problems(text, at, where)
    return problems


def check_outline(outline: dict, unit_stems: list) -> list:
    if not isinstance(outline, dict):
        return ["outline: not a JSON object"]
    problems = []
    if not isinstance(outline.get("course"), str) or not outline["course"].strip():
        problems.append("outline: has no course")
    modules = outline.get("modules")
    if not isinstance(modules, list) or not modules:
        problems.append("outline: has no modules")
        modules = []
    seen = set()
    for n, m in enumerate(modules, 1):
        if not isinstance(m, dict) or not isinstance(m.get("unit"), str):
            problems.append("outline: module %d has no unit stem" % n)
            continue
        stem = m["unit"]
        at = "module %s" % stem
        if stem in seen:
            problems.append("%s: listed twice" % at)
        seen.add(stem)
        if stem not in unit_stems:
            problems.append("%s: no unit page has this stem" % at)
        problems += _check_module(m, at)
    for stem in unit_stems:
        if stem not in seen:
            problems.append("module %s: a unit page exists but the outline has no module for it" % stem)
    return problems
