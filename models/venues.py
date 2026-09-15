"""Класс Venue (площадка) и функции для работы с коллекцией площадок."""


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


def add_venue(venues: list[Venue], name: str, capacity: int) -> Venue:
    """Создать площадку, добавить её в коллекцию venues и вернуть созданный объект.

    Вызывает ValueError, если вместимость некорректна.
    """
    if not Venue.validate_capacity(capacity):
        raise ValueError("Вместимость площадки должна быть положительным числом")
    venue_id = max((venue.id for venue in venues), default=0) + 1
    venue = Venue(venue_id, name, capacity)
    venues.append(venue)
    return venue


def find_venue(venues: list[Venue], query: str) -> list[Venue]:
    """Найти площадки, в названии которых встречается подстрока query."""
    query_lower = query.lower()
    return [venue for venue in venues if query_lower in venue.name.lower()]


def get_venue(venues: list[Venue], venue_id: int) -> Venue:
    """Вернуть площадку по идентификатору.

    Вызывает KeyError, если площадка с таким id не найдена.
    """
    for venue in venues:
        if venue.id == venue_id:
            return venue
    raise KeyError(f"Площадка с id={venue_id} не найдена")


def filter_venues_by_capacity(venues: list[Venue], min_capacity: int) -> list[Venue]:
    """Отобрать площадки, вмещающие не меньше min_capacity человек."""
    return [venue for venue in venues if venue.capacity >= min_capacity]


def sort_venues(venues: list[Venue]) -> list[Venue]:
    """Вернуть площадки, отсортированные по вместимости (по возрастанию)."""
    return sorted(venues, key=lambda venue: venue.capacity)
