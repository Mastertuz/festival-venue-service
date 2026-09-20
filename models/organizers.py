"""Класс Organizer (организатор) и функции для работы с коллекцией организаторов."""


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


def add_organizer(organizers: list[Organizer], name: str) -> Organizer:
    """Создать организатора, добавить его в коллекцию organizers и вернуть объект."""
    organizer_id = max((org.id for org in organizers), default=0) + 1
    organizer = Organizer(organizer_id, name)
    organizers.append(organizer)
    return organizer


def show_organizers(organizers: list[Organizer]) -> None:
    """Вывести информацию об объектах Organizer."""
    if not organizers:
        print("Список организаторов пуст.")
        return
    for organizer in organizers:
        print(f"{organizer.id}. {organizer}")


def find_organizer(organizers: list[Organizer], query: str) -> list[Organizer]:
    """Найти организаторов, в названии которых встречается подстрока query."""
    query_lower = query.lower()
    return [org for org in organizers if query_lower in org.name.lower()]


def get_organizer(organizers: list[Organizer], organizer_id: int) -> Organizer:
    """Вернуть организатора по идентификатору.

    Вызывает KeyError, если организатор с таким id не найден.
    """
    for organizer in organizers:
        if organizer.id == organizer_id:
            return organizer
    raise KeyError(f"Организатор с id={organizer_id} не найден")
