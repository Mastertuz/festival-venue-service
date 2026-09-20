"""Функции для работы с организаторами фестивалей."""

from collections.abc import Iterator


class Organizer:
    """Организатор фестиваля — ответственное лицо или организация."""

    def __init__(self, organizer_id: int, name: str) -> None:
        """Создать объект организатора."""
        self.id = organizer_id
        self.name = name

    def __str__(self) -> str:
        """Вернуть удобное строковое представление организатора."""
        return self.name

    @classmethod
    def from_data(cls, data: dict) -> "Organizer":
        """Создать организатора из словаря данных (например, загруженного из JSON)."""
        return cls(data["id"], data["name"])

    def to_data(self) -> dict:
        """Представить организатора в виде словаря для сохранения в JSON."""
        return {"id": self.id, "name": self.name}


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
