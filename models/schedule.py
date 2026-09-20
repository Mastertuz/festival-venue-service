"""Класс Booking (запись расписания) и функции для работы с коллекцией бронирований."""

from datetime import date
from typing import Optional

from .festivals import Festival
from .venues import Venue


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


def is_venue_available(bookings: list[Booking], venue: Venue, booking_date: date) -> bool:
    """Проверить, свободна ли площадка на дату среди активных (не отменённых) бронирований."""
    for booking in bookings:
        if booking.is_cancelled:
            continue
        if booking.venue.id == venue.id and booking.festival.date == booking_date:
            return False
    return True


def check_venue_suitability(
    venue: Venue, festival: Festival, bookings: list[Booking]
) -> str:
    """Вернуть текстовый статус площадки для фестиваля.

    Функция из ПР1: порядок проверок и тексты сообщений сохранены, но
    доступность теперь определяется по состоянию объектов Booking
    (отменённые бронирования площадку не блокируют), а вместимость —
    методом объекта Venue.
    """
    if not is_venue_available(bookings, venue, festival.date):
        return "Площадка недоступна на выбранную дату"
    elif not venue.is_suitable_for(festival.expected_attendees):
        return "Площадка не подходит: вместимость превышена"
    else:
        return "Площадка подходит для проведения фестиваля"


def create_booking(bookings: list[Booking], festival: Festival, venue: Venue) -> Optional[Booking]:
    """Создать бронирование, связав фестиваль с площадкой.

    Возвращает None, если площадка не подходит по вместимости или уже
    занята другим активным бронированием на дату фестиваля.
    """
    if not venue.is_suitable_for(festival.expected_attendees):
        return None
    if not is_venue_available(bookings, venue, festival.date):
        return None

    booking_id = max((booking.id for booking in bookings), default=0) + 1
    booking = Booking(booking_id, festival, venue)
    bookings.append(booking)
    return booking


def cancel_booking(bookings: list[Booking], booking_id: int) -> bool:
    """Отменить бронирование по идентификатору, вызвав его метод cancel().

    Возвращает True, если бронирование было найдено.
    """
    for booking in bookings:
        if booking.id == booking_id:
            booking.cancel()
            return True
    return False


def show_bookings(bookings: list[Booking]) -> None:
    """Вывести информацию об объектах Booking."""
    if not bookings:
        print("Расписание пусто.")
        return
    for booking in bookings:
        print(f"{booking.id}. {booking}")
