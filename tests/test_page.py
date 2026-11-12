import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "video"))

import page  # noqa: E402

COURSE = {"slug": "cyber-vault", "title": "Cyber Vault"}
TIMELINE = {
    "course": "Cyber Vault",
    "section": "Start here",
    "title": "Why backups need a vault",
    "unit": "m0-u1-why-backups-need-a-vault.html",
    "sketches": {},
    "steps": [
        {"title": "Welcome", "cues": [
            {"slide": {"type": "statement", "head": "Backups get attacked"},
             "say": "Welcome.", "do": [["show", "head"]], "dur": 1.5,
             "audio": "audio/aaaaaaaaaaaaaaaa.mp3"},
        ]},
    ],
}


class Visible(HTMLParser):
    """Collects the text a learner sees or hears: text nodes and label attributes."""

    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        for k, v in attrs:
            if k in ("aria-label", "title", "alt", "placeholder") and v:
                self.parts.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def visible_text(html):
    v = Visible()
    v.feed(html)
    return " ".join(v.parts)


def module_page(index=3, total=17, prev_href="m2.html", next_href="m4.html"):
    return page.render_module(TIMELINE, COURSE, index, total, prev_href, next_href)


def test_module_page_has_module_n_of_total():
    assert "Module 3 of 17" in module_page()


def test_captions_off_by_default():
    html = module_page()
    assert 'class="cc off"' in html
    button = re.search(r'<button[^>]*id="ccbtn"[^>]*>', html).group(0)
    assert not re.search(r'class="[^"]*\bon\b', button)


def test_no_cdn():
    html = module_page()
    tags = re.findall(r"<(?:script|link)\b[^>]*>", html)
    assert tags
    for tag in tags:
        for value in re.findall(r'\b(?:src|href)="([^"]*)"', tag):
            assert "http" not in value, tag


def test_step_buttons_say_step():
    html = module_page()
    assert 'aria-label="Previous step"' in html
    assert 'aria-label="Next step"' in html
    assert "clip" not in visible_text(html).lower()


def test_contents_groups_by_section():
    modules = [
        {"title": "Why backups need a vault", "section": "Start here", "href": "m0-u1.html", "minutes": 8},
        {"title": "How the vault works", "section": "Start here", "href": "m0-u2.html", "minutes": 7},
        {"title": "Attacker with keys", "section": "The threat", "href": "m1-u1.html", "minutes": 9},
    ]
    html = page.render_contents(COURSE, modules)
    first, second = html.index("Start here"), html.index("The threat")
    assert first < second
    assert len(re.findall(r"<h2\b", html)) == 2
    assert html.index('href="m0-u1.html"') > first
    assert html.index('href="m0-u2.html"') > first
    assert first < html.index('href="m0-u2.html"') < second
    assert html.index('href="m1-u1.html"') > second


def test_contents_marks_modules_by_position_for_done_state():
    modules = [
        {"title": "A", "section": "S", "href": "a.html", "minutes": 1},
        {"title": "B", "section": "S", "href": "b.html", "minutes": 1},
    ]
    html = page.render_contents(COURSE, modules)
    assert 'data-module="1"' in html and 'data-module="2"' in html
    assert 'data-course="cyber-vault"' in html


def test_module_page_remembers_which_module_it_is_for_completion():
    html = module_page()
    assert '"moduleIndex": 3' in html and '"courseSlug": "cyber-vault"' in html


def test_script_text_cannot_close_the_script_tag():
    tl = dict(TIMELINE, title="</script><b>x")
    html = page.render_module(tl, COURSE, 1, 2, None, None)
    assert "</script><b>" not in html


def test_first_module_has_no_previous_link_and_last_has_no_next():
    html = page.render_module(TIMELINE, COURSE, 1, 1, None, None)
    assert 'id="prevmod"' not in html and 'id="nextmod"' not in html


def test_copy_assets_puts_player_rough_and_fonts_together(tmp_path):
    import pytest
    if not page.SHARED_ASSETS.exists():
        pytest.skip("shared course assets not on this machine")
    page.copy_assets(tmp_path / "video-assets")
    out = tmp_path / "video-assets"
    assert (out / "player.js").exists() and (out / "player.css").exists()
    assert (out / "rough.js").exists() and any((out / "fonts").glob("*.woff2"))


def test_caption_button_reports_its_state():
    assert 'id="ccbtn" aria-label="Captions" aria-pressed="false"' in module_page()
