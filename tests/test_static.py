from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import Client

STATIC_FILES = [
    "homepage/css/style.css",
    "homepage/js/main.js",
    "homepage/img/logo.png",
]


def test_static_files_are_found_by_django():
    for name in STATIC_FILES:
        assert finders.find(name), name


def test_logo_is_a_png_image():
    path = finders.find("homepage/img/logo.png")
    assert Path(path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_custom_css_describes_project_classes():
    css = Path(finders.find("homepage/css/style.css")).read_text(encoding="utf-8")
    for selector in (".venue-card", ".booking-status", ".fvs-logo"):
        assert selector in css


def test_main_js_sets_current_year():
    js = Path(finders.find("homepage/js/main.js")).read_text(encoding="utf-8")
    assert "current-year" in js
    assert "getFullYear" in js


def test_base_template_links_static_files(squash):
    html = squash(Client().get("/"))
    assert 'href="/static/homepage/css/style.css"' in html
    assert 'src="/static/homepage/img/logo.png"' in html
    assert 'src="/static/homepage/js/main.js"' in html
    assert 'class="fvs-logo"' in html
    assert '<span id="current-year"></span>' in html


def test_all_pages_inherit_static_files_from_base_template(web_data):
    for url in ("/", "/venues/", "/venues/1/", "/bookings/", "/bookings/1/"):
        html = Client().get(url).content.decode()
        assert "/static/homepage/css/style.css" in html, url
        assert "/static/homepage/js/main.js" in html, url


def test_cards_and_statuses_use_custom_classes(web_data):
    assert "venue-card" in Client().get("/venues/").content.decode()
    assert "booking-status" in Client().get("/bookings/").content.decode()
