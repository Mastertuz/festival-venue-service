"""Функции для работы с расписанием: привязкой фестиваля к площадке на дату."""

from datetime import date

from models.festivals import get_festival
from models.venues import get_venue


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
