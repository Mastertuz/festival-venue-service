from contextlib import closing
from datetime import date

from django.shortcuts import render

from db.database import get_connection

MAX_NUMBER = 1_000_000_000

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


FREE_VENUES_SQL = """
    SELECT
        venues.id,
        venues.name,
        venues.capacity
    FROM venues
    WHERE venues.capacity >= ?
      AND venues.id NOT IN (
          SELECT bookings.venue_id
          FROM bookings
          JOIN festivals
              ON bookings.festival_id = festivals.id
          WHERE festivals.date = ?
            AND bookings.is_cancelled = 0
      )
    ORDER BY venues.name;
"""


def parse_non_negative_int(value):
    """Разобрать целое неотрицательное число из параметра запроса.

    Возвращает пару (число или None, признак ошибки): пустое значение не считается ошибкой.
    """
    value = (value or "").strip()
    if not value:
        return None, False
    try:
        number = int(value)
    except ValueError:
        return None, True
    if not 0 <= number <= MAX_NUMBER:
        return None, True
    return number, False


def parse_iso_date(value):
    """Разобрать дату формата ГГГГ-ММ-ДД из параметра запроса: (date или None, признак ошибки)."""
    value = (value or "").strip()
    if not value:
        return None, False
    try:
        return date.fromisoformat(value), False
    except ValueError:
        return None, True


def venues(request):
    raw_value = request.GET.get("min_capacity", "")
    min_capacity, filter_error = parse_non_negative_int(raw_value)

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


def available(request):
    """Поиск площадок, свободных на выбранную дату (и подходящих по числу посетителей)."""
    raw_date = request.GET.get("date", "")
    raw_attendees = request.GET.get("attendees", "")
    search_date, date_error = parse_iso_date(raw_date)
    attendees, attendees_error = parse_non_negative_int(raw_attendees)

    searched = search_date is not None and not attendees_error
    venues_list = []
    if searched:
        with closing(get_connection()) as conn:
            venues_list = conn.execute(
                FREE_VENUES_SQL, [attendees or 0, search_date.isoformat()]
            ).fetchall()

    context = {
        "venues": venues_list,
        "searched": searched,
        "search_date": search_date,
        "raw_date": raw_date.strip(),
        "attendees": raw_attendees.strip(),
        "date_error": date_error,
        "attendees_error": attendees_error,
    }

    return render(
        request,
        "venues/venue_available.html",
        context,
    )
