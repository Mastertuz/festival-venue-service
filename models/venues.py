"""Функции для работы с площадками фестиваля."""

from collections.abc import Iterator


class Venue:
    """Площадка, доступная для проведения фестиваля."""

    def __init__(self, venue_id: int, name: str, capacity: int) -> None:
        """Создать объект площадки."""
        self.id = venue_id
        self.name = name
        self.capacity = capacity

    def is_suitable_for(self, expected_attendees: int) -> bool:
        """Проверить, что вместимость площадки не меньше ожидаемого числа посетителей."""
        return self.capacity >= expected_attendees

    def __str__(self) -> str:
        """Вернуть удобное строковое представление площадки."""
        return f"{self.name} (вместимость {self.capacity} чел.)"

    @staticmethod
    def validate_capacity(capacity: int) -> bool:
        """Проверить корректность значения вместимости (должно быть положительным)."""
        return capacity > 0

    @classmethod
    def from_data(cls, data: dict) -> "Venue":
        """Создать площадку из словаря данных (например, загруженного из JSON)."""
        return cls(data["id"], data["name"], data["capacity"])

    def to_data(self) -> dict:
        """Представить площадку в виде словаря для сохранения в JSON."""
        return {"id": self.id, "name": self.name, "capacity": self.capacity}


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
