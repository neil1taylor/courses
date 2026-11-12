# Narrated video courses: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn every unit of the four published courses into a narrated module played in a Pluralsight-style player on neil1taylor.github.io/courses, starting with Cyber Vault.

**Architecture:** A module script (JSON) lives beside each unit in its source repo. `tools/video/` in the courses repo checks scripts, voices them with Watson through demo_videos' `narrate.Speaker`, and writes one static page per module plus a course contents page. One shared player (JS and CSS, from the approved trial) draws the slides with rough.js and plays the audio.

**Tech Stack:** Python 3 (standard library, pytest), ffmpeg, IBM Watson Text to Speech (Standard plan), plain JavaScript, rough.js, Node (for the player's unit tests only).

**Spec:** `design/2026-11-12-video-courses-design.md`. Trial (the reference build): `/private/tmp/claude-501/-Users-neiltaylor-Projects-rovs-tutorials/f3aa05c3-29fa-491b-8f00-433add9e3834/scratchpad/vault-video/` (`script.json`, `synth.py`, `build.py`, `player.js`, `player.css`). Copy it into the repo in Task 2 before that folder is lost.

## Global Constraints

- Voice `en-GB_GeorgeNatural`; playback rate 0.92 with pitch kept; 0.8 s gap after each cue plus the cue's `hold`.
- Audio: mp3, 48 kbps, mono. File name: first 16 hex characters of the cached wav's hash, plus `.mp3`.
- Canvas 1920 by 1080; slide padding 96px 120px 100px; body text at least 44px, labels at least 36px, headlines 56 to 72px (title 110px, statement 88px).
- At most 20 words on a slide (headline plus body; sketch labels count). At most 4 terms on a words slide.
- Captions are off when a module opens.
- No dates, no "Beta", no region availability, no time-limited offers in narration or slide text. Dates inside screenshots and command output are fine and are not read out.
- "in our lab" appears nowhere. Each course's first module says once that everything in the course was tested.
- Narration never names a unit or module number ("unit 1.1", "module 3"); it says "the next module" or names it.
- Learner-facing words: course, section, module, step. "Cue" is internal.
- No CDN: rough.js and fonts are served from the repo.
- Commits: no Co-Authored-By or other trailers; issues and PRs never mention Claude or AI. One issue per task, closed by its PR.
- The voice rules are the blog-writing skill's `references/course-text.md`; the course-video skill (Task 1) points to it and does not copy it.

## Review Focus

1. A learner on a phone (about 400px wide): the canvas scales, the side panel stacks below, the answer cards stay tappable. Test in Task 2.
2. A learner who seeks or clicks the transcript while a question is waiting: the question resets cleanly, the score counts each check question once. Test in Task 2.
3. A cue whose words change by one character: only that cue's audio is remade, and stale mp3s are removed from the published folder. Test in Task 4.
4. A script that names a slide part, image or term that does not exist: the check fails with the step and cue named, not a blank slide at play time. Test in Task 3.
5. A learner returning later: completed modules show as done on the contents page and in the side panel. Test in Task 2.

---

### Task 1: The course-video skill

**Files:**
- Create (claude-skills repo, worktree from `origin/main`): `skills/course-video/SKILL.md`, `skills/course-video/references/slide-rules.md` (from `design/slide-research.md` section 3 and the trial's sizes), `skills/course-video/references/script-format.md`
- Link: `~/.claude/skills/course-video` -> the repo folder (as the other skills are linked)

**Interfaces:**
- Produces: the rules every later task's script writer follows: structure (course, section, module, step), slide types and their limits, the script format (Task 3 validates it), the checklist (same facts as the unit, voice, nothing that dates it, slide word limits, every person introduced), how to build and look at a module, and a pointer to `blog-writing/references/course-text.md` for the voice.

- [ ] **Step 1: Baseline.** Give a fresh subagent only the unit `~/Projects/cohesity/course/vault/m1-u1-the-attacker-who-holds-your-backup-keys.html` and the trial `script.json` as an example, and ask it for a module script. Record what it gets wrong against the spec (expected: copies narration onto slides, quotes unit numbers, keeps "in our lab" or dates, more than 20 words a slide).
- [ ] **Step 2: Write the skill** to close each recorded failure. `SKILL.md` under 300 lines; description starts "Use when making, changing or reviewing a narrated video module of a course on neil1taylor.github.io/courses".
- [ ] **Step 3: Re-run** the Step 1 task with the skill loaded; each recorded failure is gone. Fix and repeat until it is.
- [ ] **Step 4: Commit, PR, merge** in claude-skills (`git -C <wt> push` as its own command; `gh pr merge <n> --repo neil1taylor/claude-skills --squash --delete-branch`).

### Task 2: The player and the module page in the courses repo

**Files:**
- Create: `tools/video/player/player.js`, `tools/video/player/player.css` (from the trial), `tools/video/page.py`, `tools/video/player/test/player.test.mjs`, `tests/test_page.py`
- Assets: rough.js and the fonts copied from `~/Projects/cohesity/course/assets` to `docs/video-assets/` by the build.

**Interfaces:**
- Consumes: a timeline dict: the script (Task 3 format) with `dur` (seconds, float) and `audio` (relative path) added to every cue.
- Produces: `render_module(timeline: dict, course: dict, index: int, total: int, prev_href: str | None, next_href: str | None) -> str` (full HTML page); `render_contents(course: dict, modules: list[dict]) -> str` where each module dict has `title`, `section`, `href`, `minutes`. `course` has `slug`, `title`.

- [ ] **Step 1: Failing tests** in `tests/test_page.py`:
  - `test_module_page_has_module_n_of_total`: `"Module 3 of 17"` in the page.
  - `test_captions_off_by_default`: the page contains `class="cc off"` and the CC button has no `on` class.
  - `test_no_cdn`: no `http` in any `src=` or `href=` of `<script>`/`<link>`.
  - `test_step_buttons_say_step`: `aria-label="Previous step"` and `"Next step"` present; the word `clip` is in no visible text or label.
  - `test_contents_groups_by_section`: two modules in section "Start here" and one in "The threat" give two section headings in order, with the module links under them.
- [ ] **Step 2: Failing player tests** in `player.test.mjs` (Node, `node --test`), with the pure functions exported from `player.js` under a `module.exports` guard:
  - `cueAt(timeline, seconds)` returns `{step, cue}` and clamps past the end.
  - `scoreOf(answers, timeline)` counts only check questions, each once, after an answer is changed by a seek and re-answered.
  - `progressKey(courseSlug)` is `"courses-video:" + slug`; `markDone(storage, slug, module)` then `doneModules(storage, slug)` returns it, and both survive storage that throws.
- [ ] **Step 3: Implement** `page.py` from the trial's `build.py` shell and the player from the trial, adding: "Module n of N", captions off, autoplay to `next_href`, completion in `localStorage` through `markDone`, keyboard (space play/pause, left/right one cue), and the phone layout at max-width 900px.
- [ ] **Step 4: Run** `pytest tests/test_page.py -q` and `node --test tools/video/player/test/` — all pass.
- [ ] **Step 5: Look.** Render the trial timeline with `render_module` into a scratch folder, serve it on 127.0.0.1, and check in Chrome at 1920x1080 and at 400px wide: every slide type renders, the answer cards fit, nothing overflows. Save screenshots in the PR.
- [ ] **Step 6: Commit, PR, merge.**

### Task 3: The script check

**Files:**
- Create: `tools/video/script.py`, `tests/test_script.py`, `tests/fixtures/` (a good script and one bad script per rule)

**Interfaces:**
- Produces: `load_script(path: Path) -> dict`; `check_script(script: dict, unit_html: str, first_module: bool) -> list[str]`, each problem as `"step <n> cue <m>: <what>"`, empty when clean. Script fields: `course`, `section`, `title`, `unit` (source file name), `sketches` (name -> spec), `steps: [{title, cues: [{slide?, say, do?, hold?}]}]`. The trial's `clips` key is renamed `steps`, `module` renamed `section`, `unit` (title) renamed `title`.

- [ ] **Step 1: Failing tests**, one per rule, each with its fixture:
  - more than 20 words on a slide; a words slide with 5 terms
  - a date (`\b(19|20)\d\d\b`, month names followed by a number), `Beta`, `us-south`/`Dallas`/`eu-de` used as availability, "in our lab" anywhere
  - `unit \d` or `module \d` in narration
  - a `do` action naming a sketch part, slide key or image that does not exist
  - a step with no cues; a question with no `ok` option; `slide.text` repeated word for word in `say` (narration on screen)
  - `first_module=True` and no cue says the course was tested
  - the good fixture returns `[]`
- [ ] **Step 2: Run** `pytest tests/test_script.py -q` — all fail.
- [ ] **Step 3: Implement** `check_script`. Words on a slide: strip tags, count `head`, `sub`, `tip`, `text`, option text and sketch titles and details shown on that slide.
- [ ] **Step 4: Run** — all pass. Run it on the trial script (renamed fields): it returns `[]` or only real problems, which you fix in the script.
- [ ] **Step 5: Commit, PR, merge.**

### Task 4: Voicing with a cache

**Files:**
- Create: `tools/video/voice.py`, `tests/test_voice.py`

**Interfaces:**
- Consumes: `narrate.Speaker(voice).wav(text) -> str` (path to a cached wav) and `narrate.spoken(text, say)`, `pronunciation.load(pronunciation.file_path())`, from `~/Projects/demo_videos/scripts` (put on `sys.path`; `settings` must be imported with the cwd at the demo_videos root).
- Produces: `voice_script(script: dict, audio_dir: Path, speaker) -> dict` (the timeline: the script with `dur` and `audio` on every cue) and `prune_audio(audio_dir: Path, timelines: list[dict]) -> list[Path]` (deletes and returns mp3s no timeline uses).

- [ ] **Step 1: Failing tests** with a fake speaker that writes a 1-second silent wav and counts calls:
  - two cues with the same words make one call and share one mp3
  - changing one cue's words makes exactly one new call
  - the mp3 is 48 kbps mono (`ffprobe` shows `bit_rate=48000`, `channels=1`)
  - `prune_audio` deletes an mp3 no timeline names and keeps the rest
- [ ] **Step 2: Run** — all fail.
- [ ] **Step 3: Implement.** Pronunciation comes only from the shared file (`$DEMO_CLIPS/pronunciation.txt`); no word rules in this code.
- [ ] **Step 4: Add the "read" rule** to `~/Projects/demo_videos-clips/pronunciation.txt`: `read = <phoneme alphabet="ipa" ph="ɹiːd">read</phoneme>`. That file is the owner's data, not a repo; add the one line only. Script writers spell past-tense "read" so it is not voiced as "reed" (the skill from Task 1 says how).
- [ ] **Step 5: Run** — all pass. Commit, PR, merge.

### Task 5: Screen and terminal slides

**Files:**
- Modify: `tools/video/player/player.js`, `player.css`, `tools/video/script.py`, tests in both suites.

**Interfaces:**
- Produces two slide types. `screen`: `{type:"screen", head, img, boxes:[[x,y,w,h] in image pixels]}`; action `box <i>` outlines box i in blue (earlier boxes grey). `terminal`: `{type:"terminal", cmd, out:[lines], max 8}`; action `line <i>` turns line i blue.

- [ ] **Step 1: Failing tests:** `check_script` rejects a terminal slide with 9 lines, a `box` index past the list, and an `img` the unit does not use; `player.test.mjs` checks `boxRect(box, imgSize, frameSize)` scales a box to the displayed image (letterboxed).
- [ ] **Step 2: Run** — fail. **Step 3: Implement.** The image fills the slide below the headline, scaled to fit. **Step 4: Run** — pass.
- [ ] **Step 5: Look** in Chrome with a screenshot from `m2-u2-create-a-vault.html` and a command from `m4-u2`. Commit, PR, merge.

### Task 6: The site build makes the video courses

**Files:**
- Modify: `tools/build.py`, `home/index.html`, `README.md`; Create: `tests/test_build_video.py`

**Interfaces:**
- Consumes: Tasks 2 to 5. Each source has a `video/` folder; a module's file name is its unit's file name with `.json`.
- Produces: `docs/<slug>/video/index.html` (contents), `docs/<slug>/video/<unit name>.html`, `docs/<slug>/video/audio/*.mp3`. A dict `VIDEO = {"vault": {"title": ..., "source": Path, "live": False}, ...}`; `live` decides whether the home page links the video version or the interactive one. Today Cyber Vault is published inside the backup course at `docs/backup/course/vault/`; its video version goes at `docs/vault/video/` (slug `vault`), and the others at `docs/rovs/video/`, `docs/vpc/video/`, `docs/backup/video/`.

- [ ] **Step 1: Failing tests** with two fixture scripts and a fake speaker: the build writes both pages and the contents page; it stops with the problems listed when `check_script` finds any; with `live: False` the home page still links the interactive course; modules are ordered by unit file name, and a section heading appears when `section` changes.
- [ ] **Step 2: Run** — fail. **Step 3: Implement.** `--no-voice` skips Watson and fails if any cue lacks cached audio. **Step 4: Run** — pass. Commit, PR, merge.

### Task 7: Cyber Vault module 1 through the pipeline

**Files:** Create `~/Projects/cohesity/course/vault/video/m0-u1-why-backups-need-a-vault.json` from the trial script (renamed fields, Task 3).

- [ ] **Step 1:** `check_script` returns `[]`. **Step 2:** build the site; the module plays end to end in Chrome, with the same slides and voice as the approved trial. **Step 3:** PR in cohesity (script) and in courses (built `docs/`), merge both. Nothing links to it yet (`live: False`).

### Task 8: Cyber Vault modules 2 to 5, then the owner's review

- [ ] **Step 1:** Write the scripts for the four next units with the course-video skill, fixing each unit in the same PR where its text breaks a Global Constraint. **Step 2:** each passes `check_script`; a cold reader on a different model reads each against its unit and the voice guide, and every line it flags is fixed. **Step 3:** build, look at every slide in Chrome. **Step 4: Stop and ask the owner to watch modules 2 to 5.** Fold their feedback into the skill (Task 1's repo) as well as the scripts before Task 9.

### Task 9: Cyber Vault modules 6 to 17, and the switch

- [ ] Same steps as Task 8 for the remaining 12 units. Then ask the owner to approve the course. On approval set `VIDEO["vault"]["live"] = True`, rebuild, merge.

### Tasks 10 to 12: Backup and Recovery, VPC, ROVS

- [ ] One task per course, in that order, each with Task 8's early review after its first four modules and Task 9's approval before `live` is set. The first module of each course says once that everything in it was tested.

---

## Self-review notes

- Spec coverage: player and look (Task 2, 5), voice and pace (Global Constraints, Task 4), script check (Task 3), where things live (Tasks 3, 4, 6), rollout and reviews (Tasks 7 to 12), skill (Task 1), mobile and keyboard (Task 2), size budget (Task 4's 48 kbps test, `prune_audio`).
- Changed from the design: the pronunciation file is the owner's `pronunciation.txt` in the demo_videos clips folder, not a file in the demo_videos repo, so no pull request there (Task 4, Step 4).
