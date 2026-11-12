"""Build the HTML pages of a narrated course: one player page per module, and a contents page.

A timeline is a script (see the course-video skill's script-format.md) with `dur`
(seconds) and `audio` (a path relative to the page) added to every cue.
"""
import json
import shutil
from html import escape
from pathlib import Path

PLAYER_DIR = Path(__file__).resolve().parent / "player"
SHARED_ASSETS = Path.home() / "Projects" / "cohesity" / "course" / "assets"
DEFAULT_ASSETS = "../video-assets/"


def _json_for_script(data) -> str:
    """JSON that is safe inside a <script> element."""
    return json.dumps(data).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _link(label: str, href: str | None, ident: str) -> str:
    if not href:
        return "<span></span>"
    return f'<a id="{ident}" href="{escape(href, quote=True)}">{label}</a>'


def render_module(timeline: dict, course: dict, index: int, total: int,
                  prev_href: str | None, next_href: str | None,
                  assets: str = DEFAULT_ASSETS, contents_href: str | None = None) -> str:
    data = dict(timeline)
    data.update(courseSlug=course["slug"], moduleIndex=index, moduleTotal=total, nextHref=next_href)
    title = escape(timeline["title"])
    course_title = escape(course["title"])
    nav = ""
    if prev_href or next_href:
        nav = ('<div class="modnav">'
               + _link("&larr; Previous module", prev_href, "prevmod")
               + _link("Next module &rarr;", next_href, "nextmod")
               + "</div>")
    if contents_href:
        nav += f'\n    <p class="backlink"><a id="contents" href="{escape(contents_href, quote=True)}">All modules in this course</a></p>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} &middot; {course_title}</title>
<link rel="stylesheet" href="{assets}player.css">
<script src="{assets}rough.js" defer></script>
<script src="{assets}player.js" defer></script>
</head>
<body>
<div class="app">
  <div class="stage-col">
    <div class="stage" id="stage">
      <div class="canvas" id="canvas"></div>
      <div class="cc off" id="cc" aria-live="polite"></div>
      <button class="bigplay" id="bigplay" aria-label="Play">&#9654;</button>
    </div>
    <div class="answerbar" id="answerbar" role="group" aria-label="Answers" hidden></div>
    <div class="bar">
      <div class="seek" id="seek"><div class="fill" id="fill"></div><div class="knob" id="knob"></div></div>
      <div class="ctrls">
        <button id="play" aria-label="Play">&#9654;</button>
        <button id="prevstep" aria-label="Previous step">&#9198;</button>
        <button id="backline" aria-label="Back one line">&#8634;</button>
        <button id="fwdline" aria-label="Forward one line">&#8635;</button>
        <button id="nextstep" aria-label="Next step">&#9197;</button>
        <span class="time" id="time">0:00 / 0:00</span>
        <span class="grow"></span>
        <button id="speed" aria-label="Speed">1x</button>
        <button id="ccbtn" aria-label="Captions" aria-pressed="false">CC</button>
      </div>
    </div>
  </div>
  <aside class="side">
    <div class="sidetop">
      <div class="course">{course_title}</div>
      <h1 class="ctitle">{title}</h1>
      <div class="by">Module {index} of {total}<span class="donebadge" id="donebadge" hidden>Done</span></div>
      <div class="modsdone" id="modsdone"></div>
      <div class="comp"><span>Module completion</span><div class="cbar"><i id="cfill"></i></div><b id="cpct">0%</b></div>
      <div class="tabs" role="tablist">
        <button role="tab" class="on" data-tab="toc">Steps</button>
        <button role="tab" data-tab="tr">Transcript</button>
      </div>
    </div>
    <div class="pane" id="toc"></div>
    <div class="pane" id="tr" hidden></div>
    <label class="auto"><input type="checkbox" id="autoplay" checked> Autoplay the next module</label>
    {nav}
  </aside>
</div>
<script>window.TIMELINE = {_json_for_script(data)};</script>
</body>
</html>
"""


def render_contents(course: dict, modules: list[dict], assets: str = DEFAULT_ASSETS,
                    home_href: str | None = None) -> str:
    """The contents page: modules grouped under their section, in order."""
    course_title = escape(course["title"])
    groups: list[tuple[str, list[tuple[int, dict]]]] = []
    for n, module in enumerate(modules, start=1):
        if not groups or groups[-1][0] != module["section"]:
            groups.append((module["section"], []))
        groups[-1][1].append((n, module))
    body = []
    for section, items in groups:
        rows = "\n".join(
            f'    <li><a href="{escape(m["href"], quote=True)}" data-module="{n}">'
            f'<span class="t">{escape(m["title"])}</span>'
            f'<span class="min">{m["minutes"]} min</span><span class="tick"></span></a></li>'
            for n, m in items)
        body.append(f"  <h2>{escape(section)}</h2>\n  <ul>\n{rows}\n  </ul>")
    back = f'  <p class="backlink"><a href="{escape(home_href, quote=True)}">All courses</a></p>\n' if home_href else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{course_title} &middot; Modules</title>
<link rel="stylesheet" href="{assets}player.css">
<script src="{assets}player.js" defer></script>
</head>
<body class="contents">
<main data-contents data-course="{escape(course["slug"], quote=True)}">
  <h1>{course_title}</h1>
{back}  <p class="count" data-count></p>
{chr(10).join(body)}
</main>
</body>
</html>
"""


def copy_assets(dest: Path) -> None:
    """Copy the player, rough.js and the fonts to `dest`, so no page loads anything from a CDN."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("player.js", "player.css"):
        shutil.copy(PLAYER_DIR / name, dest / name)
    shutil.copy(SHARED_ASSETS / "rough.js", dest / "rough.js")
    shutil.copy(SHARED_ASSETS / "LICENSE-rough.txt", dest / "LICENSE-rough.txt")
    shutil.copytree(SHARED_ASSETS / "fonts", dest / "fonts", dirs_exist_ok=True)
