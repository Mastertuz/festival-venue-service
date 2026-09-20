"""Функции для работы с организаторами фестивалей."""

from collections.abc import Iterator


def add_organizer(organizers: dict[int, dict], name: str) -> int:
    """Добавить организатора в словарь organizers и вернуть его идентификатор."""
    organizer_id = max(organizers.keys(), default=0) + 1
    organizers[organizer_id] = {"id": organizer_id, "name": name}
    return organizer_id


def iter_organizers(organizers: dict[int, dict]) -> Iterator[dict]:
    """Генератор, последовательно возвращающий данные организаторов."""
    for organizer in organizers.values():
        yield organizer


def find_organizer(organizers: dict[int, dict], query: str) -> list[dict]:
    """Найти организаторов, в названии которых встречается подстрока query."""
    query_lower = query.lower()
    return [org for org in iter_organizers(organizers) if query_lower in org["name"].lower()]


def get_organizer(organizers: dict[int, dict], organizer_id: int) -> dict:
    """Вернуть организатора по идентификатору.

    Вызывает KeyError, если организатор с таким id не найден.
    """
    if organizer_id not in organizers:
        raise KeyError(f"Организатор с id={organizer_id} не найден")
    return organizers[organizer_id]
