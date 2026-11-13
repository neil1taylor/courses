"""A module's narration as a plain text file the owner edits in their own editor.

Format: two heading lines, then one "## <step title>" block per step with one "[<module>.<n>] <sentence>" line per
cue, n counted across the module. A line starting with ">" under a sentence is a comment on it.
"""
import re

import script as scripts

HINT = ("# Change the words after a tag. Don't change or remove the tags. "
        "To leave a comment, write a line starting with > under the sentence.")
_HEADING = re.compile(r"^#\s+\S+\s+(\d+):")
_TAG = re.compile(r"^\[(\d+)\.(\d+)\]\s*(.*)$")


def _squash(text) -> str:
    return " ".join(str(text).split())


def export_text(script, letter, number) -> str:
    title = script.get("title", "") if isinstance(script, dict) else ""
    blocks = ["# %s %d: %s\n%s" % (letter, number, title, HINT)]
    n = 0
    for step in script.get("steps") or []:
        lines = ["## %s" % (step or {}).get("title", "")]
        for cue in (step or {}).get("cues") or []:
            if isinstance(cue, dict):
                n += 1
                lines.append("[%d.%d] %s" % (number, n, _squash(cue.get("say", ""))))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def parse_text(text):
    """Returns (says by n, comments by n, problems)."""
    says, comments, problems = {}, {}, []
    module, last = None, None
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if i == 1:
            m = _HEADING.match(line)
            module = int(m.group(1)) if m else None
        if not line or line.startswith("#"):
            continue
        if line.startswith(">"):
            if last is None:
                problems.append("line %d: a comment must come under a sentence, and there is none above it" % i)
            else:
                comments.setdefault(last, []).append(line[1:].strip())
            continue
        m = _TAG.match(line)
        if not m:
            hint = "; was this line meant to be part of [%d.%d]?" % (module, last) if last and module else ""
            problems.append("line %d: no tag at the start%s" % (i, hint))
            continue
        mod, n, body = int(m.group(1)), int(m.group(2)), _squash(m.group(3))
        if module is not None and mod != module:
            problems.append("line %d: [%d.%d] has module number %d but this file is for module %d"
                            % (i, mod, n, mod, module))
            continue
        last = n
        if n in says:
            problems.append("line %d: [%d.%d] appears twice" % (i, mod, n))
        elif not body:
            problems.append("line %d: [%d.%d] has empty text" % (i, mod, n))
        else:
            says[n] = body
    return says, comments, problems


def apply_text(script, letter, number, says):
    """Write changed sentences into the script. Returns (refs changed, problems)."""
    changed, problems, seen = [], [], set()
    for n, (_, _, cue) in enumerate(scripts._cues(script), 1):
        seen.add(n)
        if n not in says:
            problems.append("[%d.%d] is missing from the file; the sentence was left as it was" % (number, n))
        elif _squash(says[n]) != _squash(cue.get("say", "")):
            cue["say"] = _squash(says[n])
            changed.append("%s %d.%d" % (letter, number, n))
    for n in sorted(set(says) - seen):
        problems.append("[%d.%d] is in the file but the module has no such sentence" % (number, n))
    return changed, problems
