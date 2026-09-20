"""Функции сохранения и загрузки данных проекта: JSON <-> объекты предметной области."""

import json
from datetime import date

from models.festivals import Festival, get_festival
from models.organizers import Organizer, get_organizer
from models.schedule import Booking
from models.venues import Venue, get_venue


def _read_json_list(filename: str) -> list[dict]:
    """Прочитать список записей из JSON-файла.

    Если файл отсутствует или содержит некорректный JSON, возвращается
    пустой список.
    """
    try:
        with open(filename, encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_json_list(filename: str, records: list[dict]) -> None:
    """Записать список записей в JSON-файл."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def load_venues(filename: str) -> list[Venue]:
    """Загрузить площадки из JSON-файла и создать объекты Venue."""
    return [Venue.from_data(record) for record in _read_json_list(filename)]


def save_venues(filename: str, venues: list[Venue]) -> None:
    """Сохранить площадки в JSON-файл."""
    _write_json_list(filename, [venue.to_data() for venue in venues])


def load_organizers(filename: str) -> list[Organizer]:
    """Загрузить организаторов из JSON-файла и создать объекты Organizer."""
    return [Organizer.from_data(record) for record in _read_json_list(filename)]


def save_organizers(filename: str, organizers: list[Organizer]) -> None:
    """Сохранить организаторов в JSON-файл."""
    _write_json_list(filename, [organizer.to_data() for organizer in organizers])


def load_festivals(filename: str, organizers: list[Organizer]) -> list[Festival]:
    """Загрузить фестивали из JSON-файла, связав их с объектами Organizer.

    Записи, ссылающиеся на несуществующего организатора, пропускаются.
    """
    festivals = []
    for record in _read_json_list(filename):
        try:
            organizer = get_organizer(organizers, record["organizer_id"])
        except KeyError:
            continue
        festival = Festival(
            record["id"],
            record["name"],
            date.fromisoformat(record["date"]),
            record["expected_attendees"],
            organizer,
        )
        festivals.append(festival)
    return festivals


def save_festivals(filename: str, festivals: list[Festival]) -> None:
    """Сохранить фестивали в JSON-файл (организатор сохраняется по id)."""
    _write_json_list(filename, [festival.to_data() for festival in festivals])


def load_bookings(filename: str, festivals: list[Festival], venues: list[Venue]) -> list[Booking]:
    """Загрузить расписание из JSON-файла, связав записи с Festival и Venue.

    Записи, ссылающиеся на несуществующий фестиваль или площадку, пропускаются.
    """
    bookings = []
    for record in _read_json_list(filename):
        try:
            festival = get_festival(festivals, record["festival_id"])
            venue = get_venue(venues, record["venue_id"])
        except KeyError:
            continue
        booking = Booking(record["id"], festival, venue)
        booking.is_cancelled = record.get("is_cancelled", False)
        bookings.append(booking)
    return bookings


def save_bookings(filename: str, bookings: list[Booking]) -> None:
    """Сохранить расписание в JSON-файл (фестиваль и площадка сохраняются по id)."""
    _write_json_list(filename, [booking.to_data() for booking in bookings])
