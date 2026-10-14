from contextlib import closing
from datetime import date

from django.shortcuts import render

from db.database import get_connection

MAX_CAPACITY_FILTER = 1_000_000_000

VENUES_SQL = """
    SELECT
        id,
        name,
        capacity
    FROM venues
    ORDER BY name;
"""

VENUES_BY_CAPACITY_SQL = """
    SELECT
        id,
        name,
        capacity
    FROM venues
    WHERE capacity >= ?
    ORDER BY capacity;
"""

VENUE_BY_ID_SQL = """
    SELECT
        id,
        name,
        capacity
    FROM venues
    WHERE id = ?;
"""

VENUE_BUSY_COUNT_SQL = """
    SELECT
        COUNT(*) AS busy_count
    FROM bookings
    JOIN festivals
        ON bookings.festival_id = festivals.id
    WHERE bookings.venue_id = ?
      AND festivals.date = ?
      AND bookings.is_cancelled = 0;
"""


def parse_min_capacity(value):
    """Вернуть вместимость из параметра запроса; None — если параметр пуст или некорректен."""
    value = (value or "").strip()
    if not value:
        return None, False
    try:
        number = int(value)
    except ValueError:
        return None, True
    if not 0 <= number <= MAX_CAPACITY_FILTER:
        return None, True
    return number, False


def venues(request):
    raw_value = request.GET.get("min_capacity", "")
    min_capacity, filter_error = parse_min_capacity(raw_value)

    with closing(get_connection()) as conn:
        if min_capacity is None:
            venues_list = conn.execute(VENUES_SQL).fetchall()
        else:
            venues_list = conn.execute(VENUES_BY_CAPACITY_SQL, [min_capacity]).fetchall()

    context = {
        "venues": venues_list,
        "min_capacity": raw_value.strip(),
        "filter_error": filter_error,
    }

    return render(
        request,
        "venues/venue_list.html",
        context,
    )


def venue_detail(request, venue_id):
    available = None

    with closing(get_connection()) as conn:
        venue = conn.execute(VENUE_BY_ID_SQL, [venue_id]).fetchone()
        if venue is not None:
            busy = conn.execute(
                VENUE_BUSY_COUNT_SQL, [venue_id, date.today().isoformat()]
            ).fetchone()
            available = busy["busy_count"] == 0

    context = {
        "venue": venue,
        "available": available,
    }

    return render(
        request,
        "venues/venue_detail.html",
        context,
        status=404 if venue is None else 200,
    )
