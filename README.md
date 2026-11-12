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
