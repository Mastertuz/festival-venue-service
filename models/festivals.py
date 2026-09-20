"""Класс Festival и функции для работы с коллекцией фестивалей."""

from datetime import date

from .organizers import Organizer, get_organizer


class Festival:
    """Фестиваль — мероприятие, для которого подбирается площадка."""

    def __init__(
        self,
        festival_id: int,
        name: str,
        festival_date: date,
        expected_attendees: int,
        organizer: Organizer,
    ) -> None:
        """Создать объект фестиваля, связав его с организатором."""
        self.id = festival_id
        self.name = name
        self.date = festival_date
        self.expected_attendees = expected_attendees
        self.organizer = organizer

    def __str__(self) -> str:
        """Вернуть удобное строковое представление фестиваля."""
        return (
            f"{self.name} — {self.date.isoformat()}, "
            f"{self.expected_attendees} посетителей (организатор: {self.organizer})"
        )

    def to_data(self) -> dict:
        """Представить фестиваль в виде словаря для сохранения в JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date.isoformat(),
            "expected_attendees": self.expected_attendees,
            "organizer_id": self.organizer.id,
        }


def add_festival(
    festivals: list[Festival],
    organizers: list[Organizer],
    name: str,
    festival_date: date,
    expected_attendees: int,
    organizer_id: int,
) -> Festival:
    """Создать фестиваль, связав его с существующим организатором.

    Вызывает KeyError, если организатор с указанным id не найден.
    """
    organizer = get_organizer(organizers, organizer_id)
    festival_id = max((festival.id for festival in festivals), default=0) + 1
    festival = Festival(festival_id, name, festival_date, expected_attendees, organizer)
    festivals.append(festival)
    return festival


def show_festivals(festivals: list[Festival]) -> None:
    """Вывести информацию об объектах Festival."""
    if not festivals:
        print("Список фестивалей пуст.")
        return
    for festival in festivals:
        print(f"{festival.id}. {festival}")


def find_festival(festivals: list[Festival], query: str) -> list[Festival]:
    """Найти фестивали, в названии которых встречается подстрока query."""
    query_lower = query.lower()
    return [festival for festival in festivals if query_lower in festival.name.lower()]


def get_festival(festivals: list[Festival], festival_id: int) -> Festival:
    """Вернуть фестиваль по идентификатору.

    Вызывает KeyError, если фестиваль с таким id не найден.
    """
    for festival in festivals:
        if festival.id == festival_id:
            return festival
    raise KeyError(f"Фестиваль с id={festival_id} не найден")


def filter_festivals_by_min_attendees(
    festivals: list[Festival], min_attendees: int
) -> list[Festival]:
    """Отобрать фестивали с ожидаемым числом посетителей не меньше min_attendees."""
    return [festival for festival in festivals if festival.expected_attendees >= min_attendees]


def sort_festivals_by_date(festivals: list[Festival]) -> list[Festival]:
    """Вернуть фестивали, отсортированные по дате проведения."""
    return sorted(festivals, key=lambda festival: festival.date)
