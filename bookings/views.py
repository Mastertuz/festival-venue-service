from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, render

from bookings.models import Booking
from festivals.models import Organizer
from venue_service.params import parse_iso_date, parse_non_negative_int
from venue_service.search import search_text
from venues.models import Venue

# Площадка считается «часто бронируемой», если у неё больше стольких активных бронирований.
POPULAR_THRESHOLD = 2

# Количество бронирований на одной странице списка.
BOOKINGS_PER_PAGE = 5

# Допустимые значения параметра sort и соответствующие им поля модели. Произвольное значение
# из URL в order_by() не передаётся: неизвестный параметр заменяется сортировкой по дате.
SORT_FIELDS = {
    "date": "festival__date",
    "venue": "venue__name",
    "festival": "festival__name",
    "organizer": "festival__organizer__name",
}
DEFAULT_SORT = "date"

# Поля, по которым ищется текст из параметра q (в том числе поля связанных моделей).
SEARCH_FIELDS = ["festival__name", "venue__name", "festival__organizer__name"]


def bookings(request):
    only_active = request.GET.get("active") == "1"
    raw_date = request.GET.get("date", "").strip()
    raw_venue = request.GET.get("venue", "").strip()
    raw_organizer = request.GET.get("organizer", "").strip()
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", DEFAULT_SORT)
    descending = request.GET.get("dir") == "desc"
    errors = []

    # Все бронирования; порядок по умолчанию (по дате фестиваля) задан в Meta модели.
    bookings_data = Booking.objects.all()

    # Фильтр по статусу: только активные бронирования.
    if only_active:
        bookings_data = bookings_data.filter(is_cancelled=False)

    # Фильтр по дате: условие по полю связанной модели (дата проведения фестиваля).
    selected_date, date_error = parse_iso_date(raw_date)
    if date_error:
        errors.append("Укажите корректную дату.")
    elif selected_date is not None:
        bookings_data = bookings_data.filter(festival__date=selected_date)

    # Фильтр по площадке (по внешнему ключу) и по организатору (через фестиваль).
    venue_id, venue_error = parse_non_negative_int(raw_venue)
    if venue_error:
        errors.append("Выберите площадку из списка.")
    elif venue_id is not None:
        bookings_data = bookings_data.filter(venue_id=venue_id)

    organizer_id, organizer_error = parse_non_negative_int(raw_organizer)
    if organizer_error:
        errors.append("Выберите организатора из списка.")
    elif organizer_id is not None:
        bookings_data = bookings_data.filter(festival__organizer_id=organizer_id)

    # Поиск по нескольким полям: фестиваль, площадка, организатор.
    bookings_data = search_text(bookings_data, SEARCH_FIELDS, query)

    # Сортировка по выбранному полю из заранее заданного соответствия; при равенстве значений
    # порядок определяет идентификатор. Префикс «-» меняет направление.
    if sort not in SORT_FIELDS:
        sort = DEFAULT_SORT
    sort_fields = [SORT_FIELDS[sort], "pk"]
    if descending:
        sort_fields = [f"-{field}" for field in sort_fields]
    bookings_data = bookings_data.order_by(*sort_fields)

    # Поля связанных моделей через F(): названия берутся через внешние ключи без ручного JOIN;
    # values() возвращает словари с нужными ключами.
    bookings_data = bookings_data.annotate(
        festival_name=F("festival__name"),
        booking_date=F("festival__date"),
        venue_name=F("venue__name"),
        capacity=F("venue__capacity"),
        organizer_name=F("festival__organizer__name"),
    ).values(
        "id",
        "festival_name",
        "booking_date",
        "venue_name",
        "capacity",
        "organizer_name",
        "is_cancelled",
    )

    # Пагинация применяется после фильтрации и сортировки. get_page() при некорректном номере
    # возвращает первую страницу, а при слишком большом — последнюю.
    paginator = Paginator(bookings_data, BOOKINGS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "bookings": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "only_active": only_active,
        "raw_date": raw_date,
        "selected_venue": raw_venue,
        "selected_organizer": raw_organizer,
        "query": query,
        "sort": sort,
        "descending": descending,
        "venues": Venue.objects.order_by("name"),
        "organizers": Organizer.objects.order_by("name"),
        "errors": errors,
    }

    return render(
        request,
        "bookings/booking_list.html",
        context,
    )


def booking_detail(request, booking_id):
    # Бронирование вместе с фестивалем, организатором и площадкой одним запросом
    # (select_related); при отсутствии записи get_object_or_404() вернёт ответ 404.
    booking = get_object_or_404(
        Booking.objects.select_related("festival__organizer", "venue"),
        pk=booking_id,
    )

    context = {
        "booking": booking,
    }

    return render(
        request,
        "bookings/booking_detail.html",
        context,
    )


def statistics(request):
    # Количество активных бронирований и сводные показатели вместимости площадок.
    active_bookings_count = Booking.objects.filter(is_cancelled=False).count()
    summary = Venue.objects.aggregate(
        venues_count=Count("id"),
        min_capacity=Min("capacity"),
        max_capacity=Max("capacity"),
        avg_capacity=Avg("capacity"),
        total_capacity=Sum("capacity"),
    )

    # Активные бронирования по площадкам. Запрос строится от модели Venue, поэтому площадки без
    # бронирований тоже попадают в результат (аналог LEFT JOIN); условие is_cancelled=False
    # применяется внутри Count(), а не к исходному набору площадок.
    venues_with_counts = Venue.objects.annotate(
        bookings_count=Count("bookings", filter=Q(bookings__is_cancelled=False)),
    )
    by_venue = (
        venues_with_counts.annotate(venue_name=F("name"))
        .values("venue_name", "bookings_count")
        .order_by("-bookings_count", "venue_name")
    )

    # Фестивали и ожидаемые посетители по организаторам (группировка annotate + Count/Sum);
    # организаторы без фестивалей в статистику не попадают.
    by_organizer = (
        Organizer.objects.annotate(
            festivals_count=Count("festivals"),
            total_attendees=Sum("festivals__expected_attendees"),
            organizer_name=F("name"),
        )
        .filter(festivals_count__gt=0)
        .values("organizer_name", "festivals_count", "total_attendees")
        .order_by("-total_attendees")
    )

    # Условие по агрегату после группировки (в SQL это HAVING).
    popular = (
        venues_with_counts.filter(bookings_count__gt=POPULAR_THRESHOLD)
        .annotate(venue_name=F("name"))
        .values("venue_name", "bookings_count")
        .order_by("-bookings_count", "venue_name")
    )

    context = {
        "active_bookings_count": active_bookings_count,
        "summary": summary,
        "by_venue": by_venue,
        "by_organizer": by_organizer,
        "popular": popular,
        "popular_threshold": POPULAR_THRESHOLD,
    }

    return render(
        request,
        "bookings/statistics.html",
        context,
    )
