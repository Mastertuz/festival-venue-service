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

ACTIVE_BOOKINGS_COUNT_SQL = """
    SELECT
        COUNT(*) AS bookings_count
    FROM bookings
    WHERE is_cancelled = 0;
"""

VENUES_SUMMARY_SQL = """
    SELECT
        COUNT(*) AS venues_count,
        MIN(capacity) AS min_capacity,
        MAX(capacity) AS max_capacity,
        ROUND(AVG(capacity), 1) AS avg_capacity,
        SUM(capacity) AS total_capacity
    FROM venues;
"""

BOOKINGS_BY_VENUE_SQL = """
    SELECT
        venues.name AS venue_name,
        COUNT(bookings.id) AS bookings_count
    FROM venues
    LEFT JOIN bookings
        ON venues.id = bookings.venue_id
       AND bookings.is_cancelled = 0
    GROUP BY venues.id, venues.name
    ORDER BY bookings_count DESC, venues.name;
"""

FESTIVALS_BY_ORGANIZER_SQL = """
    SELECT
        organizers.name AS organizer_name,
        COUNT(festivals.id) AS festivals_count,
        SUM(festivals.expected_attendees) AS total_attendees
    FROM organizers
    JOIN festivals
        ON festivals.organizer_id = organizers.id
    GROUP BY organizers.id, organizers.name
    ORDER BY total_attendees DESC;
"""

POPULAR_VENUES_SQL = """
    SELECT
        venues.name AS venue_name,
        COUNT(bookings.id) AS bookings_count
    FROM venues
    JOIN bookings
        ON venues.id = bookings.venue_id
    WHERE bookings.is_cancelled = 0
    GROUP BY venues.id, venues.name
    HAVING COUNT(bookings.id) > ?
    ORDER BY bookings_count DESC;
"""

# Площадка считается «часто бронируемой», если у неё больше стольких активных бронирований.
POPULAR_THRESHOLD = 2


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


def statistics(request):
    with closing(get_connection()) as conn:
        context = {
            "active_bookings_count": conn.execute(ACTIVE_BOOKINGS_COUNT_SQL).fetchone()[
                "bookings_count"
            ],
            "summary": conn.execute(VENUES_SUMMARY_SQL).fetchone(),
            "by_venue": conn.execute(BOOKINGS_BY_VENUE_SQL).fetchall(),
            "by_organizer": conn.execute(FESTIVALS_BY_ORGANIZER_SQL).fetchall(),
            "popular": conn.execute(POPULAR_VENUES_SQL, [POPULAR_THRESHOLD]).fetchall(),
            "popular_threshold": POPULAR_THRESHOLD,
        }

    return render(
        request,
        "bookings/statistics.html",
        context,
    )
