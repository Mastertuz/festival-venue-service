"""Функции для работы с расписанием бронирований площадок под фестивали."""

from datetime import date

from venues import get_venue


def check_venue_suitability(capacity: int, attendees: int, is_available: bool) -> str:
    """Вернуть текстовый статус площадки (функция из ПР1, без изменений логики)."""
    if not is_available:
        return "Площадка недоступна на выбранную дату"
    elif attendees > capacity:
        return "Площадка не подходит: вместимость превышена"
    else:
        return "Площадка подходит для проведения фестиваля"


def is_venue_available(bookings: list[dict], venue_id: int, booking_date: date) -> bool:
    """Проверить, свободна ли площадка на указанную дату."""
    for booking in bookings:
        if booking["venue_id"] == venue_id and booking["booking_date"] == booking_date.isoformat():
            return False
    return True


def create_booking(
    bookings: list[dict],
    venues: dict[int, dict],
    venue_id: int,
    festival_name: str,
    organizer_name: str,
    expected_attendees: int,
    booking_date: date,
) -> dict:
    """Создать бронирование площадки под фестиваль.

    Вызывает ValueError, если площадка не подходит по вместимости
    или уже занята на выбранную дату.
    """
    venue = get_venue(venues, venue_id)

    if not is_venue_available(bookings, venue_id, booking_date):
        raise ValueError("Площадка уже забронирована на эту дату")
    if expected_attendees > venue["capacity"]:
        raise ValueError("Ожидаемое число посетителей превышает вместимость площадки")

    booking_id = max((booking["id"] for booking in bookings), default=0) + 1
    booking = {
        "id": booking_id,
        "venue_id": venue_id,
        "festival_name": festival_name,
        "organizer_name": organizer_name,
        "expected_attendees": expected_attendees,
        "booking_date": booking_date.isoformat(),
    }
    bookings.append(booking)
    return booking


def cancel_booking(bookings: list[dict], booking_id: int) -> bool:
    """Отменить бронирование по идентификатору.

    Возвращает True, если бронирование было найдено и удалено.
    """
    for index, booking in enumerate(bookings):
        if booking["id"] == booking_id:
            del bookings[index]
            return True
    return False
