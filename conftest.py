"""Общие фикстуры тестов. Django и тестовую базу настраивает pytest-django."""

import json
from datetime import date

import pytest

import db.database
import db.import_json
from bookings.models import Booking
from festivals.models import Festival, Organizer
from venues.models import Venue


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Путь к временной базе SQLite: подменяет db.database.DB_PATH на время теста."""
    path = tmp_path / "test.sqlite"
    monkeypatch.setattr(db.database, "DB_PATH", path)
    return path


@pytest.fixture
def empty_db(db_path):
    """Временная база SQLite с таблицами, но без данных."""
    connection = db.database.get_connection(must_exist=False)
    try:
        db.database.init_schema(connection)
        connection.commit()
    finally:
        connection.close()
    return db_path


@pytest.fixture
def web_data(tmp_path, monkeypatch, db_path):
    """Временная база SQLite, заполненная скриптом импорта из временных JSON-файлов."""
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
    attributes = {
        "venues": "VENUES_FILE",
        "organizers": "ORGANIZERS_FILE",
        "festivals": "FESTIVALS_FILE",
        "bookings": "BOOKINGS_FILE",
    }
    for name, records in files.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(db.import_json, attributes[name], path)
    db.import_json.main()
    return db_path


@pytest.fixture
def squash():
    """Вернуть функцию, сжимающую пробельные символы в HTML-ответе до одного пробела."""

    def _squash(response) -> str:
        return " ".join(response.content.decode().split())

    return _squash


@pytest.fixture
def orm_data(db):
    """Тестовые данные в базе Django: две площадки, фестиваль на сегодня и два бронирования.

    Бронирование 1 активно (площадка «Городской парк»), бронирование 2 отменено
    (площадка «Арена <b>»): отменённое бронирование площадку не блокирует.
    """
    organizer = Organizer.objects.create(name="АНО «Арт-Ивент»")
    park = Venue.objects.create(name="Городской парк", capacity=5000)
    arena = Venue.objects.create(name="Арена <b>", capacity=2000)
    festival = Festival.objects.create(
        name="Фестиваль уличной музыки",
        date=date.today(),
        expected_attendees=4500,
        organizer=organizer,
    )
    active = Booking.objects.create(festival=festival, venue=park)
    cancelled = Booking.objects.create(festival=festival, venue=arena, is_cancelled=True)
    return {
        "organizer": organizer,
        "park": park,
        "arena": arena,
        "festival": festival,
        "active": active,
        "cancelled": cancelled,
    }
