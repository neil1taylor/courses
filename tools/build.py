"""Copy the published courses from their source repos into docs/.

Each course links to files outside its own folder: screenshots in its tutorial
site, and tutorial chapters. Screenshots are copied, keeping their path, so the
course's links still work. Tutorial chapters are not published here, so those
links become plain text, except the header's "Tutorials" link, which goes to
this site's home page instead.

Run from the repo root:  python3 tools/build.py
"""
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote

HOME = Path.home() / "Projects"
ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"

# slug -> (base folder that the course's "../" links resolve under, course folder inside it)
SOURCES = {
    "rovs": (HOME / "rovs_tutorials/docs", "course"),
    "vpc": (HOME / "vpc_tutorials/docs", "course"),
    "backup": (HOME / "cohesity", "course"),
}

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


def build():
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
    shutil.copy2(ROOT / "home/index.html", SITE / "index.html")
    (SITE / ".nojekyll").write_text("")


if __name__ == "__main__":
    build()
