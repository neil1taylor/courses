# Reviewing and approving video course content: spec

## Why

On the Cyber Vault video course, the owner found most faults only by watching finished videos. These included:

- wording that sounded machine-written;
- a question asked before its answer was taught;
- a wrong fact about which account a product sits in;
- no clear sign of a right or wrong answer;
- small numbers given too much weight;
- normal behaviour framed as a warning.

Each fault became a new rule. The rule was then applied by hand across all 17 modules, and the audio was recorded again. Rework after the owner watches is the expensive part. The owner wants to see and approve content earlier, when a change costs a minute and not a rebuild.

The next three courses are Backup and Recovery (24 modules), VPC (24) and ROVS (24). They start only after this spec is approved.

## Goals

- The owner approves what a course teaches before any module is written.
- The owner approves the voice on one module before the rest are written.
- The owner reads every script, with its slides, before any audio is made.
- The owner comments on a precise place (one sentence or one slide) without needing to know file names.
- Every fault the owner has already found is caught by a check, so the owner never has to find the same fault twice.
- Watching the finished course becomes a spot check, not the place where faults are found.

## Non-goals

- No change to how a module looks or sounds to a learner. The player, voice and pace are already approved.
- No change to the Cyber Vault course, which is approved and live. Its scripts are used to test the new checks.
- No new reviewers. The owner is the only person who approves.

## Anti-goals: it fails, even if it works, when

- The owner must open a file, a pull request or a terminal to review.
- The review page shows the script without its slides, so a slide fault is found only in the video.
- A fault the owner reported once comes back in a later module or course.
- Review takes the owner longer than watching the finished module would.

## The three approvals

### 1. The course outline

This happens once per course, before any script is written.

One page lists the course's modules in order. For each module it shows:

- what the learner will be able to do afterwards;
- the three questions that count towards the score, with their answers;
- the facts the module teaches, one line each, with where each fact comes from (the unit's page or a test).

This is where a wrong fact, a question with nothing behind it, or a module that dwells on a minor number is caught. The owner approves the outline, or comments on it and approves the corrected version.

### 2. A sample module

This happens once per course, after the outline is approved.

One module is written in full and shown on the review page (below). It is chosen to have a diagram, a screenshot and a question. After the owner approves the script, that one module is voiced, so the owner hears it once. The rest of the course follows this module.

### 3. Every script, before audio

The remaining modules are written in batches of about five. Each batch goes on the review page. The owner comments, the comments are fixed, and the owner approves the batch. Audio is made only for approved modules.

At the end, the owner watches whichever modules they choose. A fault found at this stage is a fault the checks missed, so it also becomes a new check (below).

## The review page

- It is a private web page, one per course. The owner opens it from a link in the chat.
- It shows each module as a list of its sentences. Next to each sentence is a picture of the slide as the learner sees it at that moment, including the boxes on screenshots and the parts of diagrams that light up.
- Questions are shown with their answers marked, and with the sentence that teaches each answer.
- Every sentence and slide has a short reference, for example "B 4.3" for course B, module 4, sentence 3.
- Beside every sentence is a comment box. Comments are saved on the page and read back by the agent that fixes them. If the comment boxes can't be provided, the owner writes comments in the chat using the reference instead.
- Each module has an Approve button. The owner may instead approve in the chat after reviewing the text files; the agent records it with `tools/review.py <course> --approve-outline` or `--approve`, which refuses while a text file has changes not yet imported. The page shows which modules are approved, which have comments still open, and which have changed since the owner last looked.
- When a script changes, the page is updated at the same link. Changed sentences are marked, so the owner rereads only what changed.

## The checks that run before the owner sees anything

Today's script check (word limits, repeated slide text, dates, pronunciation) stays. These checks are added, one for each fault the owner has found:

| The owner's finding | What the check does |
|---|---|
| Question before its answer is taught | It fails if a question's answer is not taught in an earlier sentence of the same module. |
| Machine-written wording ("Four items stay out of the plan") | It runs the blog-writing checker on the narration, plus a list of the phrases the owner rejected. |
| A thing named with no introduction ("the board", "the key") | It flags each key, file, setting or person on first mention, for a reader to confirm. |
| A wrong fact | It fails if a fact in the narration is not in the outline the owner approved. |
| Normal behaviour told as a warning | A reader checks each "tip" slide against a list of behaviours that are normal. |
| A contrast that isn't true | A reader checks that each "but", "only" or "unlike" states the true condition. |

A reader on a different model reads every module cold, as now, before the owner does.

The Cyber Vault scripts, as they stood before the owner's fixes, are the test. Each new check must find the fault the owner found there.

Every new comment from the owner is sorted in one of two ways:

- It is a one-off fix.
- It is a new rule. A new rule is added to the course-video skill and to these checks in the same change, then run across every module already written, before the next batch goes to the owner.

## Order of work

1. Build the review page and the new checks, and test them on the Cyber Vault scripts as they were before the owner's fixes.
2. Show the owner the Cyber Vault review page as a trial of the page itself.
3. Backup and Recovery: outline, sample module, then batches.
4. VPC, then ROVS, the same way.

## Decisions I made for you

- Three approvals per course: the outline, one sample module, then every script before audio.
- You approve facts and questions in the outline, before any narration is written, because a wrong fact found there costs one line.
- Only the sample module is voiced before your approval. All other audio waits until you approve the script.
- Scripts come to you in batches of about five modules, not all at once and not one at a time.
- The review page is a private web page with a comment box beside each sentence, and a short reference so you can also comment in the chat.
- Each fault you report becomes a check that runs on every module, so you don't find it twice.
- The Cyber Vault course is not reworked. Its old scripts are used only to test the checks.
- Watching the finished course stays your call, but it is a spot check, not a required step.
