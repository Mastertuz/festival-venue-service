"""ПР13: BookingCreateView и BookingUpdateView (CreateView, UpdateView, примеси)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import resolve
from django.utils import timezone
from django.views.generic import CreateView, UpdateView

import bookings.views as booking_views
from bookings.forms import BookingForm
from bookings.models import Booking
from bookings.views import BookingCreateView, BookingSaveMixin, BookingUpdateView
from festivals.models import Festival, Organizer
from venue_service.utils import DataMixin
from venues.models import Venue

pytestmark = pytest.mark.django_db

BUSY = "Площадка уже забронирована на эту дату: есть активное бронирование."


@pytest.fixture
def data(db):
    today = timezone.localdate()
    organizer = Organizer.objects.create(name="Организатор")
    park = Venue.objects.create(name="Парк", capacity=5000)
    arena = Venue.objects.create(name="Арена", capacity=2000)

    def festival(name, offset):
        return Festival.objects.create(
            name=name,
            date=today + timedelta(days=offset),
            expected_attendees=10,
            organizer=organizer,
        )

    future = festival("Будущий", 10)
    return {
        "park": park,
        "arena": arena,
        "future": future,
        "past": festival("Прошедший", -3),
        "booking": Booking.objects.create(festival=future, venue=park),
    }


def squashed(response):
    return " ".join(response.content.decode().split())


# --- классы ----------------------------------------------------------------------------------


def test_function_views_are_replaced_by_classes():
    assert not hasattr(booking_views, "booking_create")
    assert not hasattr(booking_views, "booking_update")
    assert resolve("/bookings/create/").func.view_class is BookingCreateView
    assert resolve("/bookings/1/edit/").func.view_class is BookingUpdateView


def test_create_view_is_configured_as_in_the_task():
    mro = BookingCreateView.__mro__
    assert issubclass(BookingCreateView, CreateView)
    assert mro.index(DataMixin) < mro.index(BookingSaveMixin) < mro.index(CreateView)
    assert BookingCreateView.model is Booking
    assert BookingCreateView.form_class is BookingForm
    assert BookingCreateView.template_name == "bookings/booking_form.html"
    assert str(BookingCreateView.success_url) == "/bookings/"
    assert BookingCreateView.title_page == "Создание бронирования"


def test_update_view_is_configured_as_in_the_task():
    mro = BookingUpdateView.__mro__
    assert issubclass(BookingUpdateView, UpdateView)
    assert mro.index(DataMixin) < mro.index(BookingSaveMixin) < mro.index(UpdateView)
    assert BookingUpdateView.model is Booking
    assert BookingUpdateView.form_class is BookingForm  # форма не дублируется
    assert BookingUpdateView.template_name == "bookings/booking_form.html"
    assert BookingUpdateView.pk_url_kwarg == "booking_id"
    assert BookingUpdateView.context_object_name == "booking"
    assert str(BookingUpdateView.success_url) == "/bookings/"


# --- создание --------------------------------------------------------------------------------


def test_create_get_shows_empty_form_title_and_initial_festival(data):
    response = Client().get("/bookings/create/")
    html = squashed(response)
    assert response.status_code == 200
    assert not response.context["form"].is_bound
    assert response.context["title"] == "Создание бронирования"
    assert "<title>Создание бронирования – Festival Venue Service</title>" in html
    assert "booking" not in response.context or response.context["booking"] is None
    assert response.context["form"].initial["festival"] == data["future"]


def test_create_post_saves_booking_and_redirects_with_message(data):
    response = Client().post(
        "/bookings/create/", {"festival": data["future"].pk, "venue": data["arena"].pk}
    )
    assert response.status_code == 302 and response["Location"] == "/bookings/"
    booking = Booking.objects.exclude(pk=data["booking"].pk).get()
    assert (booking.venue, booking.festival) == (data["arena"], data["future"])
    assert booking.status == Booking.Status.ACTIVE
    followed = Client().post(
        "/bookings/create/",
        {"festival": data["past"].pk, "venue": data["arena"].pk},
        follow=True,
    )
    assert followed.status_code == 200  # ошибка даты: форма показана повторно


def test_create_invalid_data_returns_form_with_errors_and_saves_nothing(data):
    count = Booking.objects.count()
    response = Client().post("/bookings/create/", {"festival": data["future"].pk})
    assert response.status_code == 200
    assert list(response.context["form"].errors) == ["venue"]
    assert Booking.objects.count() == count


def test_create_busy_venue_is_rejected_by_model_validation(data):
    response = Client().post(
        "/bookings/create/", {"festival": data["future"].pk, "venue": data["park"].pk}
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors() == [BUSY]
    assert Booking.objects.count() == 1


def test_create_database_conflict_goes_through_form_invalid(data, monkeypatch):
    monkeypatch.setattr(Booking, "clean", lambda self: None)
    response = Client().post(
        "/bookings/create/", {"festival": data["future"].pk, "venue": data["park"].pk}
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors() == [BUSY]
    assert Booking.objects.count() == 1


def test_create_requires_csrf_token(data):
    client = Client(enforce_csrf_checks=True)
    assert client.post("/bookings/create/", {"venue": data["arena"].pk}).status_code == 403


# --- редактирование ------------------------------------------------------------------------


def test_update_get_fills_form_and_builds_dynamic_title(data):
    booking = data["booking"]
    response = Client().get(f"/bookings/{booking.pk}/edit/")
    assert response.status_code == 200
    assert response.context["form"].instance == booking
    assert response.context["booking"] == booking
    assert response.context["title"] == f"Редактирование бронирования №{booking.pk}"
    assert (
        f"<title>Редактирование бронирования №{booking.pk} – Festival Venue Service</title>"
        in squashed(response)
    )


def test_update_post_changes_same_record(data):
    booking = data["booking"]
    response = Client().post(
        f"/bookings/{booking.pk}/edit/",
        {"festival": data["future"].pk, "venue": data["arena"].pk},
    )
    assert response.status_code == 302
    booking.refresh_from_db()
    assert booking.venue == data["arena"]
    assert Booking.objects.count() == 1


def test_update_without_changes_does_not_conflict_with_itself(data):
    booking = data["booking"]
    response = Client().post(
        f"/bookings/{booking.pk}/edit/",
        {"festival": data["future"].pk, "venue": data["park"].pk},
    )
    assert response.status_code == 302


def test_update_to_busy_venue_is_rejected(data):
    Booking.objects.create(festival=data["future"], venue=data["arena"])
    response = Client().post(
        f"/bookings/{data['booking'].pk}/edit/",
        {"festival": data["future"].pk, "venue": data["arena"].pk},
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors() == [BUSY]


def test_update_works_only_for_active_bookings_and_existing_ids(data):
    booking = data["booking"]
    booking.cancel()
    assert Client().get(f"/bookings/{booking.pk}/edit/").status_code == 404
    assert Client().get("/bookings/999999/edit/").status_code == 404


def test_update_requires_csrf_token(data):
    client = Client(enforce_csrf_checks=True)
    response = client.post(f"/bookings/{data['booking'].pk}/edit/", {"venue": data["arena"].pk})
    assert response.status_code == 403


# --- общая часть ---------------------------------------------------------------------------


def test_cancel_stays_a_function_view_with_require_post(data):
    assert callable(booking_views.booking_cancel)
    assert Client().get(f"/bookings/{data['booking'].pk}/cancel/").status_code == 405
    assert Client().post(f"/bookings/{data['booking'].pk}/cancel/").status_code == 302
    assert Booking.objects.get(pk=data["booking"].pk).status == Booking.Status.CANCELLED


def test_both_views_use_one_form_class_and_one_template(data):
    create = Client().get("/bookings/create/")
    update = Client().get(f"/bookings/{data['booking'].pk}/edit/")
    assert isinstance(create.context["form"], BookingForm)
    assert isinstance(update.context["form"], BookingForm)
    for response in (create, update):
        assert "bookings/booking_form.html" in [t.name for t in response.templates]
