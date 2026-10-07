from pathlib import Path

import homepage.views

ROOT = Path(__file__).resolve().parent.parent
VIEW_FILES = [ROOT / app / "views.py" for app in ("homepage", "venues", "bookings")]


def test_page_helper_is_removed():
    assert not hasattr(homepage.views, "page")


def test_views_do_not_build_html_in_python():
    for path in VIEW_FILES:
        source = path.read_text(encoding="utf-8")
        assert "HttpResponse" not in source, path.name
        assert "<html" not in source and "<div" not in source, path.name
        assert "page(" not in source, path.name


def test_views_use_render():
    for path in VIEW_FILES:
        source = path.read_text(encoding="utf-8")
        assert "from django.shortcuts import render" in source, path.name
        assert "return render(" in source, path.name
