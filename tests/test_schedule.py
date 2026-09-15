from datetime import date

from models.festivals import Festival
from models.organizers import Organizer
from models.schedule import (
    Booking,
    cancel_booking,
    check_venue_suitability,
    create_booking,
    is_venue_available,
)
from models.venues import Venue


def make_data() -> tuple[Festival, Venue]:
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    venue = Venue(1, "Городской парк", 5000)
    festival = Festival(1, "Фестиваль уличной музыки", date(2026, 9, 15), 4500, organizer)
    return festival, venue


def test_check_venue_suitability():
    suitable = check_venue_suitability(5000, 4500, True)
    over_capacity = check_venue_suitability(5000, 6000, True)
    unavailable = check_venue_suitability(5000, 4500, False)
    assert suitable == "Площадка подходит для проведения фестиваля"
    assert over_capacity == "Площадка не подходит: вместимость превышена"
    assert unavailable == "Площадка недоступна на выбранную дату"


def test_booking_creation():
    festival, venue = make_data()
    booking = Booking(1, festival, venue)
    assert booking.id == 1
    assert booking.festival is festival
    assert booking.venue is venue
    assert not booking.is_cancelled


def test_booking_status_property():
    festival, venue = make_data()
    booking = Booking(1, festival, venue)
    assert booking.status == "активно"
    booking.cancel()
    assert booking.status == "отменено"
    assert booking.is_cancelled


def test_is_venue_available_when_no_bookings():
    festival, venue = make_data()
    bookings: list[Booking] = []
    assert is_venue_available(bookings, venue, date(2026, 9, 15))


def test_create_booking_and_duplicate_forbidden():
    festival, venue = make_data()
    bookings: list[Booking] = []
    create_booking(bookings, festival, venue)
    assert not is_venue_available(bookings, venue, date(2026, 9, 15))


def test_create_booking_over_capacity_returns_none():
    festival, venue = make_data()
    small_venue = Venue(2, "Малый зал", 100)
    bookings: list[Booking] = []
    assert create_booking(bookings, festival, small_venue) is None
    assert bookings == []


def test_create_booking_duplicate_date_returns_none():
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    venue = Venue(1, "Городской парк", 5000)
    festival_1 = Festival(1, "Фестиваль уличной музыки", date(2026, 9, 15), 4500, organizer)
    festival_2 = Festival(2, "Другой фестиваль", date(2026, 9, 15), 1000, organizer)
    bookings: list[Booking] = []
    create_booking(bookings, festival_1, venue)
    assert create_booking(bookings, festival_2, venue) is None


def test_cancelled_booking_frees_the_venue():
    festival, venue = make_data()
    bookings: list[Booking] = []
    booking = create_booking(bookings, festival, venue)
    booking.cancel()
    assert is_venue_available(bookings, venue, date(2026, 9, 15))


def test_cancel_booking_by_id():
    festival, venue = make_data()
    bookings: list[Booking] = []
    booking = create_booking(bookings, festival, venue)
    assert cancel_booking(bookings, booking.id)
    assert booking.is_cancelled
    assert booking in bookings
    assert not cancel_booking(bookings, 99)
