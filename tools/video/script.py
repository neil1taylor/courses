"""Load and check a module script before any audio is made.

check_script returns one string per problem, "step <n> cue <m>: <what>", counting
from 1. A problem about a whole step uses cue 0; one about the whole script uses
step 0 cue 0. A problem about a slide is reported at the cue that starts the slide.
It never raises on a malformed script: it reports the malformation.
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
MAX_NARRATION = 4500
SKETCH_LIMITS = {  # slide type -> (max w, max h), from slide-rules.md
    "diagram": (960, 430), "statement": (960, 430), "title": (490, 365), "summary": (350, 365),
}

# Fields each slide type must have, as {field: kind}. Kinds: str, list, int, any.
REQUIRED = {
    "title": {"head": str, "sub": str},
    "diagram": {"head": str, "sketch": str},
    "statement": {"head": str},
    "q": {"head": str, "opts": list, "ok": int, "why": str},
    "tip": {"head": str, "tip": str},
    "words": {"head": str, "items": list},
    "summary": {"text": str, "next": str},
    "screen": {"head": str, "img": str, "boxes": list},
    "terminal": {"cmd": str, "out": (list, str)},
    "table": {"head": str, "cols": list, "rows": list},
    "score": {},
}
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
    "table": {"head", "table"},
    "score": {"head"},
}
# Keys that must be shown by the end of the slide (a question is shown by `ask`).
MUST_SHOW = {
    "title": {"head", "sub"}, "diagram": {"head"}, "statement": {"head"}, "tip": {"head", "tip"},
    "words": {"head"}, "summary": {"head", "next"}, "screen": {"head"},
    "table": {"head", "table"},
}
ACTIONS = {"show", "build", "items", "ask", "why", "box", "line", "row"}
MIN_TABLE_COLS, MAX_TABLE_COLS = 2, 4
MIN_TABLE_ROWS, MAX_TABLE_ROWS = 2, 6

MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December|"
          "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec")
# Month names count only when capitalised and followed by a day or a year.
MONTH_DAY = re.compile(r"\b(%s)\.?\s+\d" % MONTHS)
DAY_MONTH = re.compile(r"\b\d{1,2}(st|nd|rd|th)?\s+(%s)\b" % MONTHS)
YEAR_ANY = re.compile(r"\b20[2-3]\d\b")
YEAR_AFTER = re.compile(r"\b(in|since|until|by|from|during)\s+(19|20)\d\d\b", re.I)
BETA = re.compile(r"\bbeta\b", re.I)
REGIONS = re.compile(r"\b(us-south|us-east|eu-de|eu-gb|eu-es|jp-tok|jp-osa|au-syd|ca-tor|br-sao|dallas)\b", re.I)
OUR_LAB = re.compile(r"\bour lab\b|\bin our tests\b", re.I)
UNIT_NUMBER = re.compile(r"\b(unit|module)\s+(\d[\d.]*|(one|two|three|four|five|six|seven|eight|nine|ten)\b)", re.I)
UNIT_WORD = re.compile(r"\b(the|this) unit\b|\bclips?\b|\blessons?\b", re.I)
TESTED = re.compile(r"\btested\b", re.I)
TESTED_SENTENCE = "everything in this course was tested"
READ = re.compile(r"\bread\b", re.I)
PAST_READ = re.compile(r"\b(had|have|has|was|were|then|already|just) read\b", re.I)
TAG = re.compile(r"<[^>]+>")


def load_script(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def words(text) -> list:
    return TAG.sub(" ", str(text)).split()


def norm(text) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", TAG.sub(" ", str(text)).lower()).split())


def lines_of(out) -> list:
    return out.splitlines() if isinstance(out, str) else list(out)


def listed(value) -> list:
    """value if it is a list, else an empty list: a wrong kind is reported elsewhere."""
    return value if isinstance(value, list) else []


def shapes_of(spec) -> list:
    return listed(spec.get("shapes")) if isinstance(spec, dict) else []


def sketch_text(spec) -> list:
    out = []
    for shape in shapes_of(spec):
        if isinstance(shape, dict):
            out += [shape[k] for k in ("title", "detail", "text") if isinstance(shape.get(k), str)]
    return out


def slide_strings(slide) -> list:
    """Every string a learner sees on a slide, for the rules about what may be said.
    Terminal output and screenshots are left out: dates and names there are allowed."""
    out = [slide[k] for k in ("head", "sub", "tip", "text", "why", "next") if isinstance(slide.get(k), str)]
    out += [o for o in listed(slide.get("opts")) if isinstance(o, str)]
    for term in listed(slide.get("items")):
        out += [t for t in listed(term) if isinstance(t, str)]
    return out


def slide_words(slide, sketches) -> int:
    """Words counted against the limit of 20: head, sub, tip, text, answer options, sketch labels.
    The why line and the next line have their own limits."""
    parts = [slide[k] for k in ("head", "sub", "tip", "text") if isinstance(slide.get(k), str)]
    parts += [o for o in listed(slide.get("opts")) if isinstance(o, str)]
    if slide.get("sketch"):
        parts += sketch_text(sketches.get(slide["sketch"]))
    return sum(len(words(p)) for p in parts)


def fields_ok(slide, at) -> list:
    """Required fields of the right kind. Anything found here stops the deeper checks on the slide."""
    kind = slide.get("type")
    problems = []
    for field, want in REQUIRED[kind].items():
        v = slide.get(field)
        if v is None or (isinstance(v, str) and not v.strip()):
            problems.append("%s: %s slide has no %s" % (at, kind, field))
        elif isinstance(v, bool) or not isinstance(v, want):
            problems.append("%s: %s of a %s slide is the wrong kind of value" % (at, field, kind))
    if problems:
        return problems
    if kind == "words" and not all(isinstance(i, list) and len(i) == 2 and all(isinstance(t, str) for t in i)
                                   for i in slide["items"]):
        problems.append("%s: items must be [term, definition] pairs" % at)
    if kind == "q" and not all(isinstance(o, str) for o in slide["opts"]):
        problems.append("%s: opts must be strings" % at)
    if kind == "terminal" and not all(isinstance(o, str) for o in lines_of(slide["out"])):
        problems.append("%s: out must be strings" % at)
    if kind == "table":
        cols, rows = slide["cols"], slide["rows"]
        if not all(isinstance(c, str) for c in cols):
            problems.append("%s: cols must be strings" % at)
        for i, row in enumerate(rows):
            if not isinstance(row, list) or not all(isinstance(c, str) for c in row):
                problems.append("%s: row %d must be a list of strings" % (at, i))
            elif len(row) != len(cols):
                problems.append("%s: row %d has %d cells, the table has %d columns" % (at, i, len(row), len(cols)))
    if slide.get("sketch") is not None and not isinstance(slide["sketch"], str):
        problems.append("%s: sketch must be a name" % at)
    return problems


def check_slide(slide, sketches, unit_html, at) -> list:
    kind = slide.get("type")
    if kind not in SHOW_KEYS:
        return ["%s: slide type %r is not one the player can show" % (at, kind)]
    bad = fields_ok(slide, at)
    if bad:
        return bad
    problems = []
    for key in ("opts", "items"):
        if slide.get(key) is not None and not isinstance(slide[key], list):
            problems.append("%s: %s must be a list" % (at, key))
    name = slide.get("sketch")
    if name:
        spec = sketches.get(name)
        if spec is None:
            problems.append("%s: slide uses sketch %r, which is defined nowhere in sketches" % (at, name))
        elif spec.get("shapes") is not None and not isinstance(spec["shapes"], list):
            problems.append("%s: shapes of sketch %r must be a list" % (at, name))
        elif kind in SKETCH_LIMITS and isinstance(spec.get("w"), (int, float)) and isinstance(spec.get("h"), (int, float)):
            mw, mh = SKETCH_LIMITS[kind]
            if spec["w"] > mw or spec["h"] > mh:
                problems.append("%s: sketch %r is %sx%s, over the %d by %d limit for a %s slide"
                                % (at, name, spec["w"], spec["h"], mw, mh, kind))
    if kind == "words":
        items = slide["items"]
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
    if kind == "title" and len(words(slide["head"]) + words(slide["sub"])) > MAX_TITLE_WORDS:
        problems.append("%s: title slide text is over %d words" % (at, MAX_TITLE_WORDS))
    if kind == "summary" and len(words(slide["text"])) > MAX_SUMMARY_WORDS:
        problems.append("%s: summary sentence is over %d words" % (at, MAX_SUMMARY_WORDS))
    if kind == "tip" and len(words(slide["tip"])) > MAX_TIP:
        problems.append("%s: tip line is over %d words" % (at, MAX_TIP))
    if kind == "q":
        opts, ok = slide["opts"], slide["ok"]
        if not 2 <= len(opts) <= 4:
            problems.append("%s: question needs 2 to 4 options, has %d" % (at, len(opts)))
        if not 0 <= ok < len(opts):
            problems.append("%s: question has no ok option (ok is %r for %d options)" % (at, ok, len(opts)))
        for i, o in enumerate(opts):
            if len(words(o)) > MAX_OPTION:
                problems.append("%s: option %d is %d words, at most %d" % (at, i, len(words(o)), MAX_OPTION))
        if len(words(slide["why"])) > MAX_WHY:
            problems.append("%s: why line is over %d words" % (at, MAX_WHY))
    if kind == "screen" and slide["img"] not in unit_html:
        problems.append("%s: image %r is not used by the unit" % (at, slide["img"]))
    if kind == "terminal":
        n = len(lines_of(slide["out"]))
        if n > MAX_TERMINAL_LINES:
            problems.append("%s: terminal slide has %d lines, at most %d" % (at, n, MAX_TERMINAL_LINES))
    if kind == "table":
        nc, nr = len(slide["cols"]), len(slide["rows"])
        if not MIN_TABLE_COLS <= nc <= MAX_TABLE_COLS:
            problems.append("%s: table has %d column%s, needs %d to %d"
                            % (at, nc, "" if nc == 1 else "s", MIN_TABLE_COLS, MAX_TABLE_COLS))
        if not MIN_TABLE_ROWS <= nr <= MAX_TABLE_ROWS:
            problems.append("%s: table has %d row%s, needs %d to %d"
                            % (at, nr, "" if nr == 1 else "s", MIN_TABLE_ROWS, MAX_TABLE_ROWS))
    return problems


class SlideState:
    """What the cues have shown of one slide so far."""

    def __init__(self, slide, at, usable):
        self.slide, self.at, self.usable = slide, at, usable
        self.shown, self.built, self.items = set(), set(), set()
        self.asked = self.answered = False


def indices(value, limit, at, what, state_set) -> list:
    if not isinstance(value, list):
        return ["%s: %s needs a list of numbers" % (at, what)]
    out = []
    for i in value:
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < limit:
            out.append("%s: %s %s does not exist (slide has %d)" % (at, what, i, limit))
        else:
            state_set.add(i)
    return out


def check_action(action, st, sketches, at) -> list:
    slide, kind = st.slide, st.slide["type"]
    if not isinstance(action, list) or not action or not isinstance(action[0], str) or action[0] not in ACTIONS:
        name = action[0] if isinstance(action, list) and action else action
        return ["%s: action %r does not exist" % (at, name)]
    name, value = action[0], (action[1] if len(action) > 1 else None)
    if name == "show":
        if not isinstance(value, str) or value not in SHOW_KEYS[kind]:
            return ["%s: slide key %r does not exist on a %s slide" % (at, value, kind)]
        st.shown.add(value)
        if value == "head" and kind == "screen":
            st.shown.add("img")
    elif name == "build":
        spec = sketches.get(slide.get("sketch"))
        if spec is None:
            return ["%s: build on a slide with no sketch" % at]
        n = len(shapes_of(spec))
        return indices(value, n, at, "sketch part", st.built)
    elif name == "items":
        n = len(slide["items"]) if kind == "words" else 0
        st.shown.add("head")
        return indices(value, n, at, "term", st.items)
    elif name == "ask":
        if kind != "q":
            return ["%s: ask on a slide that is not a question" % at]
        st.asked = True
        st.shown.add("head")
    elif name == "why":
        if kind != "q":
            return ["%s: why on a slide that is not a question" % at]
        if st.asked:
            st.answered = True
    elif name in ("box", "line", "row"):
        if name == "box":
            n, ok_kind = (len(slide["boxes"]) if kind == "screen" else 0), "screen"
        elif name == "row":
            n, ok_kind = (len(slide["rows"]) if kind == "table" else 0), "table"
        else:
            n, ok_kind = (len(lines_of(slide["out"])) if kind == "terminal" else 0), "terminal"
        if kind != ok_kind:
            return ["%s: %s on a slide that is not a %s slide" % (at, name, ok_kind)]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < n:
            return ["%s: %s %s does not exist (slide has %d)" % (at, name, value, n)]
    return []


def finish_slide(st, sketches) -> list:
    """What the slide was supposed to show and never did."""
    if st is None or not st.usable:
        return []
    slide, kind, at, out = st.slide, st.slide["type"], st.at, []
    for key in sorted(MUST_SHOW.get(kind, ())):
        if key not in st.shown:
            out.append("%s: slide key %r is never shown" % (at, key))
    if kind == "q":
        if not st.asked:
            out.append("%s: question slide has no cue with ask" % at)
        elif not st.answered:
            out.append("%s: question slide has no cue with why after the ask" % at)
    spec = sketches.get(slide.get("sketch"))
    if spec:
        for i in range(len(shapes_of(spec))):
            if i not in st.built:
                out.append("%s: sketch part %d is never built" % (at, i))
    if kind == "words":
        for i in range(len(slide["items"])):
            if i not in st.items:
                out.append("%s: term %d is never revealed" % (at, i))
    return out


def check_text(text, at, what) -> list:
    problems = []
    if YEAR_ANY.search(text) or YEAR_AFTER.search(text) or MONTH_DAY.search(text) or DAY_MONTH.search(text):
        problems.append("%s: %s has a date" % (at, what))
    if BETA.search(text):
        problems.append("%s: %s says Beta" % (at, what))
    m = REGIONS.search(text)
    if m:
        problems.append("%s: %s names a region (%s)" % (at, what, m.group(0)))
    if OUR_LAB.search(text):
        problems.append("%s: %s says 'in our lab' or 'in our tests'" % (at, what))
    return problems


def check_narration(say, at, pronounce_read) -> list:
    problems = check_text(say, at, "narration")
    m = UNIT_NUMBER.search(say)
    if m:
        problems.append("%s: narration names %r; say the next module or its title" % (at, m.group(0)))
    m = UNIT_WORD.search(say)
    if m:
        problems.append("%s: narration says %r; say module or step" % (at, m.group(0)))
    m = PAST_READ.search(say)
    if m:
        problems.append("%s: past tense %r would be voiced 'reed'; rephrase" % (at, m.group(0)))
    elif READ.search(say) and not pronounce_read:
        problems.append("%s: narration says 'read' but the script has no pronounce for it" % at)
    return problems


def check_script(script: dict, unit_html: str, first_module: bool) -> list:
    if not isinstance(script, dict):
        return ["step 0 cue 0: the script is not a JSON object"]
    problems = []
    for key in ("course", "section", "title", "unit"):
        if not isinstance(script.get(key), str) or not script[key].strip():
            problems.append("step 0 cue 0: script has no %s" % key)
    if "clips" in script:
        problems.append("step 0 cue 0: script has a 'clips' key; the steps are called 'steps'")
    steps = script.get("steps")
    if not isinstance(steps, list) or not steps:
        problems.append("step 0 cue 0: script has no steps")
        steps = []
    sketches = script.get("sketches", {})
    if not isinstance(sketches, dict):
        problems.append("step 0 cue 0: sketches must be a name -> sketch map")
        sketches = {}
    sketches = {k: v for k, v in sketches.items() if isinstance(v, dict)}
    pronounce = script.get("pronounce", {})
    if not isinstance(pronounce, dict):
        problems.append("step 0 cue 0: pronounce must be a word -> spoken form map")
        pronounce = {}
    for word, spoken in pronounce.items():
        if not isinstance(spoken, str) or spoken != spoken.lower():
            problems.append("step 0 cue 0: pronounce %r must be lower-case plain words" % word)

    state = None
    tested = False
    narration = 0
    qs = []       # (at, slide) of each question slide, in order
    scores = []   # number of question slides before each score slide
    for si, step in enumerate(steps, 1):
        cues = step.get("cues") if isinstance(step, dict) else None
        if not isinstance(cues, list) or not cues:
            problems.append("step %d cue 0: step has no cues" % si)
            continue
        for ci, cue in enumerate(cues, 1):
            at = "step %d cue %d" % (si, ci)
            if not isinstance(cue, dict):
                problems.append("%s: cue is not an object" % at)
                continue
            say = cue.get("say")
            if not isinstance(say, str) or not say.strip():
                problems.append("%s: cue has no say" % at)
                say = ""
            narration += len(say)
            missing_slide = False
            if cue.get("slide") is not None:
                problems += finish_slide(state, sketches)
                sl = cue["slide"]
                if not isinstance(sl, dict):
                    problems.append("%s: slide is not an object" % at)
                    state = None
                else:
                    found = check_slide(sl, sketches, unit_html, at)
                    problems += found
                    state = SlideState(sl, at, sl.get("type") in SHOW_KEYS and not fields_ok(sl, at))
                    if sl.get("type") == "q":
                        qs.append((at, sl))
                    if sl.get("type") == "score":
                        scores.append(len(qs))
                    if state.usable:
                        for s in slide_strings(sl) + sketch_text(sketches.get(sl.get("sketch"))):
                            problems += check_text(s, at, "slide text")
            elif ci == 1:
                problems += finish_slide(state, sketches)
                state = None
                missing_slide = True
                problems.append("%s: first cue of a step needs a slide" % at)
            if "?" in say and not missing_slide and not (state and state.slide.get("type") == "q"):
                problems.append("%s: narration asks a question outside a question slide" % at)
            problems += check_narration(say, at, "read" in pronounce)
            if TESTED.search(say):
                tested = True
            if not first_module and TESTED_SENTENCE in norm(say):
                problems.append("%s: only the first module says everything in the course was tested" % at)
            if state is None or not state.usable:
                continue
            if state.slide["type"] not in ("q", "title"):
                for key in ("head", "sub", "tip", "text"):
                    text = norm(state.slide.get(key, ""))
                    if len(text.split()) >= 4 and text in norm(say):
                        problems.append("%s: narration on screen: %s %r is spoken word for word"
                                        % (at, key, state.slide[key]))
            do = cue.get("do", [])
            if not isinstance(do, list):
                problems.append("%s: do must be a list of actions" % at)
                continue
            for action in do:
                problems += check_action(action, state, sketches, at)
    problems += finish_slide(state, sketches)

    if first_module and not tested:
        problems.append("step 0 cue 0: the first module must say the course was tested; no cue says 'tested'")
    if narration > MAX_NARRATION:
        problems.append("step 0 cue 0: narration is %d characters, at most 4,500" % narration)
    n = len(qs)
    if not steps:
        return problems
    if not 3 <= n <= 5:
        problems.append("step 0 cue 0: module has %d questions, needs 3 to 5" % n)
    else:
        flags = [q[1].get("check") is True for q in qs]
        if flags != [False] * (n - 3) + [True] * 3:
            problems.append("step 0 cue 0: exactly the last three questions must have check true")
        if not any(c == n for c in scores):
            problems.append("step 0 cue 0: a score slide must follow the last check question")
    return problems
