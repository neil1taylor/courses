# Brief: one video module script

You write ONE narrated video module script for the <course> video course, from one unit page. Do the work yourself; don't delegate. The owner has pre-approved the course, so quality must be right without their review.

Paths (W = the worktree you were given):
- Unit page: W/<course folder>/<unit>.html
- Script to write: W/<course folder>/video/<unit>.json
- Approved outline: W/<course folder>/video/outline.json (your module's entry: title, outcomes, facts, three checks). The "Next:" line names the next module by its outline title (the part before any colon). The last module ends the course: summary `next` is "That's the end of the course." and the last cue says the course is done, one line on what the learner can now do, and "Thanks for following Northgate to the end."
- Section: from the unit page's breadcrumb.

Read in full first:
1. ~/.claude/skills/course-video/SKILL.md (including the checklist under "The check, before any audio is made"), references/slide-rules.md, references/script-format.md. Follow them exactly.
2. ~/Projects/claude-skills/skills/blog-writing/references/course-text.md (voice rules).
3. Owner-approved scripts from another course, as models of voice, shape, holds and slides: ~/Projects/cohesity/course/video/m1-u2-the-pieces.json, m3-u1-policies-and-protection-groups.json, m4-u1-restore-files-and-check-every-one.json, m6-u1-a-source-reboots-an-agent-stops.json. Once earlier modules of this course exist in W/<course folder>/video/, stay consistent with how they state the same facts.
4. Your unit page in full: every step, question and reveal. Screenshots the unit uses may be reused (img paths are relative to the unit page).

Rules from the owner and from reviews of the previous course; get them right first time:
- Use the outline's title, outcomes and three check questions. If a check slide would pass 20 words, shorten options first, then the head; the narration says the full question.
- Teach only the unit's facts. No fact, explanation, standard meaning or advice the unit doesn't give; where you'd need one, reword or cut. Lose nothing the outcomes and checks need. Copy numbers exactly; one set of numbers per event; counts must add up.
- Introduce every term, component, setting and person at its first use IN THIS MODULE, in a few words from the unit (a learner may start here). Words-slide definitions keep the unit's meaning.
- Every screenshot shows what the narration says while it is up; otherwise use a table, terminal, diagram or statement-with-sketch. A statement slide needs a sketch, except the "Three quick questions" opener.
- No two sentences contradict; every "only", "but", "unlike" states the true condition; a tip or rule is no broader than the unit's case; normal behaviour is never a "Watch for this" tip. Lead with what works; turn a problem into advice.
- Plain, NOT basic: field terms (create, attach, route, allow, deploy, operate). Never vague "run/handle/manage/look after" for who does what.
- Never in narration or slide text (inside screenshots and real command output is fine): "in our lab", "in our test(s)" ("When we tried it, …" is allowed), dates, years 2020-2039, region or zone names (us-south, us-south-1, eu-de…; say "a region", "another zone"), "Beta", "generally available", "latest", unit or module numbers. Don't speak raw flags, IDs, CIDRs character by character, or long identifiers; describe them and show the exact text on a terminal or table slide. Say a CIDR as a trainer would ("a slash 24 block").
- "read": rephrase past tense; add "pronounce": {"read": "reed"} if a present-tense "read" remains.
- Terminal slides: only real commands and real output from the unit, 8 output lines at most; region names inside real output are fine on screen.
- Hand-written diagram labels sit 30-40px directly under or over the box they label, 20px clear of other shapes.
- A box with only a `title` draws it vertically centred, so a box that contains other boxes hides its title behind them. Give such a container a `detail` (which moves the title to the top) or no title plus a hand label 12px above it. Small boxes grow to fit their text, so leave at least 24px between stacked boxes.
- Unit page: fix it only if a fact is wrong, or if its prose (not code, output or screenshots) has product-status wording ("not generally available", "Beta", "only in <region>"); then change just that and report it. Don't touch other modules' files.
- Temp files only in W/.tmp-<unit>/; delete each with a plain `rm <file>`, then `rmdir` the folder. Never leave files behind.

Check from ~/Projects/courses until it prints clean (use `first` only for module 1, which must say once "Everything in this course was tested on a real IBM Cloud account, or comes from IBM's own documents." (check the course's README for what was really tested)):

    cd ~/Projects/courses && /opt/homebrew/bin/python3.14 -c "
    import sys; from pathlib import Path
    from tools.video.script import load_script, check_script
    s = Path(sys.argv[1]); u = Path(sys.argv[2])
    p = check_script(load_script(s), u.read_text(), first_module=sys.argv[3] == 'first')
    print('\n'.join(p) or 'clean')" <script.json> <unit.html> <first|other>

Then do the skill's manual checklist. 4,500 narration characters at most.

Don't commit, push or build. Report in under 12 lines: path, character count, check result, slide types, any unit-page change, anything unsure.
