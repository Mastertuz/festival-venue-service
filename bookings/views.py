from contextlib import closing

from django.shortcuts import render

from db.database import get_connection, row_with_dates

BOOKINGS_SQL = """
    SELECT
        bookings.id,
        festivals.name AS festival_name,
        festivals.date AS booking_date,
        venues.name AS venue_name,
        venues.capacity,
        organizers.name AS organizer_name,
        bookings.is_cancelled
    FROM bookings
    JOIN festivals
        ON bookings.festival_id = festivals.id
    JOIN venues
        ON bookings.venue_id = venues.id
    JOIN organizers
        ON festivals.organizer_id = organizers.id
    ORDER BY festivals.date, bookings.id;
"""

ACTIVE_BOOKINGS_SQL = """
    SELECT
        bookings.id,
        festivals.name AS festival_name,
        festivals.date AS booking_date,
        venues.name AS venue_name,
        venues.capacity,
        organizers.name AS organizer_name,
        bookings.is_cancelled
    FROM bookings
    JOIN festivals
        ON bookings.festival_id = festivals.id
    JOIN venues
        ON bookings.venue_id = venues.id
    JOIN organizers
        ON festivals.organizer_id = organizers.id
    WHERE bookings.is_cancelled = 0
    ORDER BY festivals.date, bookings.id;
"""

BOOKING_BY_ID_SQL = """
    SELECT
        bookings.id,
        festivals.name AS festival_name,
        festivals.date AS booking_date,
        venues.id AS venue_id,
        venues.name AS venue_name,
        organizers.name AS organizer_name,
        bookings.is_cancelled
    FROM bookings
    JOIN festivals
        ON bookings.festival_id = festivals.id
    JOIN venues
        ON bookings.venue_id = venues.id
    JOIN organizers
        ON festivals.organizer_id = organizers.id
    WHERE bookings.id = ?;
"""


def bookings(request):
    only_active = request.GET.get("active") == "1"

    with closing(get_connection()) as conn:
        rows = conn.execute(ACTIVE_BOOKINGS_SQL if only_active else BOOKINGS_SQL).fetchall()

    context = {
        "bookings": [row_with_dates(row, "booking_date") for row in rows],
        "only_active": only_active,
    }

    return render(
        request,
        "bookings/booking_list.html",
        context,
    )


def booking_detail(request, booking_id):
    with closing(get_connection()) as conn:
        row = conn.execute(BOOKING_BY_ID_SQL, [booking_id]).fetchone()

    booking = row_with_dates(row, "booking_date") if row is not None else None

    context = {
        "booking": booking,
    }

    return render(
        request,
        "bookings/booking_detail.html",
        context,
        status=404 if booking is None else 200,
    )
