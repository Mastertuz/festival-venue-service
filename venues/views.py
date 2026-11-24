from datetime import date

from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, UpdateView

from bookings.models import Booking
from venue_service.params import parse_iso_date, parse_non_negative_int
from venue_service.search import search_text
from venue_service.utils import DataMixin
from venues.models import Venue

from .forms import VenueForm

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


class VenueCreateView(DataMixin, SuccessMessageMixin, CreateView):
    """Добавление площадки: GET показывает пустую форму, POST проверяет данные и файл."""

    model = Venue
    form_class = VenueForm
    template_name = "venues/venue_form.html"
    title_page = "Добавление площадки"
    success_message = "Площадка добавлена."
    # success_url не задан: после сохранения CreateView перенаправляет на адрес, который
    # возвращает Venue.get_absolute_url() (страница новой площадки).

    # request.FILES в форму передаёт сам CreateView (get_form_kwargs()).


class VenueUpdateView(DataMixin, SuccessMessageMixin, UpdateView):
    """Редактирование площадки, в том числе замена или удаление изображения."""

    model = Venue
    form_class = VenueForm
    template_name = "venues/venue_form.html"
    context_object_name = "venue"
    # Площадка выбирается по slug (поле модели slug, параметр маршрута slug).
    slug_field = "slug"
    slug_url_kwarg = "slug"
    title_page = "Редактирование площадки"
    success_message = "Изменения сохранены."

    def get_object(self, queryset=None):
        venue = super().get_object(queryset)
        # Имя прежнего файла запоминается до проверки формы: ModelForm подставляет в объект
        # новое значение поля ещё при is_valid().
        self.old_image = venue.image.name
        return venue

    def form_valid(self, form):
        response = super().form_valid(form)
        # Django не удаляет заменённый файл сам: убираем его, чтобы не копить лишние файлы.
        if self.old_image and self.object.image.name != self.old_image:
            default_storage.delete(self.old_image)
        return response


def venue_redirect(request, venue_id):
    """Постоянное перенаправление со старого адреса /venues/<id>/ на /venues/<slug>/."""
    venue = get_object_or_404(Venue, pk=venue_id)
    return redirect(venue, permanent=True)


class VenueDetailView(DataMixin, DetailView):
    """Карточка площадки: объект выбирается по slug из адреса."""

    model = Venue
    template_name = "venues/venue_detail.html"
    context_object_name = "venue"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    title_page = "Площадка"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venue = self.object
        # Обратная связь по related_name: бронирования этой площадки вместе с фестивалями
        # (select_related), только активные и не в прошлом.
        context["upcoming_bookings"] = (
            venue.bookings.active()
            .select_related("festival")
            .filter(festival__date__gte=date.today())[:UPCOMING_BOOKINGS_LIMIT]
        )
        context["available"] = venue.is_available_on(date.today())
        # Заголовок страницы — название площадки (динамическое значение).
        return self.get_mixin_context(context, title=venue.name)


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
        # (менеджер: active() и for_date()).
        booked_venue_ids = (
            Booking.objects.active().for_date(search_date).values_list("venue_id", flat=True)
        )

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
