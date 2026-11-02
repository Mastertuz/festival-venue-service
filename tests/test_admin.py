"""ПР10: административная панель Django — регистрация, настройки ModelAdmin, действия."""

from datetime import date, timedelta

import pytest
from django.apps import apps
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext

from bookings.admin import BookingAdmin
from bookings.models import Booking
from festivals.admin import FestivalAdmin, OrganizerAdmin
from festivals.models import Festival, Organizer
from venues.admin import VenueAdmin
from venues.models import Venue

pytestmark = pytest.mark.django_db

TODAY = date.today()


def squash(response):
    return " ".join(response.content.decode().split())


@pytest.fixture
def many_bookings(orm_data):
    """К данным orm_data добавляются ещё шесть бронирований на разные даты и площадки."""
    for index in range(6):
        festival = Festival.objects.create(
            name=f"Дополнительный {index}",
            date=TODAY + timedelta(days=index + 1),
            expected_attendees=10,
            organizer=orm_data["organizer"],
        )
        venue = orm_data["park"] if index % 2 else orm_data["arena"]
        Booking.objects.create(festival=festival, venue=venue)
    return orm_data


# --- Регистрация моделей ---


@pytest.mark.parametrize(
    ("model", "admin_class"),
    [
        (Venue, VenueAdmin),
        (Organizer, OrganizerAdmin),
        (Festival, FestivalAdmin),
        (Booking, BookingAdmin),
    ],
)
def test_models_are_registered_once_with_own_model_admin(model, admin_class):
    assert type(admin.site._registry[model]) is admin_class


# --- Настройки ModelAdmin ---


def test_venue_admin_settings():
    venue_admin = admin.site._registry[Venue]
    assert venue_admin.list_display[:3] == ("id", "name", "capacity")
    assert "is_large" in venue_admin.list_display
    assert venue_admin.list_display_links == ("name",)
    assert venue_admin.list_editable == ("capacity",)
    assert venue_admin.search_fields == ("name",)
    assert venue_admin.ordering == ("name",)
    assert venue_admin.list_per_page == 20
    assert set(venue_admin.readonly_fields) == {"id", "slug", "is_large"}
    assert venue_admin.view_on_site is True
    assert venue_admin.inlines


def test_booking_admin_settings():
    booking_admin = admin.site._registry[Booking]
    assert (
        "status" in booking_admin.list_display and "is_cancelled" not in booking_admin.list_display
    )
    assert booking_admin.search_fields == (
        "festival__name",
        "venue__name",
        "festival__organizer__name",
    )
    assert "status" in booking_admin.list_filter and "festival__date" in booking_admin.list_filter
    assert booking_admin.list_select_related == ("festival", "venue")
    assert booking_admin.date_hierarchy == "festival__date"
    assert set(booking_admin.actions) == {
        "cancel_bookings",
        "complete_bookings",
        "restore_bookings",
    }


def test_admin_configuration_has_no_system_check_errors():
    from django.core import checks

    errors = [
        message
        for message in checks.run_checks(include_deployment_checks=False)
        if message.level >= checks.ERROR
    ]
    assert errors == []


# --- Локализация ---


def test_app_names_are_translated():
    names = {config.label: config.verbose_name for config in apps.get_app_configs()}
    assert names["venues"] == "Площадки"
    assert names["festivals"] == "Организаторы и фестивали"
    assert names["bookings"] == "Бронирования"
    assert names["homepage"] == "Главная страница"


def test_model_and_field_names_are_translated():
    assert Venue._meta.verbose_name_plural == "Площадки"
    assert Booking._meta.verbose_name == "Бронирование"
    assert Venue._meta.get_field("capacity").verbose_name == "Вместимость"
    assert Venue._meta.get_field("is_large").verbose_name == "Большая площадка"
    assert Booking._meta.get_field("status").verbose_name == "Статус бронирования"
    assert "Максимальное число посетителей" in Venue._meta.get_field("capacity").help_text


def test_admin_index_is_in_russian_and_shows_translated_apps(admin_client, orm_data):
    html = squash(admin_client.get("/admin/"))
    assert 'lang="ru-ru"' in html
    for text in ("Площадки", "Организаторы и фестивали", "Бронирования", "Фестивали"):
        assert text in html


def test_admin_requires_login(client):
    response = client.get("/admin/venues/venue/")
    assert response.status_code == 302 and "/admin/login/" in response["Location"]


# --- Списки и поиск ---


@pytest.mark.parametrize(
    "url",
    [
        "/admin/venues/venue/",
        "/admin/festivals/organizer/",
        "/admin/festivals/festival/",
        "/admin/bookings/booking/",
    ],
)
def test_changelists_open(admin_client, orm_data, url):
    assert admin_client.get(url).status_code == 200


def test_venue_changelist_shows_generated_field_link_and_active_count(admin_client, orm_data):
    html = squash(admin_client.get("/admin/venues/venue/"))
    assert "Активных бронирований" in html and "Страница на сайте" in html
    assert orm_data["park"].get_absolute_url() in html
    assert 'name="form-0-capacity"' in html  # вместимость редактируется в списке


def test_venue_search_by_name(admin_client, orm_data):
    response = admin_client.get("/admin/venues/venue/", {"q": "Городской"})
    assert [obj.pk for obj in response.context["cl"].result_list] == [orm_data["park"].pk]


def test_venue_filter_by_generated_field(admin_client, orm_data):
    response = admin_client.get("/admin/venues/venue/", {"is_large__exact": "1"})
    assert [obj.pk for obj in response.context["cl"].result_list] == [orm_data["park"].pk]


def test_venue_active_bookings_column_counts_only_active(admin_client, orm_data):
    response = admin_client.get("/admin/venues/venue/")
    counts = {obj.name: obj.active_bookings for obj in response.context["cl"].result_list}
    assert counts == {"Городской парк": 1, "Арена <b>": 0}


def test_venue_capacity_is_editable_in_the_list(admin_client, orm_data):
    park, arena = orm_data["park"], orm_data["arena"]
    # Строки списка идут по названию: «Арена <b>», затем «Городской парк».
    data = {
        "form-TOTAL_FORMS": "2",
        "form-INITIAL_FORMS": "2",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
        "form-0-id": str(arena.pk),
        "form-0-capacity": "2600",
        "form-1-id": str(park.pk),
        "form-1-capacity": "5000",
        "_save": "Сохранить",
    }
    response = admin_client.post("/admin/venues/venue/", data, follow=True)
    assert response.status_code == 200
    arena.refresh_from_db()
    assert arena.capacity == 2600


def test_booking_search_by_related_venue_festival_and_organizer(admin_client, orm_data):
    def found(query):
        response = admin_client.get("/admin/bookings/booking/", {"q": query})
        return {obj.pk for obj in response.context["cl"].result_list}

    assert found("Городской") == {orm_data["active"].pk}  # по названию площадки
    assert found("Арена") == {orm_data["cancelled"].pk}
    assert found("уличной") == {orm_data["active"].pk, orm_data["cancelled"].pk}  # по фестивалю
    assert found("Арт-Ивент") == {
        orm_data["active"].pk,
        orm_data["cancelled"].pk,
    }  # по организатору
    assert found("нет такого") == set()


def test_booking_filter_by_status(admin_client, orm_data):
    def found(status):
        response = admin_client.get("/admin/bookings/booking/", {"status__exact": status})
        return {obj.pk for obj in response.context["cl"].result_list}

    assert found("active") == {orm_data["active"].pk}
    assert found("cancelled") == {orm_data["cancelled"].pk}
    assert found("completed") == set()


def test_booking_changelist_shows_related_columns(admin_client, orm_data):
    html = squash(admin_client.get("/admin/bookings/booking/"))
    assert "Вместимость площадки" in html and "Дата фестиваля" in html
    assert "Городской парк" in html and "5000" in html
    assert "Отменено" in html


def test_booking_changelist_query_count_does_not_depend_on_row_count(admin_client, orm_data):
    with CaptureQueriesContext(connection) as small:
        admin_client.get("/admin/bookings/booking/")
    festival = orm_data["festival"]
    for index in range(6):
        extra = Venue.objects.create(name=f"Площадка {index}", capacity=100 + index)
        Booking.objects.create(festival=festival, venue=extra, status=Booking.Status.COMPLETED)
    with CaptureQueriesContext(connection) as large:
        admin_client.get("/admin/bookings/booking/")
    assert len(large) == len(small)


def test_list_select_related_prevents_n_plus_one_for_method_columns(
    admin_client, many_bookings, monkeypatch
):
    """Столбцы-методы обращаются к festival и venue: без list_select_related — N+1 запросов."""
    booking_admin = admin.site._registry[Booking]
    monkeypatch.setattr(booking_admin, "list_display", ("id", "venue_capacity", "festival_date"))

    def count_queries():
        with CaptureQueriesContext(connection) as queries:
            admin_client.get("/admin/bookings/booking/")
        return len(queries)

    monkeypatch.setattr(booking_admin, "list_select_related", False)
    without_join = count_queries()
    monkeypatch.setattr(booking_admin, "list_select_related", ("festival", "venue"))
    with_join = count_queries()
    rows = Booking.objects.count()
    assert without_join - with_join >= rows  # по запросу на каждую строку и связь
    assert with_join < without_join


def test_venue_changelist_query_count_does_not_depend_on_row_count(admin_client, orm_data):
    with CaptureQueriesContext(connection) as small:
        admin_client.get("/admin/venues/venue/")
    for index in range(6):
        Venue.objects.create(name=f"Новая {index}", capacity=100)
    with CaptureQueriesContext(connection) as large:
        admin_client.get("/admin/venues/venue/")
    assert len(large) == len(small)


def test_organizer_changelist_counts_festivals(admin_client, orm_data):
    response = admin_client.get("/admin/festivals/organizer/")
    assert [obj.festivals_total for obj in response.context["cl"].result_list] == [1]


# --- Карточки объектов и inline ---


def test_venue_change_page_shows_inline_bookings_and_readonly_fields(admin_client, orm_data):
    park = orm_data["park"]
    html = squash(admin_client.get(f"/admin/venues/venue/{park.pk}/change/"))
    assert "Бронирования площадки" in html
    assert "Фестиваль уличной музыки" in html
    assert park.slug in html  # slug показан только для чтения
    assert 'name="slug"' not in html and 'name="is_large"' not in html
    assert "Смотреть на сайте" in html  # ссылка строится по get_absolute_url()
    assert "Максимальное число посетителей" in html  # help_text


def test_venue_inline_allows_changing_status_but_not_adding_records(admin_client, orm_data):
    park = orm_data["park"]
    venue_admin = admin.site._registry[Venue]
    inline = venue_admin.get_inline_instances(None)[0]
    assert inline.has_add_permission(None) is False
    assert inline.can_delete is False and inline.extra == 0
    assert "status" in inline.fields and "festival" in inline.readonly_fields
    assert admin_client.get(f"/admin/venues/venue/{park.pk}/change/").status_code == 200


def test_organizer_and_festival_cards_show_related_objects(admin_client, orm_data):
    organizer, festival = orm_data["organizer"], orm_data["festival"]
    organizer_html = squash(admin_client.get(f"/admin/festivals/organizer/{organizer.pk}/change/"))
    assert (
        "Фестивали организатора" in organizer_html and "Фестиваль уличной музыки" in organizer_html
    )
    festival_html = squash(admin_client.get(f"/admin/festivals/festival/{festival.pk}/change/"))
    assert "Бронирования фестиваля" in festival_html and "Городской парк" in festival_html


def test_booking_add_form_uses_autocomplete_and_translated_labels(admin_client, orm_data):
    html = squash(admin_client.get("/admin/bookings/booking/add/"))
    assert "Статус бронирования" in html and "Фестиваль" in html and "Площадка" in html
    assert "admin-autocomplete" in html


def test_booking_add_form_rejects_second_active_booking_for_busy_date(admin_client, orm_data):
    data = {
        "festival": str(orm_data["festival"].pk),
        "venue": str(orm_data["park"].pk),  # у площадки уже есть активное бронирование
        "status": "active",
    }
    response = admin_client.post("/admin/bookings/booking/add/", data)
    assert response.status_code == 200
    assert "Площадка уже забронирована на эту дату" in squash(response)
    assert Booking.objects.count() == 2


def test_booking_add_form_accepts_booking_on_free_date(admin_client, orm_data):
    free_festival = Festival.objects.create(
        name="Свободный",
        date=TODAY + timedelta(days=30),
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )
    data = {
        "festival": str(free_festival.pk),
        "venue": str(orm_data["park"].pk),
        "status": "active",
    }
    response = admin_client.post("/admin/bookings/booking/add/", data)
    assert response.status_code == 302
    assert Booking.objects.count() == 3


# --- Массовые действия ---


def run_action(client, action, bookings):
    data = {
        "action": action,
        "_selected_action": [str(booking.pk) for booking in bookings],
        "index": "0",
    }
    return client.post("/admin/bookings/booking/", data, follow=True)


def test_cancel_action_changes_status_and_reports_count(admin_client, orm_data):
    response = run_action(admin_client, "cancel_bookings", [orm_data["active"]])
    orm_data["active"].refresh_from_db()
    assert orm_data["active"].status == Booking.Status.CANCELLED
    assert "Отменено бронирований: 1." in squash(response)


def test_complete_action_changes_status(admin_client, orm_data):
    response = run_action(admin_client, "complete_bookings", [orm_data["active"]])
    orm_data["active"].refresh_from_db()
    assert orm_data["active"].status == Booking.Status.COMPLETED
    assert "Завершено бронирований: 1." in squash(response)


def test_cancelled_booking_stops_blocking_the_venue_after_admin_action(admin_client, orm_data):
    park = orm_data["park"]
    assert park.is_available_on(TODAY) is False
    run_action(admin_client, "cancel_bookings", [orm_data["active"]])
    assert park.is_available_on(TODAY) is True


def test_restore_action_returns_booking_to_active_when_venue_is_free(admin_client, orm_data):
    response = run_action(admin_client, "restore_bookings", [orm_data["cancelled"]])
    orm_data["cancelled"].refresh_from_db()
    assert orm_data["cancelled"].status == Booking.Status.ACTIVE
    assert "Возвращено в активные: 1." in squash(response)


def test_restore_action_does_not_break_business_rule(admin_client, orm_data):
    # Площадка «Городской парк» уже занята активным бронированием на эту дату.
    duplicate = Booking.objects.create(
        festival=orm_data["festival"], venue=orm_data["park"], status=Booking.Status.CANCELLED
    )
    response = run_action(admin_client, "restore_bookings", [duplicate])
    duplicate.refresh_from_db()
    assert duplicate.status == Booking.Status.CANCELLED
    assert "Возвращено в активные: 0." in squash(response)
    assert "Пропущено" in squash(response)
