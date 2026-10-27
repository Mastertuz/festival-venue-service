"""Общие фикстуры тестов. Django и тестовую базу настраивает pytest-django."""

from datetime import date

import pytest

import db.database
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
