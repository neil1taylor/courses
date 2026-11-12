"""Load and check a module script before any audio is made.

check_script returns one string per problem, "step <n> cue <m>: <what>", counting
from 1. A problem about a whole step uses cue 0; one about the whole script uses
step 0 cue 0.
"""
import json
import re
from pathlib import Path

MAX_WORDS = 20
MAX_TERMS = 4
MAX_DEFINITION = 10
MAX_OPTION = 5
MAX_WHY = 15
MAX_TIP = 12
MAX_TITLE_WORDS = 14
MAX_SUMMARY_WORDS = 14
MAX_TERMINAL_LINES = 8

# The keys a `show` action can reveal, by slide type: the data-k values the player renders.
SHOW_KEYS = {
    "title": {"head", "sub"},
    "diagram": {"head"},
    "statement": {"head"},
    "q": {"head", "opts", "hint", "why"},
    "tip": {"head", "tip"},
    "words": {"head"},
    "summary": {"head", "next"},
    "screen": {"head", "img"},
    "terminal": set(),
    "score": {"head"},
}
ACTIONS = {"show", "build", "items", "ask", "why", "box", "line"}

MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December|"
          "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
YEAR = re.compile(r"\b(19|20)\d\d\b")
MONTH_DAY = re.compile(r"\b(%s)\.?\s+\d" % MONTHS, re.I)
DAY_MONTH = re.compile(r"\b\d{1,2}(st|nd|rd|th)?\s+(%s)\b" % MONTHS, re.I)
BETA = re.compile(r"\bbeta\b", re.I)
REGIONS = re.compile(r"\b(us-south|dallas|eu-de)\b", re.I)
OUR_LAB = re.compile(r"\bin our lab\b", re.I)
NUMBER_WORDS = "one|two|three|four|five|six|seven|eight|nine|ten"
UNIT_NUMBER = re.compile(r"\b(unit|module)\s+(\d[\d.]*|(%s)\b)" % NUMBER_WORDS, re.I)
TESTED = re.compile(r"\btested\b", re.I)
TAG = re.compile(r"<[^>]+>")


def load_script(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def words(text) -> list:
    return TAG.sub(" ", str(text)).split()


def norm(text) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", TAG.sub(" ", str(text)).lower()).split())


def sketch_text(spec) -> list:
    out = []
    for shape in (spec or {}).get("shapes", []):
        for key in ("title", "detail", "text"):
            if shape.get(key):
                out.append(shape[key])
    return out


def slide_strings(slide) -> list:
    """Every string a learner sees on a slide, for the rules about what may be said.
    Terminal output and screenshots are left out: dates and names there are allowed."""
    out = [slide.get(k) for k in ("head", "sub", "tip", "text", "why", "next") if slide.get(k)]
    out += list(slide.get("opts", []))
    for term in slide.get("items", []):
        out += list(term)
    return out


def slide_words(slide, sketches) -> int:
    """Words counted against the limit of 20: head, sub, tip, text, answer options, sketch labels.
    The why line and the next line have their own limits."""
    parts = [slide.get(k) for k in ("head", "sub", "tip", "text") if slide.get(k)]
    parts += list(slide.get("opts", []))
    if slide.get("sketch"):
        parts += sketch_text(sketches.get(slide["sketch"]))
    return sum(len(words(p)) for p in parts)


def check_slide(slide, sketches, unit_html, at) -> list:
    problems = []
    kind = slide.get("type")
    if kind not in SHOW_KEYS:
        return ["%s: slide type %r is not one the player can show" % (at, kind)]
    if slide.get("sketch") and slide["sketch"] not in sketches:
        problems.append("%s: slide uses sketch %r, which is defined nowhere in sketches" % (at, slide["sketch"]))
    if kind == "words":
        items = slide.get("items", [])
        if len(items) > MAX_TERMS:
            problems.append("%s: words slide has %d terms, at most %d" % (at, len(items), MAX_TERMS))
        for term, definition in items:
            if len(words(definition)) > MAX_DEFINITION:
                problems.append("%s: definition of %r is %d words, at most %d"
                                % (at, term, len(words(definition)), MAX_DEFINITION))
    else:
        n = slide_words(slide, sketches)
        if n > MAX_WORDS:
            problems.append("%s: slide has %d words, at most %d" % (at, n, MAX_WORDS))
    if kind == "title" and len(words(slide.get("head", "")) + words(slide.get("sub", ""))) > MAX_TITLE_WORDS:
        problems.append("%s: title slide text is over %d words" % (at, MAX_TITLE_WORDS))
    if kind == "summary" and len(words(slide.get("text", ""))) > MAX_SUMMARY_WORDS:
        problems.append("%s: summary sentence is over %d words" % (at, MAX_SUMMARY_WORDS))
    if kind == "tip" and len(words(slide.get("tip", ""))) > MAX_TIP:
        problems.append("%s: tip line is over %d words" % (at, MAX_TIP))
    if kind == "q":
        opts = slide.get("opts", [])
        ok = slide.get("ok")
        if not 2 <= len(opts) <= 4:
            problems.append("%s: question needs 2 to 4 options, has %d" % (at, len(opts)))
        if not isinstance(ok, int) or isinstance(ok, bool) or not 0 <= ok < len(opts):
            problems.append("%s: question has no ok option (ok is %r for %d options)" % (at, ok, len(opts)))
        for i, o in enumerate(opts):
            if len(words(o)) > MAX_OPTION:
                problems.append("%s: option %d is %d words, at most %d" % (at, i, len(words(o)), MAX_OPTION))
        if len(words(slide.get("why", ""))) > MAX_WHY:
            problems.append("%s: why line is over %d words" % (at, MAX_WHY))
    if kind == "screen":
        img = slide.get("img", "")
        if not img or img not in unit_html:
            problems.append("%s: image %r is not used by the unit" % (at, img))
    if kind == "terminal":
        out = slide.get("out", [])
        if len(out) > MAX_TERMINAL_LINES:
            problems.append("%s: terminal slide has %d lines, at most %d" % (at, len(out), MAX_TERMINAL_LINES))
    return problems


def check_action(action, slide, sketches, at) -> list:
    if not isinstance(action, list) or not action or action[0] not in ACTIONS:
        name = action[0] if isinstance(action, list) and action else action
        return ["%s: action %r does not exist" % (at, name)]
    name, value = action[0], action[1] if len(action) > 1 else None
    kind = slide.get("type")
    if name == "show":
        if value not in SHOW_KEYS[kind]:
            return ["%s: slide key %r does not exist on a %s slide" % (at, value, kind)]
    elif name == "build":
        spec = sketches.get(slide.get("sketch"))
        if spec is None:
            return ["%s: build on a slide with no sketch" % at]
        n = len(spec.get("shapes", []))
        return ["%s: sketch part %s does not exist (sketch has %d parts)" % (at, i, n)
                for i in value if not isinstance(i, int) or not 0 <= i < n]
    elif name == "items":
        n = len(slide.get("items", [])) if kind == "words" else 0
        return ["%s: term %s does not exist (slide has %d terms)" % (at, i, n)
                for i in value if not isinstance(i, int) or not 0 <= i < n]
    elif name in ("ask", "why"):
        if kind != "q":
            return ["%s: %s on a slide that is not a question" % (at, name)]
    elif name == "box":
        n = len(slide.get("boxes", [])) if kind == "screen" else 0
        if not isinstance(value, int) or not 0 <= value < n:
            return ["%s: box %s does not exist (slide has %d boxes)" % (at, value, n)]
    elif name == "line":
        n = len(slide.get("out", [])) if kind == "terminal" else 0
        if not isinstance(value, int) or not 0 <= value < n:
            return ["%s: line %s does not exist (slide has %d lines)" % (at, value, n)]
    return []


def check_text(text, at, what) -> list:
    problems = []
    if YEAR.search(text) or MONTH_DAY.search(text) or DAY_MONTH.search(text):
        problems.append("%s: %s has a date" % (at, what))
    if BETA.search(text):
        problems.append("%s: %s says Beta" % (at, what))
    m = REGIONS.search(text)
    if m:
        problems.append("%s: %s names a region (%s)" % (at, what, m.group(0)))
    if OUR_LAB.search(text):
        problems.append("%s: %s says 'in our lab'" % (at, what))
    return problems


def check_script(script: dict, unit_html: str, first_module: bool) -> list:
    problems = []
    sketches = script.get("sketches", {})
    slide = None
    slide_at = ""
    said = []  # narration of the cues on the current slide
    tested = False
    for si, step in enumerate(script.get("steps", []), 1):
        cues = step.get("cues", [])
        if not cues:
            problems.append("step %d cue 0: step has no cues" % si)
            continue
        for ci, cue in enumerate(cues, 1):
            at = "step %d cue %d" % (si, ci)
            say = cue.get("say", "")
            if not say.strip():
                problems.append("%s: cue has no say" % at)
            if cue.get("slide"):
                slide, slide_at, said = cue["slide"], at, []
                problems += check_slide(slide, sketches, unit_html, at)
                for s in slide_strings(slide) + sketch_text(sketches.get(slide.get("sketch"))):
                    problems += check_text(s, at, "slide text")
            elif ci == 1 or slide is None:
                problems.append("%s: first cue of a step needs a slide" % at)
            said.append(norm(say))
            problems += check_text(say, at, "narration")
            if UNIT_NUMBER.search(say):
                problems.append("%s: narration names %r; say the next module or its title"
                                % (at, UNIT_NUMBER.search(say).group(0)))
            if TESTED.search(say):
                tested = True
            if slide is not None and slide.get("type") in SHOW_KEYS:
                if slide.get("type") != "q":
                    for key in ("head", "sub", "tip", "text"):
                        text = norm(slide.get(key, ""))
                        if len(text.split()) >= 4 and text in norm(say):
                            problems.append("%s: narration on screen: %s %r is spoken word for word"
                                            % (at, key, slide[key]))
                for action in cue.get("do", []):
                    problems += check_action(action, slide, sketches, at)
    if first_module and not tested:
        problems.append("step 0 cue 0: the first module must say the course was tested; no cue says 'tested'")
    return problems
