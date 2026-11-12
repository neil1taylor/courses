# Reviewing course content before audio: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The owner reviews and approves a course's outline, a sample module and every script, with its slides, on a local review page before any audio is made. Checks catch each fault the owner has already reported.

**Architecture:**
- **Review server.** `tools/review.py` builds a course's module pages without voice into a scratch folder and serves a review page from it at `http://127.0.0.1:8770/`.
- **Slide pictures.** The review page shows each cue's slide as a lazy-loaded iframe of the real module page in a new still mode (`?still=<step>.<cue>`), so the picture is exactly what the learner sees.
- **Comments and approvals.** These are saved by the server to `review/<slug>.json` in the courses repo, which is the approval record. A command-line mode prints the open comments for the agent fixing them.
- **New checks.** These go in `tools/video/script.py`.
- **Outline.** The course outline is a new `video/outline.json` in each source repo, checked by `tools/video/outline.py`.

**Tech Stack:** Python 3 standard library (`http.server`, `json`, `hashlib`), pytest, plain JavaScript, Node for the player tests.

**Spec:** `design/2026-11-12-content-approval-spec.md`. Context: `design/2026-11-12-video-courses-design.md` and its plan.

## Global Constraints

- The server binds 127.0.0.1 only, port 8770. No page loads anything from a CDN.
- References read `<course letter> <module>.<sentence>`. The letters are V Cyber Vault, B Backup and Recovery, N VPC and R ROVS. Module counts from 1 in course order. Sentence counts from 1 across the whole module, not per step. For example, "V 13.3".
- A cue's hash is sha1 of its `say` plus the JSON of its slide and `do`, sorted keys, first 12 hex characters. "Changed since last look" compares this hash with the one stored when the owner last approved, or last marked the module read.
- `review/<slug>.json` is committed; it is the record of what was approved. Shape: `{"modules": {"<unit stem>": {"approved": "<module hash>"|null, "seen": {"<ref>": "<cue hash>"}}}, "comments": [{"id": int, "ref": str, "text": str, "open": bool}], "outline": {"<unit stem>": {"approved": "<hash>"|null}}}`. A module hash is sha1 of its cue hashes joined, first 12.
- The page and its words follow the owner's style: plain English, no jargon in labels ("Approve module", "Mark as read", "Comment").
- The new checks must not fail any of today's 17 Cyber Vault scripts. Each must fail the matching pre-fix script (Task 2).
- Commits: no trailers; issues and PRs never mention Claude or AI; one issue per task, closed by its PR.

## Review Focus

1. The owner comments on a cue, then the script changes so that cue moves: the comment stays attached to its text. Store the cue's `say` with the comment and show it. Test in Task 4.
2. A module approved, then one sentence changed: the module shows as "changed since approved" and only that sentence is marked. Test in Task 4.
3. A question slide in still mode: it shows the options with the right one marked, not a waiting question. Test in Task 1.
4. The server is stopped and started again: no comment or approval is lost (written to disk on every change, atomically). Test in Task 4.
5. A script that doesn't pass the checks: the review page still opens, listing the problems at the top of the module, so the owner never reviews a script the agent hasn't seen fail. Test in Task 4.

---

### Task 1: Still mode in the player

**Files:** Modify `tools/video/player/player.js`, `tools/video/player/player.css`. Test `tools/video/player/test/player.test.mjs`.

**Interfaces:** Produces `stillAt(search) -> [step, cue] | null`. It parses `?still=3.2` into zero-based `[2, 1]`, and returns null when the value is absent or malformed. Module pages opened with `?still=s.q` show only the canvas (class `still` on `body`), at that cue's finished state, with no audio and no controls.

- [ ] Write failing node tests:
  - `stillAt("?still=3.2")` deep-equals `[2,1]`.
  - `stillAt("")`, `stillAt("?still=x")` and `stillAt("?still=0.1")` are null.
- [ ] Implement `stillAt`. In `boot`, when it returns a cue:
  - call `goto(s, q, false)` and apply the cue's own actions;
  - if the slide is a question, show its options with the right one marked, as after answering, without counting a score;
  - add `still` to `body`.
- [ ] CSS: `body.still` hides the side panel, controls, captions and big play button; the stage fills the window.
- [ ] Check by hand in Chrome on one built module at `?still=` for a diagram cue, a screen cue and a question cue. Run `node --test tools/video/player/test/`.
- [ ] Commit.

### Task 2: New script checks

**Files:** Modify `tools/video/script.py`. Create `tools/video/rejected.txt`. Test `tests/test_script.py`, with fixtures `tests/fixtures/prefix/`.

**Interfaces:**
- **Consumes:** `check_script` (unchanged signature, more problems).
- **Produces:**
  - `teaching_cue(script, step, cue) -> (step, cue) | None`: the earlier cue in the same module whose narration best teaches the question's answer.
  - `notes(script) -> list[str]`: advisory lines for a reader, not failures, in the form "step n cue m: first mention of 'the X'". The review page shows these notes.

- [ ] Copy the pre-fix fixtures from the cohesity repo with `git -C ~/Projects/cohesity show <ref>:<path>`:
  - `m1-u4-two-products-one-name.json` at `ae63234` (question before teaching), with its unit page `course/vault/m1-u4-two-products-one-name.html` at the same ref;
  - the script at `ae63234` holding "Four items stay out of the plan" (find it with `git grep` at that ref), with its unit page.
- [ ] Write failing tests:
  - `check_script` on the m1-u4 pre-fix fixture includes a problem containing "asked before it is taught".
  - On the "Four items" fixture it includes "rejected wording".
  - Every script in `~/Projects/cohesity/course/vault/video/` at today's main gives no new problems; skip if the folder is absent.
  - `teaching_cue` on today's m1-u4 returns a cue earlier than each question.
- [ ] Implement:
  - **Question taught first.** Take the content words of the right option plus the `why` (lower case, at least 4 letters, minus a small stop list). A cue in the same module before the question teaches it when its `say` contains at least half of those words, and at least two. No such cue gives "step n cue m: question asked before it is taught".
    - "Check yourself" questions are included.
    - Tune the threshold until both tests pass, and write the final rule in the docstring.
  - **Rejected wording.** `rejected.txt` holds one case-insensitive regex per line, with `#` comments. Seed it with:
    - `^(two|three|four|five|six) (items|things|points|steps|parts) (stay|are|remain)\b`, matched at sentence start;
    - the rejected lines listed in `~/.claude/skills/blog-writing/references/course-text.md` that can be written as a pattern.

    A match gives "step n cue m: rejected wording: '<text>'".
  - **First mentions.** These are notes, not problems: the first time "the <word> (key|file|setting|list|window|board|bucket|endpoint)" appears in a module where no earlier sentence names that word.
- [ ] Run `python3 -m pytest tests -q`, then commit.

### Task 3: The course outline

**Files:** Create `tools/video/outline.py`. Test `tests/test_outline.py`, with fixture `tests/fixtures/outline.json`.

**Interfaces:** Produces `check_outline(outline: dict, unit_stems: list[str]) -> list[str]` and `load_outline(path) -> dict`.

Shape of `video/outline.json`: `{"course": str, "modules": [{"unit": "<unit stem>", "title": str, "outcomes": [str], "facts": [{"text": str, "source": str}], "checks": [{"head": str, "opts": [str], "ok": int, "why": str}]}]}`.

- [ ] Write failing tests. Each must return a problem naming the module:
  - a module with fewer than 2 outcomes;
  - a module with no facts;
  - a fact with an empty source;
  - a module without exactly 3 checks;
  - a check whose `ok` is out of range;
  - a unit stem with no unit page;
  - a unit page with no module.

  A good fixture gives `[]`.
- [ ] Implement, reusing `script.py`'s limits for option and `why` length and its date and Beta checks on all text.
- [ ] Run the tests, then commit.

### Task 4: The review page and server

**Files:**
- Create `tools/review.py` (command line and server).
- Create `tools/video/review_page.py` (HTML).
- Create `tools/video/review_state.py` (load, save, hashes, comments).
- Test `tests/test_review.py`.
- Add `review/.gitkeep`.

**Interfaces:**
- **Consumes:** `build.load_video`, `build.write_video` with `voice.offline_speaker()` (writes pages without Watson); `script.check_script`, `script.teaching_cue`, `script.notes`; `outline.check_outline`; `?still=` from Task 1.
- **Produces:**
  - `python3 tools/review.py <slug>` builds into `<scratch>/review-<slug>/` and serves the review page.
  - `python3 tools/review.py <slug> --comments` prints the open comments as `<ref>  "<sentence>"  <comment>`.
  - `python3 tools/review.py <slug> --close <id> [<id>...]` closes comments.
  - Server routes:
    - `GET /`: the course page, listing modules with status Approved, Changed since approved, Has open comments or Not reviewed;
    - `GET /m/<stem>`: one module;
    - `GET /outline`;
    - `POST /api/comment {ref, say, text}`;
    - `POST /api/approve {stem}`;
    - `POST /api/seen {stem}`;
    - `POST /api/approve-outline {stem}`;
    - static files from the build folder.

The module page has these parts:
- At the top: the check problems and notes (Task 2, Review Focus 5).
- Then one row per cue:
  - the reference ("V 13.3");
  - the sentence;
  - a 480 by 270 still iframe (`loading="lazy"`) when the cue has a slide or actions;
  - for a question, the teaching sentence's reference and text;
  - a "Changed" mark when the cue's hash differs from the seen hash;
  - the open comments, each with its stored sentence;
  - a comment box.
- At the foot: "Approve module" and "Mark as read".

The outline page shows each module's outcomes, facts with sources, and checks with the right answer marked. It has a comment box per module (ref `<letter> <module>.0`) and "Approve outline for this module".

- [ ] Write failing tests:
  - state round-trip through save and load;
  - the save is atomic (written to a temp file, then renamed);
  - cue and module hashes are stable, and change when one character of `say` changes;
  - refs number sentences across steps;
  - status logic for each of the four states;
  - `--comments` output format;
  - the rendered module page contains the ref, the iframe `src` with `?still=`, the teaching reference for a question, and the problems block for a script with problems.

  Use `tests/fixtures/good.json` and a copy with one changed `say`.
- [ ] Implement. Escape all script text in HTML, and give the page the dark look of `player.css`. A small inline script posts comments and approvals and reloads the page.
- [ ] Run `python3 -m pytest tests -q`.
- [ ] Run `python3 tools/review.py vault`, open it in Chrome, and leave and close one test comment, then remove it from `review/vault.json`.
- [ ] Commit.

### Task 5: The course-video skill uses the three approvals

**Files:** In `~/Projects/claude-skills` (worktree, pull request): `skills/course-video/SKILL.md` and its reader prompt.

- [ ] Add the workflow:
  1. Write the outline and serve it for approval.
  2. Write one sample module (with a diagram, a screenshot and a question); serve it; after approval voice only that module.
  3. Write batches of about five; serve them; fix comments with `--comments` and `--close`.
  4. Voice and publish only approved modules.

  Add the rule that every new owner comment is either a one-off fix or a new rule. A new rule is added to the skill and to `rejected.txt` or `script.py` in the same change, then run across modules already written.
- [ ] Add to the cold reader's prompt:
  - check each fact against the approved outline;
  - check each tip slide against normal behaviour;
  - check each "but", "only" and "unlike" states the true condition;
  - read the first-mention notes.
- [ ] Commit, open a pull request, merge.

### Task 6: Trial on Cyber Vault

**Files:** Create `course/vault/video/outline.json` in the cohesity repo (worktree, pull request), written from the 17 current scripts and their unit pages. Create `review/vault.json` in the courses repo.

- [ ] Write the outline. Each module's three checks are its "Check yourself" questions. Each fact's source is the unit page, or the test record in `cyber-vault/` for test results.
- [ ] `check_outline` gives `[]`; `python3 tools/review.py vault` serves both pages with no problems.
- [ ] Leave the server running in the background and give the owner the link, so they can try the page itself.

## Rulings during the build

- The "question asked before it is taught" check is not automated. In the pre-fix Cyber Vault module the owner flagged, the answer had already been stated in passing two sentences before the question. The fault was a question opening a step with the teaching only in passing, which word matching can't tell apart from scenario questions in today's approved scripts. Instead, the review page shows each question beside the sentence that teaches it (`teaching_cue`), and the cold reader checks it. Cost if wrong: the owner may still see a badly placed question, but on the review page, before any audio.
