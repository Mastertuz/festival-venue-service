"""Функции для работы с расписанием: привязкой фестиваля к площадке на дату."""

from datetime import date

from models.festivals import Festival, get_festival
from models.venues import Venue, get_venue


class Booking:
    """Бронирование площадки под фестиваль (запись расписания).

    Композиция: Booking связывает объекты Festival и Venue, но не является
    их разновидностью — отношение "является" (наследование) здесь неуместно.
    """

    def __init__(self, booking_id: int, festival: Festival, venue: Venue) -> None:
        """Создать бронирование, связав фестиваль с площадкой."""
        self.id = booking_id
        self.festival = festival
        self.venue = venue
        self.is_cancelled = False

    def cancel(self) -> None:
        """Отменить бронирование, не удаляя его из коллекции."""
        self.is_cancelled = True

    @property
    def booking_date(self) -> date:
        """Дата бронирования — дата проведения связанного фестиваля."""
        return self.festival.date

    @property
    def status(self) -> str:
        """Текстовый статус бронирования (доступен как атрибут, без вызова)."""
        return "отменено" if self.is_cancelled else "активно"

    def __str__(self) -> str:
        """Вернуть удобное строковое представление бронирования."""
        return (
            f"{self.festival.name} → {self.venue.name}, "
            f"{self.booking_date.isoformat()} ({self.status})"
        )

    def to_data(self) -> dict:
        """Представить бронирование в виде словаря для сохранения в JSON."""
        return {
            "id": self.id,
            "festival_id": self.festival.id,
            "venue_id": self.venue.id,
            "is_cancelled": self.is_cancelled,
        }


def check_venue_suitability(capacity: int, attendees: int, is_available: bool) -> str:
    """Вернуть текстовый статус площадки (функция из ПР1, без изменений логики)."""
    if not is_available:
        return "Площадка недоступна на выбранную дату"
    elif attendees > capacity:
        return "Площадка не подходит: вместимость превышена"
    else:
        return "Площадка подходит для проведения фестиваля"


def is_venue_available(
    bookings: list[dict], festivals: dict[int, dict], venue_id: int, booking_date: date
) -> bool:
    """Проверить, свободна ли площадка на дату (дата берётся из фестиваля бронирования)."""
    for booking in bookings:
        booked_festival = festivals[booking["festival_id"]]
        is_same_date = booked_festival["date"] == booking_date.isoformat()
        if booking["venue_id"] == venue_id and is_same_date:
            return False
    return True


def create_booking(
    bookings: list[dict],
    festivals: dict[int, dict],
    venues: dict[int, dict],
    festival_id: int,
    venue_id: int,
) -> dict:
    """Привязать фестиваль к площадке (создать запись расписания).

    Вызывает ValueError, если площадка не подходит по вместимости
    или уже занята другим фестивалем на ту же дату.
    """
    festival = get_festival(festivals, festival_id)
    venue = get_venue(venues, venue_id)
    booking_date = date.fromisoformat(festival["date"])

    if not is_venue_available(bookings, festivals, venue_id, booking_date):
        raise ValueError("Площадка уже занята другим фестивалем на эту дату")
    if festival["expected_attendees"] > venue["capacity"]:
        raise ValueError("Ожидаемое число посетителей превышает вместимость площадки")

    booking_id = max((booking["id"] for booking in bookings), default=0) + 1
    booking = {"id": booking_id, "festival_id": festival_id, "venue_id": venue_id}
    bookings.append(booking)
    return booking


def cancel_booking(bookings: list[dict], booking_id: int) -> bool:
    """Отменить запись расписания по идентификатору.

    Возвращает True, если запись была найдена и удалена.
    """
    for index, booking in enumerate(bookings):
        if booking["id"] == booking_id:
            del bookings[index]
            return True
    return False
