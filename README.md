# IBM Cloud courses

Short, interactive courses on IBM Cloud that need no account or cluster.
Published at https://neil1taylor.github.io/courses/.

| Course | Source |
|---|---|
| Learn ROVS without a cluster | `rovs-tutorials`, `docs/course/` |
| Learn IBM Cloud VPC without an account | `vpc-tutorials`, `docs/course/` |
| Learn IBM Cloud Backup and Recovery without an account | `cohesity`, `course/` |
| Learn IBM Cloud Cyber Vault without an account | `cohesity`, `course/vault/` |

The courses are written in their source repos. This repo only publishes them.

## Update the site

1. Pull the latest `main` of each source repo into `~/Projects`.
2. Run `python3 tools/build.py`. It rebuilds `docs/` and needs Pillow.
3. Open a pull request with the changed `docs/` files. GitHub Pages publishes `docs/` on `main`.

The build copies the screenshots each course uses, turns links to the unpublished
tutorials into plain text, removes each unit's note of its source files, and blurs
the screenshot areas listed in `BLUR`. Check new screenshots for names from outside
the lab before you publish them; add any you find to `BLUR`.

## Making a video course

A video course is made from a course that already exists on the site. Its pages are where the
facts come from, and every fact in them has been tested or cited. For a brand-new topic, the
course pages are written and tested first, then the video.

1. **You:** open a session in `~/Projects/courses` and ask, for example, "Make the video course for
   Backup and Recovery."
2. **The agent** writes the course outline from the course's pages: for each module, what the
   learner will be able to do, the facts it teaches with their sources, and three check questions.
   It starts the review page (`tools/review.py <course>`, at http://127.0.0.1:8780/) and sends you
   the link.
3. **You** review the outline in its text file, `review/<course>/00-outline.txt`: change the wording, move
   the `*` to the right answer, or leave a comment (a line starting with `>`), then say "done". When
   you're happy, say "approved" (or "modules 1 to 5 approved"); the agent records it. Nothing else is
   written until you approve.
4. **The agent** writes one sample module, checks it, and has a second agent read it fresh. It
   sends you the module's text file (in `review/<course>/`) and its review page with the slides.
5. **You** edit the text file or leave comments (a line starting with `>`), then say "done". The
   agent applies your changes. When you're happy, say "approved" and the agent records it. The agent
   then voices that one module, so you hear the voice once.
6. **The rest of the modules come in batches of about five**, repeating steps 4 and 5.
7. **The agent** records and publishes only approved modules. The site switches to the video
   version when the whole course is approved.

You say which course to make, then "done" after each review and "approved" when it's right. The
agent can't record an approval while your text file has edits it hasn't applied, so what's approved
is what you read. The review page still has Approve buttons if you prefer them. Everything else, including the
review page and the pull requests, is the agent's job. The `course-video` skill has the steps.
The approval process is specified in `design/2026-11-12-content-approval-spec.md`.

## Video courses

Each source repo keeps a module script for each unit in a `video/` folder beside the course
pages (`<unit file name>.json`). `VIDEO` in `tools/build.py` lists the sources. A source with no
`video/` folder is skipped. For each course the build checks every script, stops with the
problems if there are any, makes the audio for any changed cue, and writes
`docs/<course>/video/`: a contents page, one page per module, and `audio/`. Cyber Vault's video
version is `docs/vault/video/`.

Making audio needs the Watson key, so do it on the owner's workstation. `python3 tools/build.py --no-voice`
makes no Watson calls and stops if any cue has no cached audio.

The home page links a course's interactive version until its `live` flag in `VIDEO` is `True`;
then it links the video version. The interactive pages stay published.

`home/index.html` is the home page. It lists the courses by hand, so add a course there too.
