"""Функции для работы с площадками фестиваля."""

from collections.abc import Iterator


def add_venue(venues: dict[int, dict], name: str, capacity: int) -> int:
    """Добавить площадку в словарь venues и вернуть её идентификатор."""
    venue_id = max(venues.keys(), default=0) + 1
    venues[venue_id] = {"id": venue_id, "name": name, "capacity": capacity}
    return venue_id


def iter_venues(venues: dict[int, dict]) -> Iterator[dict]:
    """Генератор, последовательно возвращающий данные площадок."""
    for venue in venues.values():
        yield venue


def find_venue(venues: dict[int, dict], query: str) -> list[dict]:
    """Найти площадки, в названии которых встречается подстрока query."""
    query_lower = query.lower()
    return [venue for venue in iter_venues(venues) if query_lower in venue["name"].lower()]


def get_venue(venues: dict[int, dict], venue_id: int) -> dict:
    """Вернуть площадку по идентификатору.

    Вызывает KeyError, если площадка с таким id не найдена.
    """
    if venue_id not in venues:
        raise KeyError(f"Площадка с id={venue_id} не найдена")
    return venues[venue_id]


def check_venue_capacity(venues: dict[int, dict], venue_id: int, expected_attendees: int) -> bool:
    """Проверить, что вместимость площадки не меньше ожидаемого числа посетителей."""
    venue = get_venue(venues, venue_id)
    return venue["capacity"] >= expected_attendees


def filter_venues_by_capacity(venues: dict[int, dict], min_capacity: int) -> list[dict]:
    """Отобрать площадки, вмещающие не меньше min_capacity человек."""
    return [venue for venue in iter_venues(venues) if venue["capacity"] >= min_capacity]


def sort_venues(venues: dict[int, dict]) -> list[dict]:
    """Вернуть площадки, отсортированные по вместимости (по возрастанию)."""
    return sorted(iter_venues(venues), key=lambda venue: venue["capacity"])
