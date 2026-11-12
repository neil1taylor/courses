"""Copy the published courses from their source repos into docs/.

Each course links to files outside its own folder: screenshots in its tutorial
site, and tutorial chapters. Screenshots are copied, keeping their path, so the
course's links still work. Tutorial chapters are not published here, so those
links become plain text, except the header's "Tutorials" link, which goes to
this site's home page instead.

Run from the repo root:  python3 tools/build.py [--no-voice]
--no-voice makes no Watson calls; it stops if any cue has no cached audio.
"""
import hashlib
import math
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent / "video"))

HOME = Path.home() / "Projects"
ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"

# slug -> (base folder that the course's "../" links resolve under, course folder inside it)
SOURCES = {
    "rovs": (HOME / "rovs_tutorials/docs", "course"),
    "vpc": (HOME / "vpc_tutorials/docs", "course"),
    "backup": (HOME / "cohesity", "course"),
}

# Video courses: slug -> title, the source folder of the module scripts, and whether the whole
# course is approved. The home page links the video version only when live is True; until then
# it links the interactive course. A missing video folder means no modules yet.
# Cyber Vault's interactive version is published inside the backup course; its video version is not.
VIDEO = {
    "vault": {"title": "IBM Cloud Cyber Vault", "source": HOME / "cohesity/course/vault/video", "live": False},
    "backup": {"title": "IBM Cloud Backup and Recovery", "source": HOME / "cohesity/course/video", "live": False},
    "vpc": {"title": "IBM Cloud VPC", "source": HOME / "vpc_tutorials/docs/course/video", "live": False},
    "rovs": {"title": "Red Hat OpenShift Virtualization Service", "source": HOME / "rovs_tutorials/docs/course/video", "live": False},
}
# Where the home page links each course's interactive version.
INTERACTIVE = {"rovs": "rovs/course/", "vpc": "vpc/course/", "backup": "backup/course/", "vault": "backup/course/vault/"}
GAP = 0.8  # seconds of silence after each cue, as the player plays it
RATE = 0.92  # playback rate

# Screenshot areas that show resource names from outside the lab; blurred in the published copy.
# (path inside docs/, [(left, top, right, bottom), ...])
BLUR = {
    "backup/ibm-brs/tutorials/images/B1-1-encryption-default-on.png": [(108, 202, 250, 226), (498, 202, 690, 226)],
    "backup/ibm-brs/tutorials/images/B7g-6-key-disabled.png": [(8, 326, 195, 356)],
}

# Files a course may pull in from outside its folder.
COPYABLE = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

REF = re.compile(r'\b(href|src)="([^"]*)"')
ANCHOR = re.compile(r'<a\b[^>]*\bhref="([^"]*)"[^>]*>(.*?)</a>', re.S)
# Each unit names its private source files in a comment; readers do not need them.
SOURCE_NOTE = re.compile(r"<!-- course-unit .*?-->\n?", re.S)


def is_local(url):
    return url and not re.match(r"^([a-z]+:|#|//)", url)


def resolve(page, url):
    path = unquote(url.split("#")[0].split("?")[0])
    return (page.parent / path).resolve() if path else page


def publish_page(page, base, course_dir, out_base, depth_to_root, copied, dropped):
    text = page.read_text(encoding="utf-8")
    text = SOURCE_NOTE.sub("", text)
    home = "../" * depth_to_root

    def fix_anchor(m):
        url = m.group(1)
        if not is_local(url):
            return m.group(0)
        target = resolve(page, url)
        if target.is_relative_to(course_dir) or (target.suffix.lower() in COPYABLE and target.is_file()):
            return m.group(0)
        if m.group(2) == "Tutorials":  # the header link to the tutorial site
            return f'<a href="{home}">All courses</a>'
        dropped.add(str(target.relative_to(base) if target.is_relative_to(base) else target))
        return m.group(2)

    text = ANCHOR.sub(fix_anchor, text)

    for _, url in REF.findall(text):
        if not is_local(url) or url == home:
            continue
        target = resolve(page, url)
        if target.is_relative_to(course_dir):
            if not target.exists():
                sys.exit(f"{page}: broken link {url}")
            continue
        if not (target.suffix.lower() in COPYABLE and target.is_file() and target.is_relative_to(base)):
            sys.exit(f"{page}: cannot publish {url}")
        dest = out_base / target.relative_to(base)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, dest)
        copied.add(dest)

    out = out_base / page.relative_to(base)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def blur(path, boxes):
    from PIL import Image, ImageFilter  # Pillow: only needed for the BLUR list

    if not path.is_file():
        sys.exit(f"blur list names a missing file: {path}")
    img = Image.open(path)
    for box in boxes:
        img.paste(img.crop(box).filter(ImageFilter.GaussianBlur(8)), box)
    img.save(path)


class MissingAudio(Exception):
    pass


class CachedOnly:
    """A speaker that never calls Watson: it returns the cached wav or says what is missing."""

    def __init__(self, voice, cache):
        self.voice, self.cache = voice, Path(cache)

    def wav(self, text):
        key = hashlib.sha256(f"{self.voice}|{text}".encode()).hexdigest()
        path = self.cache / (key + ".wav")
        if not path.exists():
            raise MissingAudio(f'no cached audio for: "{text[:70]}"')
        return str(path)


def minutes(timeline):
    seconds = sum((c["dur"] + GAP + c.get("hold", 0)) / RATE for s in timeline["steps"] for c in s["cues"])
    return max(1, math.ceil(seconds / 60))


def build_video(site, slug, cfg, speaker, shared):
    """Write docs/<slug>/video/: a contents page, a page and the audio for each module script."""
    import page
    import script as scripts
    import voice

    source = Path(cfg["source"])
    if not source.is_dir():
        return
    files = sorted(source.glob("*.json"))
    problems = []
    loaded = []
    for n, f in enumerate(files):
        s = scripts.load_script(f)
        unit = source.parent / (f.stem + ".html")
        if not unit.is_file():
            problems.append(f"{f.name}: no unit page {unit.name} beside the video folder")
            continue
        problems += [f"{f.name}: {p}" for p in scripts.check_script(s, unit.read_text(encoding="utf-8"), n == 0)]
        loaded.append((f.stem, s))
    if problems:
        sys.exit(f"{slug}: the scripts have problems:\n" + "\n".join(problems))
    out = site / slug / "video"
    audio = out / "audio"
    try:
        timelines = [(stem, voice.voice_script(s, audio, speaker, shared)) for stem, s in loaded]
    except MissingAudio as e:
        sys.exit(f"{slug}: {e}\nRun the build without --no-voice on the workstation that has the Watson key.")
    voice.prune_audio(audio, [t for _, t in timelines])
    assets = "../../video-assets/"
    page.copy_assets(site / "video-assets")
    course = {"slug": slug, "title": cfg["title"]}
    total = len(timelines)
    for i, (stem, t) in enumerate(timelines):
        prev_href = timelines[i - 1][0] + ".html" if i else None
        next_href = timelines[i + 1][0] + ".html" if i + 1 < total else None
        (out / (stem + ".html")).write_text(
            page.render_module(t, course, i + 1, total, prev_href, next_href, assets=assets,
                               contents_href="index.html"), encoding="utf-8")
    rows = [{"section": t["section"], "title": t["title"], "href": stem + ".html", "minutes": minutes(t)}
            for stem, t in timelines]
    (out / "index.html").write_text(page.render_contents(course, rows, assets=assets, home_href="../../"),
                                    encoding="utf-8")
    print(f"{slug}: {total} video modules")


def home_html(html, video):
    """The home page, linking a course's video version once that course is live."""
    for slug, cfg in video.items():
        if cfg["live"]:
            html = html.replace(f'href="{INTERACTIVE[slug]}"', f'href="{slug}/video/"')
    return html


def build_videos(no_voice):
    if not any(Path(c["source"]).is_dir() for c in VIDEO.values()):
        return
    import voice

    shared = voice.shared_pronunciation()
    if no_voice:
        _, _, settings = voice._demo_videos()
        import narrate
        speaker = CachedOnly(settings.get("DEMO_VOICE", required=True), narrate.CACHE)
    else:
        speaker = voice.new_speaker()
    for slug, cfg in VIDEO.items():
        build_video(SITE, slug, cfg, speaker, shared)


def build(no_voice=False):
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    for slug, (base, course) in SOURCES.items():
        base = base.resolve()
        course_dir = base / course
        out_base = SITE / slug
        copied, dropped = set(), set()
        for f in sorted(course_dir.rglob("*")):
            if f.is_dir() or f.name.endswith(".md"):
                continue
            if "video" in f.relative_to(course_dir).parts[:-1]:  # module scripts are not published
                continue
            if f.suffix == ".html":
                depth = len(f.relative_to(base).parts)  # slug folder + path inside it
                publish_page(f, base, course_dir, out_base, depth, copied, dropped)
            else:
                dest = out_base / f.relative_to(base)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        print(f"{slug}: {len(copied)} screenshots copied, {len(dropped)} tutorial links made plain text")
    for rel, boxes in BLUR.items():
        blur(SITE / rel, boxes)
    shutil.copytree(SITE / "rovs/course/assets", SITE / "assets")
    build_videos(no_voice)
    html = (ROOT / "home/index.html").read_text(encoding="utf-8")
    (SITE / "index.html").write_text(home_html(html, VIDEO), encoding="utf-8")
    (SITE / ".nojekyll").write_text("")


if __name__ == "__main__":
    build(no_voice="--no-voice" in sys.argv[1:])
