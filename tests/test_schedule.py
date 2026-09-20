from datetime import date

import pytest

from models.festivals import add_festival
from models.organizers import add_organizer
from models.schedule import cancel_booking, create_booking, is_venue_available
from models.venues import add_venue


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
