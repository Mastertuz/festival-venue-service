"""Функции для работы с фестивалями."""

from collections.abc import Iterator
from datetime import date

from models.organizers import get_organizer


def add_festival(
    festivals: dict[int, dict],
    organizers: dict[int, dict],
    name: str,
    festival_date: date,
    expected_attendees: int,
    organizer_id: int,
) -> int:
    """Добавить фестиваль в словарь festivals и вернуть его идентификатор.

    Вызывает KeyError, если организатор с указанным id не найден.
    """
    get_organizer(organizers, organizer_id)
    festival_id = max(festivals.keys(), default=0) + 1
    festivals[festival_id] = {
        "id": festival_id,
        "name": name,
        "date": festival_date.isoformat(),
        "expected_attendees": expected_attendees,
        "organizer_id": organizer_id,
    }
    return festival_id


def iter_festivals(festivals: dict[int, dict]) -> Iterator[dict]:
    """Генератор, последовательно возвращающий данные фестивалей."""
    for festival in festivals.values():
        yield festival


def get_festival(festivals: dict[int, dict], festival_id: int) -> dict:
    """Вернуть фестиваль по идентификатору.

    Вызывает KeyError, если фестиваль с таким id не найден.
    """
    if festival_id not in festivals:
        raise KeyError(f"Фестиваль с id={festival_id} не найден")
    return festivals[festival_id]


def find_festival(festivals: dict[int, dict], query: str) -> list[dict]:
    """Найти фестивали, в названии которых встречается подстрока query."""
    query_lower = query.lower()
    return [f for f in iter_festivals(festivals) if query_lower in f["name"].lower()]


def filter_festivals_by_min_attendees(festivals: dict[int, dict], min_attendees: int) -> list[dict]:
    """Отобрать фестивали с ожидаемым числом посетителей не меньше min_attendees."""
    return [f for f in iter_festivals(festivals) if f["expected_attendees"] >= min_attendees]


def sort_festivals_by_date(festivals: dict[int, dict]) -> list[dict]:
    """Вернуть фестивали, отсортированные по дате проведения."""
    return sorted(iter_festivals(festivals), key=lambda f: f["date"])
