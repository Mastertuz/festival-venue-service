"""ПР11: создание бронирования через ModelForm (BookingForm и представление booking_create)."""

from datetime import timedelta

import pytest
from django import forms
from django.db import IntegrityError
from django.test import Client
from django.utils import timezone

from bookings.forms import BookingForm
from bookings.models import Booking
from festivals.models import Festival, Organizer
from venues.models import Venue

pytestmark = pytest.mark.django_db

URL = "/bookings/create/"
BUSY = "Площадка уже забронирована на эту дату: есть активное бронирование."
PAST = "Нельзя создать бронирование на прошедшую дату: фестиваль уже состоялся."


def squashed(response):
    return " ".join(response.content.decode().split())


@pytest.fixture
def data(db):
    """Организатор, две площадки и фестивали: прошедший, сегодняшний и два будущих."""
    today = timezone.localdate()
    organizer = Organizer.objects.create(name="Арт-Ивент")
    park = Venue.objects.create(name="Парк", capacity=5000)
    arena = Venue.objects.create(name="Арена", capacity=2000)

    def festival(name, offset):
        return Festival.objects.create(
            name=name,
            date=today + timedelta(days=offset),
            expected_attendees=100,
            organizer=organizer,
        )

    return {
        "park": park,
        "arena": arena,
        "past": festival("Прошедший", -3),
        "today": festival("Сегодняшний", 0),
        "future": festival("Будущий", 10),
        "second": festival("Второй будущий", 20),
    }


def post(**fields):
    return Client().post(URL, fields)


def form_data(festival, venue):
    return {"festival": festival.pk, "venue": venue.pk}


# --- устройство формы --------------------------------------------------------


def test_form_is_a_model_form_for_booking_with_explicit_fields():
    assert issubclass(BookingForm, forms.ModelForm)
    assert BookingForm.Meta.model is Booking
    assert BookingForm.Meta.fields == ["festival", "venue"]
    assert list(BookingForm().fields) == ["festival", "venue"]


def test_status_is_not_available_in_the_form():
    assert "status" not in BookingForm().fields
    assert "status" not in BookingForm.Meta.fields


def test_form_has_labels_help_texts_and_bootstrap_widgets():
    form = BookingForm()
    assert form.fields["festival"].label == "Фестиваль"
    assert form.fields["venue"].label == "Площадка"
    assert form.fields["festival"].help_text
    assert form.fields["venue"].help_text
    assert form.fields["festival"].widget.attrs["class"] == "form-select"
    assert form.fields["venue"].widget.attrs["class"] == "form-select"


def test_choice_labels_show_festival_date_and_venue_capacity(data):
    form = BookingForm()
    festival_label = form.fields["festival"].label_from_instance(data["future"])
    assert festival_label == f"Будущий — {data['future'].date:%d.%m.%Y}"
    assert form.fields["venue"].label_from_instance(data["park"]) == "Парк (5000 мест)"


def test_festival_choices_are_ordered_by_date(data):
    names = [festival.name for festival in BookingForm().fields["festival"].queryset]
    assert names == ["Прошедший", "Сегодняшний", "Будущий", "Второй будущий"]


# --- GET: пустая форма -------------------------------------------------------


def test_get_shows_empty_form_with_csrf_token_and_two_fields(data):
    response = Client().get(URL)
    html = squashed(response)
    assert response.status_code == 200
    assert "bookings/booking_form.html" in [t.name for t in response.templates]
    assert not response.context["form"].is_bound
    assert "Создание бронирования" in html
    assert 'name="csrfmiddlewaretoken"' in html
    assert 'name="festival"' in html and 'name="venue"' in html
    assert 'name="status"' not in html
    assert "Создать бронирование" in html
    assert "Дата бронирования равна дате проведения фестиваля." in html


def test_get_preselects_nearest_upcoming_festival(data):
    response = Client().get(URL)
    assert response.context["form"].initial["festival"] == data["today"]
    assert f'<option value="{data["today"].pk}" selected>' in squashed(response)


def test_get_without_festivals_shows_form_without_initial_value(db):
    response = Client().get(URL)
    assert response.status_code == 200
    assert response.context["form"].initial["festival"] is None


def test_form_is_available_by_named_url_and_linked_from_the_list(data):
    from django.urls import reverse

    assert reverse("bookings:create") == URL
    assert URL in squashed(Client().get("/bookings/"))


# --- POST: успешное создание -------------------------------------------------


def test_valid_post_creates_active_booking_and_redirects_to_list(data):
    response = post(**form_data(data["future"], data["park"]))
    assert response.status_code == 302
    assert response["Location"] == "/bookings/"
    booking = Booking.objects.get()
    assert booking.festival == data["future"]
    assert booking.venue == data["park"]
    assert booking.status == Booking.Status.ACTIVE
    assert booking.booking_date == data["future"].date


def test_success_message_is_shown_once_after_redirect(data):
    client = Client()
    response = client.post(URL, form_data(data["future"], data["park"]), follow=True)
    assert "Бронирование создано." in squashed(response)
    assert "Бронирование создано." not in squashed(client.get("/bookings/"))


def test_new_booking_appears_in_the_list(data):
    post(**form_data(data["future"], data["park"]))
    response = Client().get("/bookings/")
    assert response.context["total_count"] == 1
    assert "Будущий → Парк" in squashed(response)


def test_booking_for_today_is_allowed(data):
    assert post(**form_data(data["today"], data["park"])).status_code == 302
    assert Booking.objects.count() == 1


def test_status_from_post_is_ignored(data):
    # Поле status не входит в форму: подставленное значение не попадает в модель.
    response = post(**form_data(data["future"], data["park"]), status="cancelled")
    assert response.status_code == 302
    assert Booking.objects.get().status == Booking.Status.ACTIVE


# --- POST: ошибки полей ------------------------------------------------------


def test_empty_post_shows_required_errors_and_saves_nothing(data):
    response = post()
    html = squashed(response)
    assert response.status_code == 200
    assert response.context["form"].is_bound
    assert html.count("Обязательное поле.") == 2
    assert Booking.objects.count() == 0


def test_missing_venue_is_reported_and_entered_festival_is_kept(data):
    response = post(festival=data["future"].pk)
    form = response.context["form"]
    assert list(form.errors) == ["venue"]
    assert f'<option value="{data["future"].pk}" selected>' in squashed(response)
    assert Booking.objects.count() == 0


def test_unknown_festival_or_venue_is_rejected(data):
    response = post(festival=999999, venue="abc")
    assert set(response.context["form"].errors) == {"festival", "venue"}
    assert Booking.objects.count() == 0


def test_past_date_is_rejected_by_clean_festival(data):
    response = post(**form_data(data["past"], data["park"]))
    form = response.context["form"]
    assert response.status_code == 200
    assert form.errors["festival"] == [PAST]
    assert PAST in squashed(response)
    assert Booking.objects.count() == 0


def test_past_date_error_is_a_field_error_not_a_general_error(data):
    form = BookingForm(form_data(data["past"], data["park"]))
    assert not form.is_valid()
    assert list(form.errors) == ["festival"]
    assert form.non_field_errors() == []


# --- POST: занятость площадки ------------------------------------------------


def test_busy_venue_is_rejected_with_general_error(data):
    Booking.objects.create(festival=data["future"], venue=data["park"])
    other = Festival.objects.create(
        name="В тот же день",
        date=data["future"].date,
        expected_attendees=10,
        organizer=data["future"].organizer,
    )
    response = post(**form_data(other, data["park"]))
    form = response.context["form"]
    assert response.status_code == 200
    assert form.non_field_errors() == [BUSY]
    assert not form.errors.get("festival") and not form.errors.get("venue")
    assert BUSY in squashed(response)
    assert Booking.objects.count() == 1


def test_same_venue_on_other_date_and_other_venue_on_same_date_are_allowed(data):
    Booking.objects.create(festival=data["future"], venue=data["park"])
    assert post(**form_data(data["second"], data["park"])).status_code == 302
    assert post(**form_data(data["future"], data["arena"])).status_code == 302
    assert Booking.objects.active().count() == 3


@pytest.mark.parametrize("status", [Booking.Status.CANCELLED, Booking.Status.COMPLETED])
def test_cancelled_and_completed_bookings_do_not_block_the_venue(data, status):
    Booking.objects.create(festival=data["future"], venue=data["park"], status=status)
    response = post(**form_data(data["future"], data["park"]))
    assert response.status_code == 302
    assert Booking.objects.active().count() == 1


def test_booking_blocks_venue_until_it_is_cancelled(data):
    first = Booking.objects.create(festival=data["future"], venue=data["park"])
    assert post(**form_data(data["future"], data["park"])).status_code == 200
    first.cancel()
    assert post(**form_data(data["future"], data["park"])).status_code == 302
    assert Booking.objects.active().count() == 1


# --- конкурентное создание: защита на уровне базы данных ----------------------


def test_database_conflict_is_shown_as_form_error_not_as_server_error(data, monkeypatch):
    # Имитация гонки: проверка в Booking.clean() ещё не видит чужую запись,
    # а триггер базы данных отклоняет вставку при сохранении.
    Booking.objects.create(festival=data["future"], venue=data["park"])
    monkeypatch.setattr(Booking, "clean", lambda self: None)
    other = Festival.objects.create(
        name="В тот же день",
        date=data["future"].date,
        expected_attendees=10,
        organizer=data["future"].organizer,
    )
    response = post(**form_data(other, data["park"]))
    assert response.status_code == 200
    assert response.context["form"].non_field_errors() == [BUSY]
    assert Booking.objects.count() == 1


def test_unrelated_integrity_error_is_not_hidden(data, monkeypatch):
    def broken_save(self, *args, **kwargs):
        raise IntegrityError("другая ошибка базы данных")

    monkeypatch.setattr(BookingForm, "save", broken_save)
    with pytest.raises(IntegrityError, match="другая ошибка"):
        post(**form_data(data["future"], data["park"]))


# --- защита POST-запроса -----------------------------------------------------


def test_post_without_csrf_token_is_forbidden(data):
    client = Client(enforce_csrf_checks=True)
    response = client.post(URL, form_data(data["future"], data["park"]))
    assert response.status_code == 403
    assert Booking.objects.count() == 0


def test_post_with_csrf_token_is_accepted(data):
    client = Client(enforce_csrf_checks=True)
    token = client.get(URL).cookies["csrftoken"].value
    response = client.post(
        URL, {**form_data(data["future"], data["park"]), "csrfmiddlewaretoken": token}
    )
    assert response.status_code == 302
    assert Booking.objects.count() == 1


def test_failed_post_does_not_change_other_pages(data):
    post(**form_data(data["past"], data["park"]))
    assert Client().get("/bookings/").status_code == 200
    assert Client().get("/bookings/statistics/").status_code == 200
