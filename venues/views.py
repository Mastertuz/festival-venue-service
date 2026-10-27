from datetime import date

from django.shortcuts import get_object_or_404, render

from bookings.models import Booking
from venue_service.params import parse_iso_date, parse_non_negative_int
from venue_service.search import search_text
from venues.models import Venue

UPCOMING_BOOKINGS_LIMIT = 5


def venues(request):
    raw_capacity = request.GET.get("min_capacity", "")
    raw_query = request.GET.get("q", "")
    min_capacity, filter_error = parse_non_negative_int(raw_capacity)

    # Все площадки; порядок по названию задан в Meta модели Venue.
    venues_list = Venue.objects.all()

    # Поиск по части названия (регистр не учитывается).
    venues_list = search_text(venues_list, ["name"], raw_query)

    # Фильтр по вместимости; результат сортируется по вместимости, затем по названию.
    if min_capacity is not None:
        venues_list = venues_list.filter(capacity__gte=min_capacity).order_by("capacity", "name")

    context = {
        "venues": venues_list,
        "min_capacity": raw_capacity.strip(),
        "query": raw_query.strip(),
        "filter_error": filter_error,
    }

    return render(
        request,
        "venues/venue_list.html",
        context,
    )


def venue_detail(request, venue_id):
    # Площадка по первичному ключу; если её нет, get_object_or_404() вернёт ответ 404
    # (исключение Http404 обрабатывает handler404 проекта).
    venue = get_object_or_404(Venue, pk=venue_id)

    # Обратная связь по related_name: бронирования этой площадки вместе с фестивалями
    # (select_related), только активные и не в прошлом.
    upcoming_bookings = venue.bookings.select_related("festival").filter(
        is_cancelled=False,
        festival__date__gte=date.today(),
    )[:UPCOMING_BOOKINGS_LIMIT]

    context = {
        "venue": venue,
        "available": venue.is_available_on(date.today()),
        "upcoming_bookings": upcoming_bookings,
    }

    return render(
        request,
        "venues/venue_detail.html",
        context,
    )


def available(request):
    """Поиск площадок, свободных на выбранную дату (и подходящих по числу посетителей)."""
    raw_date = request.GET.get("date", "")
    raw_attendees = request.GET.get("attendees", "")
    search_date, date_error = parse_iso_date(raw_date)
    attendees, attendees_error = parse_non_negative_int(raw_attendees)

    searched = search_date is not None and not attendees_error
    venues_list = Venue.objects.none()
    if searched:
        # Идентификаторы площадок с активным бронированием на выбранную дату
        # (условие по полю связанной модели festival__date).
        booked_venue_ids = Booking.objects.filter(
            festival__date=search_date,
            is_cancelled=False,
        ).values_list("venue_id", flat=True)

        # Исключаем занятые площадки; оставшиеся отбираем по вместимости.
        venues_list = (
            Venue.objects.exclude(pk__in=booked_venue_ids)
            .filter(capacity__gte=attendees or 0)
            .order_by("name")
        )

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
