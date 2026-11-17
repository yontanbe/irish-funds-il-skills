"""בדיקות לדפי ה-HTML: סנכרון עם הדאטה, נגישות ועצמאות."""
import re
import sys

import pytest

PAGES = ["index.html", "tik.html", "kranot.html", "dmei-nihul.html"]


@pytest.fixture(scope="module")
def built(root):
    sys.path.insert(0, str(root / "scripts"))
    import build_site
    return build_site.build()


@pytest.mark.parametrize("name", PAGES)
def test_committed_page_matches_fresh_build(root, built, name):
    committed = (root / "docs" / name).read_text(encoding="utf-8")
    assert committed == built[name], "הדף לא מסונכרן. להריץ python3 scripts/build_site.py"


@pytest.mark.parametrize("name", PAGES)
def test_page_is_hebrew_rtl_and_mobile_ready(built, name):
    html = built[name]
    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="he" dir="rtl">' in html
    assert 'name="viewport" content="width=device-width, initial-scale=1"' in html
    assert re.search(r"<title>[^<]+</title>", html)
    assert html.count("<h1>") == 1
    assert "<main>" in html and 'aria-label="ניווט ראשי"' in html


@pytest.mark.parametrize("name", PAGES)
def test_page_shows_disclaimer(built, name):
    assert "אינו ייעוץ השקעות" in built[name]


@pytest.mark.parametrize("name", PAGES)
def test_page_is_self_contained(built, name):
    """אין טעינה של קבצים חיצוניים: אין מעקב, והדף עובד גם בלי רשת."""
    html = built[name]
    assert not re.search(r"<script[^>]+src=", html)
    assert not re.search(r"<link[^>]+href=", html)
    assert not re.search(r"<img[^>]+src=[\"']https?:", html)
    assert "fetch(" not in html and "XMLHttpRequest" not in html
    assert "localStorage" not in html and "document.cookie" not in html


@pytest.mark.parametrize("name", PAGES)
def test_every_form_control_has_a_label(built, name):
    html = built[name]
    labelled = set(re.findall(r'<label[^>]+for="([^"]+)"', html))
    for tag in re.findall(r"<(?:input|select)\b[^>]*>", html):
        m = re.search(r'\bid="([^"]+)"', tag)
        assert m, f"לשדה אין מזהה: {tag}"
        assert m.group(1) in labelled, f"לשדה {m.group(1)} אין תווית"


@pytest.mark.parametrize("name", PAGES)
def test_touch_targets_and_focus_styles_exist(built, name):
    html = built[name]
    assert "min-height:48px" in html
    assert ":focus-visible" in html
    assert "prefers-color-scheme:dark" in html


def test_nav_marks_current_page(built):
    for name in PAGES:
        assert built[name].count('aria-current="page"') == 1
        assert f'<a href="{name}" aria-current="page">' in built[name]


def test_tables_have_header_scopes(built):
    for name in ["kranot.html", "dmei-nihul.html"]:
        assert 'scope="col"' in built[name]


def test_dynamic_regions_announce_changes(built):
    assert 'aria-live="polite"' in built["tik.html"]
    assert 'role="alert"' in built["tik.html"]
    assert 'role="alert"' in built["dmei-nihul.html"]


def test_builder_page_embeds_all_funds(built, data):
    for f in data["funds"]["funds"]:
        assert f["tase_number"] in built["tik.html"]
        assert f["tase_number"] in built["kranot.html"]


def test_text_contrast_meets_wcag_aa(root):
    """יחס ניגודיות של 4.5 לפחות בין צבעי הטקסט לרקעים, במצב בהיר ובמצב כהה."""
    sys.path.insert(0, str(root / "scripts"))
    import build_site

    def lum(hex_color):
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        vals = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        vals = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in vals]
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]

    def ratio(a, b):
        la, lb = sorted((lum(a), lum(b)), reverse=True)
        return (la + 0.05) / (lb + 0.05)

    blocks = re.findall(r":root\{([^}]+)\}", build_site.CSS)
    assert len(blocks) == 2
    for block in blocks:
        v = dict(re.findall(r"--([\w-]+):(#[0-9a-fA-F]{3,6})", block))
        pairs = [("ink", "bg"), ("ink", "card"), ("muted", "bg"), ("muted", "card"),
                 ("accent", "card"), ("accent", "bg"), ("accent-ink", "accent"), ("warn-ink", "warn-bg")]
        for fg, bg in pairs:
            assert ratio(v[fg], v[bg]) >= 4.5, f"ניגודיות נמוכה: {fg} על {bg} = {ratio(v[fg], v[bg]):.2f}"
