"""A course outline as a plain text file the owner edits in their own editor.

Each module is a "## <letter> <n>: <title>" block. Every editable line starts with a tag:
[n.title], [n.oK] outcome, [n.fK] fact, [n.qK] check question, [n.qKa] to [n.qKd] its options and
[n.qKwhy] its answer line. The right option starts with "* ". A "source:" line under a fact is shown
for reference and not read back. A line starting with ">" is a comment on the tagged line above it.
"""
import re

HINT = ("# Change the words after a tag. Don't change or remove the tags. Put * before the right answer.\n"
        "# To leave a comment, write a line starting with > under the line it is about.")
_TAG = re.compile(r"^\[(\d+)\.(title|o\d+|f\d+|q\d+(?:[a-d]|why)?)\]\s*(.*)$")
LETTERS = "abcd"


def _squash(text) -> str:
    return " ".join(str(text).split())


def _items(m):
    """(key, label, text) for every editable line of one module, in file order."""
    yield "title", "title", m.get("title", "")
    for k, o in enumerate(m.get("outcomes") or [], 1):
        yield "o%d" % k, "outcome %d" % k, o
    for k, f in enumerate(m.get("facts") or [], 1):
        yield "f%d" % k, "fact %d" % k, (f or {}).get("text", "")
    for k, c in enumerate(m.get("checks") or [], 1):
        yield "q%d" % k, "check %d" % k, c.get("head", "")
        for j, o in enumerate(c.get("opts") or []):
            yield "q%d%s" % (k, LETTERS[j]), "check %d option %s" % (k, LETTERS[j]), ("* " if j == c.get("ok") else "") + o
        yield "q%dwhy" % k, "check %d answer" % k, c.get("why", "")


def label(module, key) -> str:
    return next((lab for k, lab, _ in _items(module) if k == key), key)


def export_outline(outline, letter) -> str:
    blocks = ["# %s outline: %s\n%s" % (letter, outline.get("course", ""), HINT)]
    for n, m in enumerate(outline.get("modules") or [], 1):
        lines = ["## %s %d: %s" % (letter, n, m.get("title", ""))]
        facts = m.get("facts") or []
        for key, _, text in _items(m):
            if key == "o1":
                lines += ["", "# Outcomes"]
            elif key == "f1":
                lines += ["", "# Facts"]
            elif key == "q1" or (key.startswith("q") and key[1:].isdigit()):
                lines += ["", "# Check question %s" % key[1:]]
            lines.append("[%d.%s] %s" % (n, key, _squash(text)))
            if key.startswith("f"):
                lines.append("    source: %s" % (facts[int(key[1:]) - 1] or {}).get("source", ""))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def parse_outline(text):
    """Returns (values by (n, key), comments by (n, key), problems)."""
    values, comments, problems, last = {}, {}, [], None
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("source:"):
            continue
        if line.startswith(">"):
            if last is None:
                problems.append("line %d: a comment must come under a tagged line, and there is none above it" % i)
            else:
                comments.setdefault(last, []).append(line[1:].strip())
            continue
        m = _TAG.match(line)
        if not m:
            hint = "; was this line meant to be part of [%d.%s]?" % last if last else ""
            problems.append("line %d: no tag at the start%s" % (i, hint))
            continue
        key, body = (int(m.group(1)), m.group(2)), _squash(m.group(3))
        last = key
        if key in values:
            problems.append("line %d: [%d.%s] appears twice" % ((i,) + key))
        elif not body or body == "*":
            problems.append("line %d: [%d.%s] has empty text" % ((i,) + key))
        else:
            values[key] = body
    return values, comments, problems


def apply_outline(outline, letter, values):
    """Write changed lines into the outline. Returns (parts changed, problems)."""
    changed, problems, seen = [], [], set()
    for n, m in enumerate(outline.get("modules") or [], 1):
        keys = [k for k, _, _ in _items(m)]
        seen.update((n, k) for k in keys)
        missing = [k for k in keys if (n, k) not in values]
        for k in missing:
            problems.append("[%d.%s] is missing from the file; it was left as it was" % (n, k))
        get = lambda k, old: values.get((n, k), old)  # noqa: E731
        if "title" not in missing and _squash(get("title", "")) != _squash(m.get("title", "")):
            m["title"] = get("title", "")
            changed.append("%s %d title" % (letter, n))
        for k, o in enumerate(m.get("outcomes") or [], 1):
            if _squash(get("o%d" % k, o)) != _squash(o):
                m["outcomes"][k - 1] = get("o%d" % k, o)
                changed.append("%s %d outcome %d" % (letter, n, k))
        for k, f in enumerate(m.get("facts") or [], 1):
            if _squash(get("f%d" % k, f["text"])) != _squash(f["text"]):
                f["text"] = get("f%d" % k, f["text"])
                changed.append("%s %d fact %d" % (letter, n, k))
        for k, c in enumerate(m.get("checks") or [], 1):
            where = "%s %d check %d" % (letter, n, k)
            opts, stars = [], []
            for j, o in enumerate(c.get("opts") or []):
                text = get("q%d%s" % (k, LETTERS[j]), ("* " if j == c.get("ok") else "") + o)
                if text.startswith("*"):
                    stars.append(j)
                    text = text[1:].strip()
                opts.append(text)
            if len(stars) != 1:
                problems.append("%s has %s; it was left as it was"
                                % (where, "no answer marked with *" if not stars else "%d answers marked with *" % len(stars)))
                continue
            new = dict(c, head=get("q%d" % k, c["head"]), opts=opts, ok=stars[0], why=get("q%dwhy" % k, c["why"]))
            if any(_squash(new[f]) != _squash(c[f]) for f in ("head", "why")) or new["opts"] != c["opts"] or new["ok"] != c["ok"]:
                c.update(new)
                changed.append(where)
    for n, k in sorted(set(values) - seen):
        problems.append("[%d.%s] is in the file but the outline has no such line" % (n, k))
    return changed, problems
