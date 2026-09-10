from datetime import date

import pytest

from schedule import cancel_booking, create_booking, is_venue_available
from venues import add_venue


def make_venues():
    venues = {}
    add_venue(venues, "Городской парк", 5000)
    return venues


def test_is_venue_available_when_no_bookings():
    bookings = []
    assert is_venue_available(bookings, 1, date(2026, 9, 15))


def test_create_booking_and_duplicate_forbidden():
    venues = make_venues()
    bookings = []
    create_booking(
        bookings, venues, 1, "Фестиваль уличной музыки",
        "АНО «Арт-Ивент»", 4500, date(2026, 9, 15),
    )
    assert not is_venue_available(bookings, 1, date(2026, 9, 15))


def test_create_booking_over_capacity_raises_error():
    venues = make_venues()
    bookings = []
    with pytest.raises(ValueError):
        create_booking(
            bookings, venues, 1, "Слишком большой фестиваль",
            "Организатор", 9000, date(2026, 9, 15),
        )


def test_cancel_booking():
    venues = make_venues()
    bookings = []
    booking = create_booking(
        bookings, venues, 1, "Фестиваль уличной музыки",
        "АНО «Арт-Ивент»", 4500, date(2026, 9, 15),
    )
    assert cancel_booking(bookings, booking["id"])
    assert bookings == []
    assert not cancel_booking(bookings, booking["id"])
