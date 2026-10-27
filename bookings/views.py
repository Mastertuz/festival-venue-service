from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, render

from bookings.models import Booking
from festivals.models import Organizer
from venues.models import Venue

# Площадка считается «часто бронируемой», если у неё больше стольких активных бронирований.
POPULAR_THRESHOLD = 2


def bookings(request):
    only_active = request.GET.get("active") == "1"

    # Все бронирования; порядок (по дате фестиваля, затем по идентификатору) задан в Meta модели.
    bookings_data = Booking.objects.all()

    # Только активные: условие по булеву полю модели.
    if only_active:
        bookings_data = bookings_data.filter(is_cancelled=False)

    # Поля связанных моделей через F(): названия фестиваля, площадки и организатора берутся
    # через внешние ключи без ручного JOIN; values() возвращает словари с нужными ключами.
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

    context = {
        "bookings": bookings_data,
        "only_active": only_active,
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
