from contextlib import closing
from datetime import date

from django.shortcuts import render

from db.database import get_connection, row_with_dates

ACTIVE_BOOKINGS_COUNT_SQL = """
    SELECT
        COUNT(*) AS bookings_count
    FROM bookings
    WHERE is_cancelled = 0;
"""

NEXT_FESTIVALS_SQL = """
    SELECT
        festivals.id,
        festivals.name,
        festivals.date,
        organizers.name AS organizer_name
    FROM festivals
    JOIN organizers
        ON festivals.organizer_id = organizers.id
    WHERE festivals.date >= ?
    ORDER BY festivals.date
    LIMIT 3;
"""


def index(request):
    with closing(get_connection()) as conn:
        count_row = conn.execute(ACTIVE_BOOKINGS_COUNT_SQL).fetchone()
        festival_rows = conn.execute(NEXT_FESTIVALS_SQL, [date.today().isoformat()]).fetchall()

    context = {
        "active_bookings_count": count_row["bookings_count"],
        "next_festivals": [row_with_dates(row, "date") for row in festival_rows],
    }

    return render(request, "homepage/index.html", context)


def page_not_found(request, exception):
    """Обработчик 404: страница проекта вместо служебной страницы Django."""
    return render(request, "homepage/404.html", status=404)
