from datetime import date

from models.festivals import Festival
from models.organizers import Organizer
from models.schedule import (
    Booking,
    cancel_booking,
    check_venue_suitability,
    create_booking,
    is_venue_available,
    show_bookings,
)
from models.venues import Venue


def make_data() -> tuple[Festival, Venue]:
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    venue = Venue(1, "Городской парк", 5000)
    festival = Festival(1, "Фестиваль уличной музыки", date(2026, 9, 15), 4500, organizer)
    return festival, venue


def test_booking_creation():
    festival, venue = make_data()
    booking = Booking(1, festival, venue)
    assert booking.id == 1
    assert booking.festival is festival
    assert booking.venue is venue
    assert not booking.is_cancelled


def test_booking_date_comes_from_festival():
    festival, venue = make_data()
    booking = Booking(1, festival, venue)
    assert booking.booking_date == date(2026, 9, 15)


def test_booking_status_property():
    festival, venue = make_data()
    booking = Booking(1, festival, venue)
    assert booking.status == "активно"
    booking.cancel()
    assert booking.status == "отменено"
    assert booking.is_cancelled


def test_booking_str_reflects_state():
    festival, venue = make_data()
    booking = Booking(1, festival, venue)
    assert str(booking) == "Фестиваль уличной музыки → Городской парк, 2026-09-15 (активно)"
    booking.cancel()
    assert str(booking).endswith("(отменено)")


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
    assert len(bookings) == 1


def test_cancelled_booking_frees_the_venue():
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    venue = Venue(1, "Городской парк", 5000)
    festival_1 = Festival(1, "Фестиваль уличной музыки", date(2026, 9, 15), 4500, organizer)
    festival_2 = Festival(2, "Другой фестиваль", date(2026, 9, 15), 1000, organizer)
    bookings: list[Booking] = []
    first = create_booking(bookings, festival_1, venue)
    assert create_booking(bookings, festival_2, venue) is None

    first.cancel()

    assert is_venue_available(bookings, venue, date(2026, 9, 15))
    second = create_booking(bookings, festival_2, venue)
    assert second is not None
    assert len(bookings) == 2
    assert first in bookings


def test_cancel_booking_by_id():
    festival, venue = make_data()
    bookings: list[Booking] = []
    booking = create_booking(bookings, festival, venue)
    assert cancel_booking(bookings, booking.id)
    assert booking.is_cancelled
    assert booking in bookings
    assert not cancel_booking(bookings, 99)


def test_check_venue_suitability_suitable():
    festival, venue = make_data()
    result = check_venue_suitability(venue, festival, [])
    assert result == "Площадка подходит для проведения фестиваля"


def test_check_venue_suitability_over_capacity():
    festival, _ = make_data()
    small_venue = Venue(2, "Малый зал", 100)
    result = check_venue_suitability(small_venue, festival, [])
    assert result == "Площадка не подходит: вместимость превышена"


def test_check_venue_suitability_unavailable_and_freed_after_cancel():
    festival, venue = make_data()
    bookings: list[Booking] = []
    booking = create_booking(bookings, festival, venue)
    unavailable = check_venue_suitability(venue, festival, bookings)
    assert unavailable == "Площадка недоступна на выбранную дату"
    booking.cancel()
    freed = check_venue_suitability(venue, festival, bookings)
    assert freed == "Площадка подходит для проведения фестиваля"


def test_show_bookings(capsys):
    festival, venue = make_data()
    bookings: list[Booking] = []
    show_bookings(bookings)
    assert "пусто" in capsys.readouterr().out
    create_booking(bookings, festival, venue)
    show_bookings(bookings)
    assert "Фестиваль уличной музыки → Городской парк" in capsys.readouterr().out
