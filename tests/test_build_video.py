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


class NoCalls:
    voice = ""

    def wav(self, text):
        raise AssertionError("the speaker was called")


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
        shot = course / "assets" / "shot-console.png"
        if not shot.exists():
            shot.parent.mkdir(exist_ok=True)
            shot.write_bytes(b"png-of-" + stem.encode())
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


def test_rebuild_keeps_mp3_bytes_and_skips_the_speaker(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    site = run(tmp_path, video)
    audio = site / "demo" / "video" / "audio"
    mp3 = sorted(audio.glob("*.mp3"))[0]
    mp3.write_bytes(b"changed")
    run(tmp_path, video, NoCalls())
    assert mp3.read_bytes() == b"changed"


def test_no_voice_works_with_mp3s_and_no_wav_cache(tmp_path, monkeypatch):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    site = run(tmp_path, video)
    import voice
    monkeypatch.setattr(voice, "shared_pronunciation", lambda: {})
    monkeypatch.setattr(voice, "voice_name", lambda: "")
    monkeypatch.setattr(build, "SITE", site)
    monkeypatch.setattr(build, "VIDEO", {"demo": {"title": "Demo course", "source": video, "live": False}})
    build.build_videos(no_voice=True)
    assert (site / "demo" / "video" / "a.html").is_file()


def test_no_voice_stops_for_a_cue_without_an_mp3(tmp_path, monkeypatch):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    import voice
    monkeypatch.setattr(voice, "shared_pronunciation", lambda: {})
    monkeypatch.setattr(voice, "voice_name", lambda: "")
    monkeypatch.setattr(build, "SITE", tmp_path / "site")
    monkeypatch.setattr(build, "VIDEO", {"demo": {"title": "Demo course", "source": video, "live": False}})
    with pytest.raises(SystemExit) as e:
        build.build_videos(no_voice=True)
    assert "no cached audio" in str(e.value) and "--no-voice" in str(e.value)


def test_reset_site_keeps_each_courses_audio(tmp_path):
    site = tmp_path / "site"
    (site / "demo" / "video" / "audio").mkdir(parents=True)
    (site / "demo" / "video" / "audio" / "x.mp3").write_bytes(b"keep")
    (site / "demo" / "video" / "a.html").write_text("old")
    build.reset_site(site, ["demo", "other"])
    assert (site / "demo" / "video" / "audio" / "x.mp3").read_bytes() == b"keep"
    assert not (site / "demo" / "video" / "a.html").exists()


def test_failure_during_the_wipe_leaves_audio_intact(tmp_path, monkeypatch):
    site = tmp_path / "site"
    for slug in ("demo", "other"):
        (site / slug / "video" / "audio").mkdir(parents=True)
        (site / slug / "video" / "audio" / "x.mp3").write_bytes(b"keep")
        (site / slug / "video" / "a.html").write_text("old")
    (site / "demo" / "junk").mkdir()
    (site / "other" / "junk").mkdir()
    real = build.shutil.rmtree

    def failing(path, *a, **k):
        if Path(path).name in ("site", "junk"):
            raise OSError("disk error")
        return real(path, *a, **k)

    monkeypatch.setattr(build.shutil, "rmtree", failing)
    with pytest.raises(OSError):
        build.reset_site(site, ["demo", "other"])
    for slug in ("demo", "other"):
        assert (site / slug / "video" / "audio" / "x.mp3").read_bytes() == b"keep"


def test_failing_check_leaves_docs_untouched_and_reports_every_course(tmp_path, monkeypatch):
    bad = second()
    bad["steps"][0]["cues"][0]["say"] = "This runs in unit 1.1."
    v1 = make_source(tmp_path / "one", {"a": dict(bad, unit="a.html")})
    v2 = make_source(tmp_path / "two", {"a": dict(bad, unit="a.html")})
    site = tmp_path / "site"
    site.mkdir()
    (site / "sentinel.txt").write_text("x")
    monkeypatch.setattr(build, "SITE", site)
    monkeypatch.setattr(build, "VIDEO", {"c1": {"title": "One", "source": v1, "live": False},
                                         "c2": {"title": "Two", "source": v2, "live": False}})
    with pytest.raises(SystemExit) as e:
        build.build()
    assert "c1" in str(e.value) and "c2" in str(e.value)
    assert (site / "sentinel.txt").read_text() == "x"


def test_back_links_on_built_pages(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    out = run(tmp_path, video) / "demo" / "video"
    assert 'id="contents" href="index.html"' in (out / "a.html").read_text()
    index = (out / "index.html").read_text()
    assert 'class="backlink"' in index and 'href="../../"' in index


def test_page_default_has_no_back_link():
    import page
    tl = {"title": "T", "steps": []}
    course = {"slug": "s", "title": "C"}
    assert "backlink" not in page.render_module(tl, course, 1, 1, None, None)
    assert "backlink" not in page.render_contents(course, [{"section": "S", "title": "T", "href": "t.html", "minutes": 1}])


def test_home_links_interactive_course_while_not_live():
    html = (ROOT / "home" / "index.html").read_text()
    assert 'href="rovs/course/"' in html
    assert build.home_html(html, {"rovs": {"live": False}}) == html
    live = build.home_html(html, {"rovs": {"live": True}})
    assert 'href="rovs/video/"' in live and 'href="rovs/course/"' not in live


def test_module_pages_list_the_whole_course(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html"), "b": second()})
    html = (run(tmp_path, video) / "demo" / "video" / "a.html").read_text()
    assert 'data-tab="course"' in html and 'href="b.html"' in html.split('id="course"')[1]


def timeline_of(page_html):
    start = page_html.index("window.TIMELINE = ") + len("window.TIMELINE = ")
    return json.JSONDecoder().raw_decode(page_html[start:])[0]


def screen_imgs(timeline):
    return [c["slide"]["img"] for st in timeline["steps"] for c in st["cues"]
            if c.get("slide", {}).get("type") == "screen"]


def test_screen_image_is_copied_and_the_page_points_at_the_copy(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    out = run(tmp_path, video) / "demo" / "video"
    [img] = screen_imgs(timeline_of((out / "a.html").read_text()))
    assert img.startswith("images/") and img.endswith("shot-console.png")
    assert (out / img).read_bytes() == b"png-of-a"


def test_same_basename_from_different_sources_both_survive(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html"), "b": second()})
    other = video.parent / "other"
    other.mkdir()
    (other / "shot-console.png").write_bytes(b"different")
    s = json.loads((video / "b.json").read_text())
    s["steps"][3]["cues"][0]["slide"]["img"] = "other/shot-console.png"
    (video / "b.json").write_text(json.dumps(s))
    (video.parent / "b.html").write_text(UNIT.replace("assets/shot-console.png", "other/shot-console.png"))
    out = run(tmp_path, video) / "demo" / "video"
    ia = screen_imgs(timeline_of((out / "a.html").read_text()))[0]
    ib = screen_imgs(timeline_of((out / "b.html").read_text()))[0]
    assert ia != ib
    assert (out / ia).read_bytes() == b"png-of-a" and (out / ib).read_bytes() == b"different"


def test_stale_screen_images_are_removed_on_rebuild(tmp_path):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    site = run(tmp_path, video)
    stale = site / "demo" / "video" / "images" / "old.png"
    stale.write_bytes(b"x")
    run(tmp_path, video)
    assert not stale.exists()


def test_missing_screen_image_stops_the_build_before_docs_is_touched(tmp_path, monkeypatch):
    video = make_source(tmp_path, {"a": dict(GOOD, unit="a.html")})
    (video.parent / "assets" / "shot-console.png").unlink()
    site = tmp_path / "site"
    site.mkdir()
    (site / "sentinel.txt").write_text("x")
    monkeypatch.setattr(build, "SITE", site)
    monkeypatch.setattr(build, "VIDEO", {"demo": {"title": "D", "source": video, "live": False}})
    with pytest.raises(SystemExit) as e:
        build.build()
    msg = str(e.value)
    assert "a.json" in msg and "step 4" in msg and "shot-console.png" in msg
    assert (site / "sentinel.txt").read_text() == "x"
