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
import json
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
    "vault": {"title": "IBM Cloud Cyber Vault", "source": HOME / "cohesity/course/vault/video", "live": True},
    "backup": {"title": "IBM Cloud Backup and Recovery", "source": HOME / "cohesity/course/video", "live": True},
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


def screen_slides(script):
    """Yield (step number, step title, slide) for each screen slide in a module script."""
    for n, step in enumerate(script["steps"], 1):
        for cue in step["cues"]:
            slide = cue.get("slide")
            if slide and slide.get("type") == "screen":
                yield n, step.get("title", ""), slide


def screen_source(unit, img):
    return (unit.parent / unit_img_path(img)).resolve()


def unit_img_path(img):
    return unquote(img.split("#")[0].split("?")[0])


def blur_boxes(src):
    """The BLUR boxes for a source image, found by the path it has inside docs/ in the interactive course."""
    for slug, (base, _) in SOURCES.items():
        base = base.resolve()
        if src.is_relative_to(base):
            return BLUR.get(f"{slug}/{src.relative_to(base).as_posix()}")
    return None


def copy_screens(out, unit_dir, timelines):
    """Copy each screen slide's image into out/images and point the timeline at the copy."""
    images = out / "images"
    if images.exists():
        shutil.rmtree(images)
    for _, t in timelines:
        for _, _, slide in screen_slides(t):
            src = screen_source(unit_dir / t["unit"], slide["img"])
            name = hashlib.sha1(str(src).encode()).hexdigest()[:8] + "-" + src.name
            dest = images / name
            if not dest.exists():
                images.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                boxes = blur_boxes(src)
                if boxes:
                    blur(dest, boxes)
            slide["img"] = "images/" + name


def minutes(timeline):
    seconds = sum((c["dur"] + GAP + c.get("hold", 0)) / RATE for s in timeline["steps"] for c in s["cues"])
    return max(1, math.ceil(seconds / 60))


def first_stem(source):
    """The course's first module: the outline's first unit, or with no outline the first script by name."""
    outline = Path(source) / "outline.json"
    if outline.is_file():
        modules = json.loads(outline.read_text(encoding="utf-8")).get("modules") or []
        if modules:
            return modules[0].get("unit")
    files = sorted(f.stem for f in Path(source).glob("*.json") if f.name != "outline.json")
    return files[0] if files else None


def load_video(slug, cfg):
    """Load and check a course's module scripts. Returns ([(unit stem, script)], [problem])."""
    import script as scripts

    source = Path(cfg["source"])
    if not source.is_dir():
        return [], []
    problems, loaded, first = [], [], first_stem(source)
    for f in sorted(f for f in source.glob("*.json") if f.name != "outline.json"):
        s = scripts.load_script(f)
        unit = source.parent / (f.stem + ".html")
        if not unit.is_file():
            problems.append(f"{slug}: {f.name}: no unit page {unit.name} beside the video folder")
            continue
        found = scripts.check_script(s, unit.read_text(encoding="utf-8"), f.stem == first)
        problems += [f"{slug}: {f.name}: {p}" for p in found]
        for step_no, title, slide in screen_slides(s):
            src = screen_source(unit, slide["img"])
            if not src.is_file():
                problems.append(f"{slug}: {f.name}: step {step_no} ({title}): screen image not found: {src}")
        loaded.append((f.stem, s))
    return loaded, problems


def check_videos(video):
    """Check every course's scripts; stop with all the problems together."""
    loaded, problems = {}, []
    for slug, cfg in video.items():
        loaded[slug], found = load_video(slug, cfg)
        problems += found
    if problems:
        sys.exit("The video scripts have problems:\n" + "\n".join(problems))
    return loaded


def write_video(site, slug, cfg, loaded, speaker, shared, estimate=False):
    """Write docs/<slug>/video/: a contents page, a page and the audio for each module.

    estimate=True is for the review page: durations are guessed from the word count and no audio is made,
    so a script that was never voiced can be shown.
    """
    import page
    import voice

    if not loaded:
        return
    out = site / slug / "video"
    audio = out / "audio"
    if estimate:
        timelines = [(stem, voice.estimate_script(s)) for stem, s in loaded]
    else:
        try:
            timelines = [(stem, voice.voice_script(s, audio, speaker, shared)) for stem, s in loaded]
        except voice.MissingAudio as e:
            sys.exit(f"{slug}: {e}\nRun the build without --no-voice on the workstation that has the Watson key.")
        voice.prune_audio(audio, [t for _, t in timelines])
    copy_screens(out, Path(cfg["source"]).parent, timelines)
    assets = "../../video-assets/"
    page.copy_assets(site / "video-assets")
    course = {"slug": slug, "title": cfg["title"]}
    total = len(timelines)
    rows = [{"section": t["section"], "title": t["title"], "href": stem + ".html", "minutes": minutes(t)}
            for stem, t in timelines]
    for i, (stem, t) in enumerate(timelines):
        prev_href = timelines[i - 1][0] + ".html" if i else None
        next_href = timelines[i + 1][0] + ".html" if i + 1 < total else None
        (out / (stem + ".html")).write_text(
            page.render_module(t, course, i + 1, total, prev_href, next_href, assets=assets,
                               contents_href="index.html", outline=rows), encoding="utf-8")
    (out / "index.html").write_text(page.render_contents(course, rows, assets=assets, home_href="../../"),
                                    encoding="utf-8")
    print(f"{slug}: {total} video modules")


def build_video(site, slug, cfg, speaker, shared):
    loaded = check_videos({slug: cfg})[slug]
    write_video(site, slug, cfg, loaded, speaker, shared)


def reset_site(site, slugs):
    """Empty the site folder except each course's audio folder: the committed mp3s are the persistent audio.

    Nothing is moved, so a failure part way leaves every audio folder where it was.
    """
    site = Path(site)
    keep = {(site / slug / "video" / "audio").resolve() for slug in slugs}
    site.mkdir(exist_ok=True)

    def wipe(folder):
        for child in sorted(folder.iterdir()):
            real = child.resolve()
            if real in keep:
                continue
            if child.is_dir() and not child.is_symlink() and any(k.is_relative_to(real) for k in keep):
                wipe(child)
            elif child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()

    wipe(site.resolve())


def home_html(html, video):
    """The home page, linking a course's video version once that course is live."""
    for slug, cfg in video.items():
        if cfg["live"]:
            html = html.replace(f'href="{INTERACTIVE[slug]}"', f'href="{slug}/video/"')
    return html


def build_videos(no_voice, loaded=None):
    loaded = loaded if loaded is not None else check_videos(VIDEO)
    if not any(loaded.values()):
        return
    import voice

    shared = voice.shared_pronunciation()
    speaker = voice.offline_speaker() if no_voice else voice.new_speaker()
    for slug, cfg in VIDEO.items():
        write_video(SITE, slug, cfg, loaded[slug], speaker, shared)


def build(no_voice=False):
    loaded = check_videos(VIDEO)  # before docs/ is touched
    reset_site(SITE, list(VIDEO))
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
    build_videos(no_voice, loaded)
    html = (ROOT / "home/index.html").read_text(encoding="utf-8")
    (SITE / "index.html").write_text(home_html(html, VIDEO), encoding="utf-8")
    (SITE / ".nojekyll").write_text("")


if __name__ == "__main__":
    build(no_voice="--no-voice" in sys.argv[1:])
