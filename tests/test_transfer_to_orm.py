import hashlib
import sqlite3
from datetime import date

import pytest

import db.import_sqlite_to_orm as transfer_module
from bookings.models import Booking
from db.database import BASE_DIR, SCHEMA_FILE
from db.import_sqlite_to_orm import transfer
from db.inspect_source_db import inspect, open_source
from db.inspect_source_db import main as inspect_main
from festivals.models import Festival, Organizer
from venues.models import Venue

pytestmark = pytest.mark.django_db

PROJECT_SOURCE = BASE_DIR / "data" / "festival_venue.sqlite"


def make_source(path, bookings_rows=None):
    """Создать исходную базу по схеме ПР7 и заполнить её небольшим набором данных."""
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    connection.execute("INSERT INTO organizers (id, name) VALUES (7, 'Организатор')")
    connection.executemany(
        "INSERT INTO venues (id, name, capacity) VALUES (?, ?, ?)",
        [(10, "Парк", 5000), (20, "Арена", 2000)],
    )
    connection.execute(
        "INSERT INTO festivals (id, name, date, expected_attendees, organizer_id) "
        "VALUES (30, 'Фестиваль', '2026-11-07', 1200, 7)"
    )
    connection.executemany(
        "INSERT INTO bookings (id, festival_id, venue_id, is_cancelled) VALUES (?, ?, ?, ?)",
        bookings_rows or [(40, 30, 10, 0), (41, 30, 20, 1)],
    )
    connection.commit()
    connection.close()
    return path


@pytest.fixture
def source(tmp_path):
    return make_source(tmp_path / "source.sqlite")


def test_transfer_copies_all_records(source):
    counts = transfer(source)
    assert counts == {"organizers": 1, "venues": 2, "festivals": 1, "bookings": 2}


def test_identifiers_are_preserved(source):
    transfer(source)
    assert Organizer.objects.get(pk=7).name == "Организатор"
    assert Venue.objects.get(pk=10).capacity == 5000
    assert Booking.objects.filter(pk__in=[40, 41]).count() == 2


def test_foreign_keys_point_to_transferred_objects(source):
    transfer(source)
    booking = Booking.objects.select_related("festival__organizer", "venue").get(pk=40)
    assert booking.venue.name == "Парк"
    assert booking.festival.name == "Фестиваль"
    assert booking.festival.organizer_id == 7


def test_date_string_becomes_date_and_flag_becomes_bool(source):
    transfer(source)
    assert Festival.objects.get(pk=30).date == date(2026, 11, 7)
    assert Booking.objects.get(pk=40).is_cancelled is False
    assert Booking.objects.get(pk=41).is_cancelled is True


def test_transfer_is_repeatable_without_duplicates(source):
    first = transfer(source)
    second = transfer(source)
    assert first == second


def test_repeated_transfer_updates_changed_records(source):
    transfer(source)
    connection = sqlite3.connect(source)
    connection.execute("UPDATE venues SET name = 'Парк (новый)' WHERE id = 10")
    connection.commit()
    connection.close()
    transfer(source)
    assert Venue.objects.get(pk=10).name == "Парк (новый)"
    assert Venue.objects.count() == 2


def test_new_objects_get_identifiers_after_transferred_ones(source):
    transfer(source)
    venue = Venue.objects.create(name="Новая", capacity=10)
    assert venue.pk > 20


def test_source_database_is_not_modified(source):
    before = hashlib.md5(source.read_bytes()).hexdigest()
    transfer(source)
    assert hashlib.md5(source.read_bytes()).hexdigest() == before


def test_transfer_is_atomic(source, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("сбой при записи бронирований")

    monkeypatch.setattr(transfer_module.Booking.objects, "update_or_create", broken)
    with pytest.raises(RuntimeError):
        transfer(source)
    assert Organizer.objects.count() == 0
    assert Venue.objects.count() == 0
    assert Festival.objects.count() == 0


def test_invalid_source_is_rejected_before_any_write(tmp_path):
    path = make_source(tmp_path / "bad.sqlite", bookings_rows=[(40, 99, 10, 0)])
    with pytest.raises(ValueError, match="несуществующий фестиваль"):
        transfer(path)
    assert Booking.objects.count() == 0
    assert Venue.objects.count() == 0


def test_missing_source_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        transfer(tmp_path / "missing.sqlite")


def test_inspection_reports_tables_columns_and_counts(source):
    with open_source(source) as connection:
        report = inspect(connection)
    assert set(report["tables"]) == {"organizers", "venues", "festivals", "bookings"}
    assert report["counts"] == {"organizers": 1, "venues": 2, "festivals": 1, "bookings": 2}
    assert report["problems"] == []
    column_names = [column[0] for column in report["tables"]["bookings"]]
    assert column_names == ["id", "festival_id", "venue_id", "is_cancelled"]


def test_inspection_finds_bad_dates_and_flags(tmp_path):
    path = make_source(tmp_path / "source.sqlite")
    connection = sqlite3.connect(path)
    connection.execute("UPDATE festivals SET date = '07.11.2026' WHERE id = 30")
    connection.commit()
    connection.close()
    with open_source(path) as opened:
        problems = inspect(opened)["problems"]
    assert any("дата" in problem for problem in problems)


def test_inspection_script_prints_report(monkeypatch, source, capsys):
    monkeypatch.setattr("db.inspect_source_db.SOURCE_DB", source)
    inspect_main()
    output = capsys.readouterr().out
    assert "Таблица: bookings" in output
    assert "проблем не найдено" in output


def test_project_source_database_is_consistent():
    with open_source(PROJECT_SOURCE) as connection:
        report = inspect(connection)
    assert report["problems"] == []
    assert report["counts"] == {"organizers": 3, "venues": 4, "festivals": 7, "bookings": 8}


def test_project_data_is_transferred_with_relations():
    counts = transfer(PROJECT_SOURCE)
    assert counts == {"organizers": 3, "venues": 4, "festivals": 7, "bookings": 8}
    assert Booking.objects.get(pk=6).is_cancelled is True
    assert Venue.objects.get(pk=1).bookings.filter(is_cancelled=False).count() == 3
    assert Venue.objects.get(name="Летняя эстрада").bookings.count() == 0
