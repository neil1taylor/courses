"""The review record: comments and approvals, saved to review/<slug>.json.

Shape: {"modules": {stem: {"approved": module hash | None, "seen": {ref: cue hash}}},
        "comments": [{"id", "ref", "say", "text", "open"}],
        "outline": {stem: {"approved": hash | None}},
        "edits": [{"id", "stem", "ref", "old", "new", "open"}]}
A reference is "<course letter> <module>.<cue>", both counted from 1; the cue count runs across the whole module.
Comments keep the sentence they were made on, so they stay with that sentence when the script moves it.
An edit is the owner's new wording for one sentence; it stays open until it is applied to the script.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import script as scripts


def _sha(text) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def empty_state() -> dict:
    return {"modules": {}, "comments": [], "outline": {}, "edits": []}


def load_state(path) -> dict:
    path = Path(path)
    if not path.is_file():
        return empty_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    for key, blank in empty_state().items():
        state.setdefault(key, blank)
    return state


def save_state(path, state) -> None:
    """Write to a temporary file in the same folder, then rename it over the record."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def cue_hash(cue) -> str:
    return _sha(str(cue.get("say", "")) + json.dumps([cue.get("slide"), cue.get("do")], sort_keys=True))


def module_hash(script) -> str:
    return _sha("".join(cue_hash(c) for _, _, c in scripts._cues(script)))


def outline_hash(module) -> str:
    return _sha(json.dumps(module, sort_keys=True))


def refs(script, letter, number) -> list:
    """One entry per cue: {ref, step, cue, say, hash, data}, with step and cue counted from 1."""
    out = []
    for n, (si, ci, cue) in enumerate(scripts._cues(script), 1):
        out.append({"ref": "%s %d.%d" % (letter, number, n), "step": si, "cue": ci,
                    "say": str(cue.get("say", "")), "hash": cue_hash(cue), "data": cue})
    return out


def _module(state, stem) -> dict:
    return state["modules"].setdefault(stem, {"approved": None, "seen": {}})


def mark_seen(state, stem, script, letter, number) -> None:
    _module(state, stem)["seen"] = {r["ref"]: r["hash"] for r in refs(script, letter, number)}


def approve(state, stem, script, letter, number) -> None:
    mark_seen(state, stem, script, letter, number)
    state["modules"][stem]["approved"] = module_hash(script)


def changed_refs(state, stem, script, letter, number) -> set:
    """The refs whose cue differs from the one stored at the last approval or mark as read."""
    seen = state["modules"].get(stem, {}).get("seen") or {}
    if not seen:
        return set()
    return {r["ref"] for r in refs(script, letter, number) if seen.get(r["ref"]) != r["hash"]}


def module_number(ref) -> int:
    """The module number in a reference such as "V 13.3"."""
    try:
        return int(ref.split(" ", 1)[1].split(".", 1)[0])
    except (IndexError, ValueError):
        return 0


def open_in_module(state, letter, number) -> list:
    return [c for c in state["comments"] if c["open"] and c["ref"].startswith(letter + " ")
            and module_number(c["ref"]) == number]


def module_status(state, stem, script, letter, number) -> str:
    if open_in_module(state, letter, number) or open_edits(state, stem):
        return "Has open comments"
    approved = state["modules"].get(stem, {}).get("approved")
    if approved is None:
        return "Not reviewed"
    return "Approved" if approved == module_hash(script) else "Changed since approved"


def add_comment(state, ref, say, text) -> int:
    new = max([c["id"] for c in state["comments"]], default=0) + 1
    state["comments"].append({"id": new, "ref": ref, "say": say, "text": text, "open": True})
    return new


def close_comments(state, ids) -> None:
    for c in state["comments"]:
        if c["id"] in set(ids):
            c["open"] = False


def attach_comments(comments, module_refs):
    """Open comments for one module by the ref of the cue they belong to now.

    A comment goes to the cue whose sentence is the one it was made on; if no cue says it any more, to the cue
    that still has its ref only when the comment has no sentence (a module comment). Otherwise it is an orphan.
    """
    by_say, by_ref = {}, {r["ref"]: r for r in module_refs}
    for r in module_refs:
        by_say.setdefault(r["say"], r)
    attached, orphans = {}, []
    for c in comments:
        if not c["open"]:
            continue
        target = by_say.get(c.get("say")) if c.get("say") else by_ref.get(c["ref"])
        if target:
            attached.setdefault(target["ref"], []).append(c)
        else:
            orphans.append(c)
    return attached, orphans


def comments_report(state) -> list:
    return ['%s  "%s"  %s' % (c["ref"], c.get("say", ""), c["text"]) for c in state["comments"] if c["open"]]


def open_edits(state, stem) -> dict:
    """The open edits for one module, by the original sentence they replace."""
    return {e["old"]: e for e in state.get("edits", []) if e["open"] and e["stem"] == stem}


def add_edit(state, stem, ref, old, new) -> int:
    """Record new wording for a sentence. A second edit of the same sentence replaces the first."""
    current = open_edits(state, stem).get(old)
    if current:
        current.update(new=new, ref=ref)
        return current["id"]
    edits = state.setdefault("edits", [])
    new_id = max([e["id"] for e in edits], default=0) + 1
    edits.append({"id": new_id, "stem": stem, "ref": ref, "old": old, "new": new, "open": True})
    return new_id


def edits_report(state) -> list:
    return ['%s  "%s"  ->  "%s"' % (e["ref"], e["old"], e["new"]) for e in state.get("edits", []) if e["open"]]


def apply_edits(state, stem, script):
    """Write the open edits for one module into its script. Returns (applied ids, skipped ids); an edit whose
    sentence the script no longer has is skipped and stays open."""
    cues = {str(c.get("say", "")): c for _, _, c in scripts._cues(script)}
    applied, skipped = [], []
    for old, e in open_edits(state, stem).items():
        if old in cues:
            cues[old]["say"] = e["new"]
            e["open"] = False
            applied.append(e["id"])
        else:
            skipped.append(e["id"])
    return applied, skipped
