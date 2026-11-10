from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import Booking
from festivals.models import Festival, Organizer
from venue_service.search import search_text
from venues.models import Venue

from .forms import BookingFilterForm, BookingForm

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

# Часть сообщения триггеров базы данных (ПР10), по которой отличают конфликт бронирований.
CONFLICT_TEXT = "Площадка уже забронирована"

# Поля, по которым ищется текст из параметра q (в том числе поля связанных моделей).
SEARCH_FIELDS = ["festival__name", "venue__name", "festival__organizer__name"]


def bookings(request):
    # Форма проверяет GET-параметры. Без параметров она не связана с данными (is_bound == False),
    # и страница открывается со всеми бронированиями и сортировкой по умолчанию.
    form = BookingFilterForm(request.GET or None)
    form_valid = form.is_bound and form.is_valid()

    # Значения по умолчанию: пока форма не прошла проверку, ей не доверяют и не фильтруют.
    only_active = False
    selected_date = None
    selected_venue = None
    selected_organizer = None
    query = ""
    sort = DEFAULT_SORT
    descending = False
    error = None

    # cleaned_data доступен только после успешного is_valid(): значения уже преобразованы
    # (дата — в date, площадка и организатор — в объекты моделей).
    if form_valid:
        only_active = form.cleaned_data["active"]
        selected_date = form.cleaned_data["date"]
        selected_venue = form.cleaned_data["venue"]
        selected_organizer = form.cleaned_data["organizer"]
        query = form.cleaned_data["q"]
        sort = form.cleaned_data["sort"] or DEFAULT_SORT
        descending = form.cleaned_data["dir"] == "desc"
    elif form.is_bound:
        error = "Проверьте введённые значения фильтров."

    # Все бронирования; порядок по умолчанию (по дате фестиваля) задан в Meta модели.
    bookings_data = Booking.objects.all()

    # Фильтр по статусу: только активные бронирования (метод пользовательского QuerySet).
    if only_active:
        bookings_data = bookings_data.active()

    # Фильтр по дате: условие по полю связанной модели (дата проведения фестиваля).
    if selected_date:
        bookings_data = bookings_data.filter(festival__date=selected_date)

    # Фильтр по площадке (по внешнему ключу) и по организатору (через фестиваль).
    if selected_venue:
        bookings_data = bookings_data.filter(venue=selected_venue)

    if selected_organizer:
        bookings_data = bookings_data.filter(festival__organizer=selected_organizer)

    # Поиск по нескольким полям: фестиваль, площадка, организатор.
    bookings_data = search_text(bookings_data, SEARCH_FIELDS, query)

    # Сортировка по выбранному полю из заранее заданного соответствия (форма уже отклонила
    # значения не из списка); при равенстве значений порядок определяет идентификатор.
    # Префикс «-» меняет направление.
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
        "status",
    )

    # Пагинация применяется после фильтрации и сортировки. get_page() при некорректном номере
    # возвращает первую страницу, а при слишком большом — последнюю.
    paginator = Paginator(bookings_data, BOOKINGS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "bookings": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "form": form,
        "only_active": only_active,
        "query": query,
        "sort": sort,
        "descending": descending,
        "error": error,
    }

    return render(
        request,
        "bookings/booking_list.html",
        context,
    )


def save_booking_form(form):
    """Сохранить проверенную форму; вернуть True или добавить ошибку формы при конфликте.

    Booking.clean() уже проверил занятость площадки при is_valid(), но между проверкой и
    записью другой запрос мог занять ту же площадку на ту же дату. Тогда запись отклоняют
    триггеры базы данных (ПР10), а Django превращает отказ в IntegrityError. Пользователь
    получает ошибку формы, а не страницу 500.
    """
    try:
        # atomic() откатывает неудачную запись, не нарушая транзакцию запроса.
        with transaction.atomic():
            form.save()
    except IntegrityError as error:
        if CONFLICT_TEXT not in str(error):
            raise
        form.add_error(None, "Площадка уже забронирована на эту дату: есть активное бронирование.")
        return False
    return True


def booking_create(request):
    """Создание бронирования: GET показывает пустую форму, POST проверяет и сохраняет данные."""
    if request.method == "POST":
        # Форма связывается с данными запроса; данные не сохраняются до успешной проверки.
        form = BookingForm(request.POST)
        if form.is_valid() and save_booking_form(form):
            messages.success(request, "Бронирование создано.")
            # После успешного POST выполняется перенаправление (Post/Redirect/Get):
            # обновление страницы не отправит форму повторно.
            return redirect("bookings:list")
    else:
        # Начальное значение: ближайший фестиваль, который ещё не прошёл (если он есть).
        upcoming = Festival.objects.filter(date__gte=timezone.localdate()).first()
        form = BookingForm(initial={"festival": upcoming})

    return render(request, "bookings/booking_form.html", {"form": form})


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
    # Количество бронирований по статусам одним запросом: Count() с условием Q(status=...).
    status_counts = Booking.objects.aggregate(
        total_bookings=Count("id"),
        active_bookings=Count("id", filter=Q(status=Booking.Status.ACTIVE)),
        cancelled_bookings=Count("id", filter=Q(status=Booking.Status.CANCELLED)),
        completed_bookings=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
    )
    # Сводные показатели вместимости площадок.
    summary = Venue.objects.aggregate(
        venues_count=Count("id"),
        min_capacity=Min("capacity"),
        max_capacity=Max("capacity"),
        avg_capacity=Avg("capacity"),
        total_capacity=Sum("capacity"),
    )

    # Активные бронирования по площадкам. Запрос строится от модели Venue, поэтому площадки без
    # бронирований тоже попадают в результат (аналог LEFT JOIN); условие по статусу
    # применяется внутри Count(), а не к исходному набору площадок.
    venues_with_counts = Venue.objects.annotate(
        bookings_count=Count("bookings", filter=Q(bookings__status=Booking.Status.ACTIVE)),
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
        "active_bookings_count": status_counts["active_bookings"],
        "status_counts": status_counts,
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
