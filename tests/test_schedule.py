from datetime import date

import pytest

from models.festivals import Festival, add_festival
from models.organizers import Organizer, add_organizer
from models.schedule import Booking, cancel_booking, create_booking, is_venue_available
from models.venues import Venue, add_venue


def make_data():
    organizers = {}
    add_organizer(organizers, "АНО «Арт-Ивент»")
    venues = {}
    add_venue(venues, "Городской парк", 5000)
    festivals = {}
    add_festival(
        festivals, organizers, "Фестиваль уличной музыки", date(2026, 9, 15), 4500, 1,
    )
    return organizers, venues, festivals


def test_is_venue_available_when_no_bookings():
    _, venues, festivals = make_data()
    bookings = []
    assert is_venue_available(bookings, festivals, 1, date(2026, 9, 15))


def test_create_booking_and_duplicate_forbidden():
    _, venues, festivals = make_data()
    bookings = []
    create_booking(bookings, festivals, venues, 1, 1)
    assert not is_venue_available(bookings, festivals, 1, date(2026, 9, 15))


def test_create_booking_over_capacity_raises_error():
    organizers, venues, festivals = make_data()
    add_venue(venues, "Малый зал", 100)
    bookings = []
    with pytest.raises(ValueError):
        create_booking(bookings, festivals, venues, 1, 2)


def test_create_booking_duplicate_date_raises_error():
    organizers, venues, festivals = make_data()
    add_festival(
        festivals, organizers, "Другой фестиваль", date(2026, 9, 15), 1000, 1,
    )
    bookings = []
    create_booking(bookings, festivals, venues, 1, 1)
    with pytest.raises(ValueError):
        create_booking(bookings, festivals, venues, 2, 1)


def test_cancel_booking():
    _, venues, festivals = make_data()
    bookings = []
    booking = create_booking(bookings, festivals, venues, 1, 1)
    assert cancel_booking(bookings, booking["id"])
    assert bookings == []
    assert not cancel_booking(bookings, booking["id"])


def make_object_data() -> tuple[Festival, Venue]:
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    venue = Venue(1, "Городской парк", 5000)
    festival = Festival(1, "Фестиваль уличной музыки", date(2026, 9, 15), 4500, organizer)
    return festival, venue


def test_booking_creation():
    festival, venue = make_object_data()
    booking = Booking(1, festival, venue)
    assert booking.id == 1
    assert booking.festival is festival
    assert booking.venue is venue
    assert not booking.is_cancelled


def test_booking_date_comes_from_festival():
    festival, venue = make_object_data()
    booking = Booking(1, festival, venue)
    assert booking.booking_date == date(2026, 9, 15)


def test_booking_status_property():
    festival, venue = make_object_data()
    booking = Booking(1, festival, venue)
    assert booking.status == "активно"
    booking.cancel()
    assert booking.status == "отменено"
    assert booking.is_cancelled


def test_booking_str_reflects_state():
    festival, venue = make_object_data()
    booking = Booking(1, festival, venue)
    assert str(booking) == "Фестиваль уличной музыки → Городской парк, 2026-09-15 (активно)"
    booking.cancel()
    assert str(booking).endswith("(отменено)")
