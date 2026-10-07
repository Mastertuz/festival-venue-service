"""Настройка Django для тестов веб-слоя (pytest без pytest-django)."""

import json
import os
from datetime import date

import django
import pytest
from django.test.utils import setup_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "venue_service.settings")
django.setup()
setup_test_environment()


@pytest.fixture
def web_data(tmp_path, monkeypatch):
    """Временная папка data/ с JSON-файлами; страницы читают её по относительным путям."""
    today = date.today().isoformat()
    files = {
        "venues": [
            {"id": 1, "name": "Городской парк", "capacity": 5000},
            {"id": 2, "name": "Арена <b>", "capacity": 2000},
        ],
        "organizers": [{"id": 1, "name": "АНО «Арт-Ивент»"}],
        "festivals": [
            {
                "id": 1,
                "name": "Фестиваль уличной музыки",
                "date": today,
                "expected_attendees": 4500,
                "organizer_id": 1,
            }
        ],
        "bookings": [
            {"id": 1, "festival_id": 1, "venue_id": 1, "is_cancelled": False},
            {"id": 2, "festival_id": 1, "venue_id": 2, "is_cancelled": True},
        ],
    }
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name, records in files.items():
        (data_dir / f"{name}.json").write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8"
        )
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def squash():
    """Вернуть функцию, сжимающую пробельные символы в HTML-ответе до одного пробела."""

    def _squash(response) -> str:
        return " ".join(response.content.decode().split())

    return _squash
