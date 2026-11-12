# Narrated video courses: design

## What this is and why

The four courses on neil1taylor.github.io/courses (ROVS, VPC, Backup and Recovery, Cyber Vault) are interactive pages: a learner reads each step and clicks through. The owner wants the same courses as narrated presentations, in a player like Pluralsight's: a slide area with a voice explaining it, a side panel with the contents and a transcript, and questions the learner answers on the way. The look stays the one the courses already have (Red Hat type, hand-drawn sketches, marker blue). It is not made for Pluralsight and is not published there.

In time, the video version replaces the interactive pages on the site. A trial module (Cyber Vault, "Why backups need a vault") was built first, revised four times with the owner, and approved: "Module 1 looks good". This design is how to build every other module the same way.

## Goals

- Every unit of the four courses becomes a narrated module that teaches the same facts as the unit it comes from.
- A learner can watch a module start to finish without touching anything, except to answer questions.
- A learner can find their place: contents, transcript, seek bar, step back and forward, speed, captions.
- The slides follow the slide research (`design/slide-research.md`): one idea a slide, at most about 20 words, the narration never printed on the slide, diagrams that build as they are spoken about.
- The narration sounds like a trainer talking (the owner's voice rules, below).
- The site keeps working for a learner on a phone.

## Non-goals

- No rendered video files (MP4). The "video" is a page that plays audio and animates slides. This keeps it cheap to change one sentence.
- No new facts. A module teaches what its unit teaches; if a unit is wrong, fix the unit first.
- No accounts, sign-in or server. Progress is kept in the learner's own browser.
- No publishing on Pluralsight or any other platform.
- Infrastructure Explorer and VCF Migration Lite courses are never published on this site and are out of scope.

## Anti-goals: it fails, even if it works, when

- The narration sounds machine-written ("Something in it is too strong", "the board" with no introduction, riddles, telling the learner what to say).
- Slides are busy, hold the narration as text, or leave large empty areas.
- The course carries anything that dates it: dates, Beta status, region availability, time-limited offers. Dates inside screenshots and pasted command output are fine.
- Results are framed as failures. Lead with what was recovered or what worked; give problems as advice.
- The pace is rushed. The owner found the first trial "a little fast"; the approved pace is below.

## Words

| Word | Meaning |
|---|---|
| Course | One of the four courses. |
| Section | A heading in a course's contents. Each of today's modules becomes a section. |
| Module | One narrated video. Each of today's units becomes a module. |
| Step | A part of a module, listed in the contents with its length. The trial module has seven steps. |
| Cue | One spoken sentence or two, with the slide changes that go with it. |

The learner sees course, section, module and step. "Cue" is a build word only. Narration never quotes a unit or module number ("unit 1.1"); it says "the next module" or names it.

## What a module looks like (approved in the trial)

- A 1920 by 1080 slide area, scaled to fit, inside a dark player. The side panel shows the course, the module title, "Module n of N", a completion bar, and two tabs: Contents (the steps, with lengths) and Transcript (every cue, the current one highlighted, click to jump).
- Controls: play and pause, previous and next step, back and forward one cue, speed, captions on and off (off when a module opens; the owner's choice). Autoplay moves to the next module at the end.
- Slide types, from the trial: title, diagram, statement, question, tip ("Watch for this"), words (at most four terms), score, summary (one big sentence with key words in blue, and a drawing). Sizes and margins are in `slide-research.md` section 3 and the trial's `player.css`.
- Two more slide types for hands-on units (47 of 89 units have screenshots, and many have commands and output):
  - **screen**: the unit's screenshot filling the slide, with a blue box drawn round the part being spoken about, one box at a time as the narration names it. The published, blurred copy that `tools/build.py` makes is the one used.
  - **terminal**: the command and at most about eight lines of its output, in large monospace type, with the line being spoken about in blue. Long output is cut to the lines the narration talks about.
- Diagrams are rough.js sketches drawn from a small description (boxes, lines, text). The part being spoken about is blue, parts already covered turn grey, the rest is hidden until named.
- A question stops the narration until the learner answers. Wrong answers fade, the right one is highlighted, a one-line reason appears, and the narration goes on. "Check yourself" questions count towards the score at the end.
- Questions: a module keeps about three to five of its unit's questions. The last three, in a "Check yourself" step, count towards the score. The other questions in the unit become narration ("You might think a valid key is enough. It isn't: ..."), so no fact is lost.
- Final-scenario modules (the last module of each course) are a narrated worked answer, with a pick-one question at each decision point, not an open design task.
- Every module starts with what the learner will be able to do, and ends with a score, one sentence to remember, and what comes next.

## The voice

- IBM Watson Text to Speech, voice `en-GB_GeorgeNatural`, through `~/Projects/demo_videos/scripts/narrate.py`, as in the demo videos. The approved pace is playback at 0.92 with pitch kept, a gap of 0.8 s after each cue plus a hold set per cue (longer after a question or a diagram build).
- Pronunciation fixes go in the demo_videos pronunciation file, not in each script. The first one: "read" as in "seed" (IPA ɹiːd) where it is present tense. The trial did this with a script-side rule; the build moves it to the shared file.
- The words follow the blog-writing skill's `references/course-text.md` (the owner-approved lines and the rejected ones). In short: introduce every person; plain questions ("Is that true?"); contractions; admin words ("recovered", "with errors"); lead with what works. Say once at the start of a course that everything in it was tested; after that, state results plainly, without "in our lab".

## How a module is made

1. **Script.** One JSON file per module, written from the unit's HTML: the steps, and for each cue the words spoken, the slide (if it changes) and what builds on it. The format is the trial's `script.json`. Scripts live in the course's source repo beside the unit, in a `video/` folder, so a fix to a unit and its module go in one pull request.
2. **Check the script** before any audio is made: the module teaches the unit's facts and adds none; the voice rules hold; no dates or Beta; no slide over about 20 words; every person introduced. A reviewer on a different model reads it cold, as the blog-writing skill's cold read does.
3. **Voice.** A script turns each cue into speech. Files are named by a hash of their words, so changing one sentence regenerates one file. A timeline file records each cue's length.
4. **Build.** One shared player (the trial's `player.js` and `player.css`) and a page per module, built by the courses repo's `tools/build.py`, which already copies each course into `docs/`.
5. **Look.** Before a course is published, every slide of every module is opened at 1920 by 1080 and at phone width, and screenshots of each slide type are checked for overflow, empty space and contrast.

## Where things live

- Scripts: in each source repo, `video/<unit file name>.json` beside the course's pages. A pull request that fixes a unit fixes its script too.
- Audio: made on the owner's workstation (the Watson key never leaves it, so there is no CI step) into a shared cache, and committed only to the courses repo's `docs/`, not to the source repos.
- `tools/build.py` reads each source repo's `video/` folder, as it already reads the course pages, makes the audio for any changed cue, and writes the module pages.
- Site addresses: the video version of a course goes at `/<course>/video/`, one page per module. The home page links a course's video version only when that whole course is approved; until then it links the interactive version.
- Pronunciation fixes are a pull request to the demo_videos repo, which owns the pronunciation file.

## When a unit has something the module must not say

If a unit's own text has a date, Beta status, region availability or a wrong fact, fix the unit in the same pull request as its script. Dates and labels inside screenshots and command output stay; the narration does not read them out.

## Rollout

1. Cyber Vault first (17 modules; module 1 is the trial). The owner reviews modules 2 to 5 before the rest are made, then the whole course before it replaces the interactive one.
2. Then Backup and Recovery (24), VPC (24) and ROVS (24), one course at a time, each reviewed before it goes live.
3. While a course is being converted, the interactive version stays live. When the video version is approved, it takes the course's place on the site's home page. The interactive pages stay published at their current addresses for anyone with a link.

## Constraints

- GitHub Pages: a published site should stay under 1 GB. Speech at 48 kbps mono is about 0.4 MB a minute; 89 modules of about 5 minutes is about 180 MB. Audio is encoded at 48 kbps mono, not the trial's 96 kbps.
- Watson Text to Speech: the `demo-videos-tts` service is on the Standard plan, USD 2.12 per 100,000 characters, with no monthly cap. All 89 modules are about 350,000 characters, so about USD 7.50 for the first build; the cache means later builds pay only for changed sentences.
- External scripts and fonts come from files in the repo (rough.js and the fonts are already copied by the trial build), not from a CDN.
- Keyboard: space plays and pauses, arrow keys step cues, and the answer cards take Enter. Captions and the transcript give the narration as text for anyone who cannot hear it.

## Left to the builder

- How the script check is automated, beyond the checks listed.
- The page layout of the course home and section headings, within the existing look.
- How progress is stored in the browser, as long as a learner's completed modules show as done when they come back.
- The order of work inside a course.

## Decisions I made for you

- Screenshots and command output stay in the modules, as two new slide types (screen and terminal) with highlights that build with the narration.
- Each module keeps three to five questions; the unit's other questions become narration. The last three count for the score.
- The last module of each course is a worked answer with pick-one questions, not an open task.
- Audio is made on your workstation and committed only to the courses site, not to the source repos.
- Video pages go at `/<course>/video/`; the home page switches a course to video only when the whole course is approved.
- A wrong or dated sentence in a unit is fixed in the unit, in the same pull request as its module.

- Today's units become modules, and today's modules become section headings. You chose "modules and steps"; this puts every module at about 4 to 6 minutes.
- Scripts live in each course's source repo, next to the unit they come from, not in the courses repo.
- No MP4 files; the page plays audio and draws the slides.
- Audio at 48 kbps mono, to keep the site small. Speech sounds the same to the ear at that rate; I will check one module with you before encoding all of them.
- Cyber Vault first, because its first module is done and approved.
- You review modules 2 to 5 of Cyber Vault before the other 12 are made, so a problem is caught early.
- The interactive pages stay published at their addresses after the video version replaces them on the home page.
- "Everything in this course was tested" is said once per course, at the start; results after that are stated plainly.
