import copy
import hashlib
import json
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "video"))

import build  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
UNIT = (FIX / "unit.html").read_text()
GOOD = json.loads((FIX / "good.json").read_text())


class FakeSpeaker:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(exist_ok=True)

    def wav(self, text):
        path = self.folder / (hashlib.sha256(text.encode()).hexdigest() + ".wav")
        if not path.exists():
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(b"\0\0" * 24000)
        return str(path)


def second():
    s = copy.deepcopy(GOOD)
    s["title"] = "Second module"
    s["unit"] = "b.html"
    s["steps"][0]["cues"] = [c for c in s["steps"][0]["cues"] if "tested" not in c["say"]]
    return s


def make_source(tmp_path, scripts):
    """scripts: {unit stem: script dict}. Returns the video folder."""
    course = tmp_path / "src" / "course"
    video = course / "video"
    video.mkdir(parents=True)
    for stem, s in scripts.items():
        (course / (stem + ".html")).write_text(UNIT)
        (video / (stem + ".json")).write_text(json.dumps(s))
    return video


def run(tmp_path, video, speaker=None, slug="demo"):
    site = tmp_path / "site"
    site.mkdir(exist_ok=True)
    cfg = {"title": "Demo course", "source": video, "live": False}
    build.build_video(site, slug, cfg, speaker or FakeSpeaker(tmp_path / "wavs"), {})
    return site


def test_writes_module_and_contents_pages(tmp_path):
    a = dict(GOOD, unit="a.html")
    video = make_source(tmp_path, {"a": a, "b": second()})
    site = run(tmp_path, video)
    out = site / "demo" / "video"
    assert (out / "index.html").is_file()
    assert (out / "a.html").is_file() and (out / "b.html").is_file()
    assert list((out / "audio").glob("*.mp3"))
    assert (site / "video-assets" / "player.js").is_file()


def test_modules_ordered_by_file_name_with_links(tmp_path):
    a = dict(GOOD, unit="a.html")
    video = make_source(tmp_path, {"b": second(), "a": a})
    out = run(tmp_path, video) / "demo" / "video"
    first, last = (out / "a.html").read_text(), (out / "b.html").read_text()
    assert "Module 1 of 2" in first and "Module 2 of 2" in last
    assert 'href="b.html"' in first and 'href="a.html"' in last
    assert 'href="index.html"' in first
    index = (out / "index.html").read_text()
    assert index.index("a.html") < index.index("b.html")


def test_section_heading_when_section_changes(tmp_path):
    a = dict(GOOD, unit="a.html", section="Start here")
    b = dict(second(), section="Module 1")
    c = dict(second(), section="Module 1", title="Third")
    video = make_source(tmp_path, {"a": a, "b": b, "c": c})
    index = (run(tmp_path, video) / "demo" / "video" / "index.html").read_text()
    assert index.count("<h2>") == 2
    assert index.index("Start here") < index.index("Module 1")


def test_stops_listing_problems(tmp_path):
    bad = second()
    bad["steps"][0]["cues"][0]["say"] = "This runs in unit 1.1 in our lab."
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html"), "b": bad})
    with pytest.raises(SystemExit) as e:
        run(tmp_path, video)
    msg = str(e.value)
    assert "b.json" in msg and "step 1 cue 1" in msg
    assert not (tmp_path / "site" / "demo").exists()


def test_missing_video_folder_is_skipped(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    cfg = {"title": "X", "source": tmp_path / "none", "live": False}
    build.build_video(site, "demo", cfg, FakeSpeaker(tmp_path / "wavs"), {})
    assert list(site.iterdir()) == []


def test_prune_keeps_audio_of_every_module(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html"), "b": second()})
    site = run(tmp_path, video)
    audio = site / "demo" / "video" / "audio"
    before = {p.name for p in audio.glob("*.mp3")}
    stale = audio / "0000000000000000.mp3"
    stale.write_bytes(b"x")
    run(tmp_path, video)
    after = {p.name for p in audio.glob("*.mp3")}
    assert after == before and not stale.exists()


def test_no_voice_stops_when_audio_is_not_cached(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    speaker = build.CachedOnly("en-GB_GeorgeNatural", tmp_path / "empty-cache")
    with pytest.raises(SystemExit) as e:
        run(tmp_path, video, speaker)
    assert "no cached audio" in str(e.value) and "--no-voice" in str(e.value)


def test_home_links_interactive_course_while_not_live():
    html = (ROOT / "home" / "index.html").read_text()
    assert 'href="rovs/course/"' in html
    assert build.home_html(html, {"rovs": {"live": False}}) == html
    live = build.home_html(html, {"rovs": {"live": True}})
    assert 'href="rovs/video/"' in live and 'href="rovs/course/"' not in live
