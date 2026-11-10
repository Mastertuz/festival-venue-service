"""ПР11: редактирование (BookingForm с instance) и отмена бронирования (POST, смена статуса)."""

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.test import Client
from django.utils import timezone

from bookings.forms import BookingForm
from bookings.models import Booking
from festivals.models import Festival, Organizer
from venues.models import Venue

pytestmark = pytest.mark.django_db

BUSY = "Площадка уже забронирована на эту дату: есть активное бронирование."
PAST = "Нельзя создать бронирование на прошедшую дату: фестиваль уже состоялся."


def squashed(response):
    return " ".join(response.content.decode().split())


def edit_url(booking):
    return f"/bookings/{booking.pk}/edit/"


def cancel_url(booking):
    return f"/bookings/{booking.pk}/cancel/"


@pytest.fixture
def data(db):
    """Три площадки, фестивали на разные даты и активное бронирование «Парк» на «Будущий»."""
    today = timezone.localdate()
    organizer = Organizer.objects.create(name="Арт-Ивент")
    park = Venue.objects.create(name="Парк", capacity=5000)
    arena = Venue.objects.create(name="Арена", capacity=2000)
    hall = Venue.objects.create(name="Зал", capacity=300)

    def festival(name, offset):
        return Festival.objects.create(
            name=name,
            date=today + timedelta(days=offset),
            expected_attendees=100,
            organizer=organizer,
        )

    future = festival("Будущий", 10)
    return {
        "park": park,
        "arena": arena,
        "hall": hall,
        "past": festival("Прошедший", -3),
        "future": future,
        "second": festival("Второй будущий", 20),
        "booking": Booking.objects.create(festival=future, venue=park),
    }


# --- редактирование: GET -------------------------------------------------------


def test_edit_page_shows_form_filled_with_current_values(data):
    response = Client().get(edit_url(data["booking"]))
    html = squashed(response)
    assert response.status_code == 200
    assert "bookings/booking_form.html" in [t.name for t in response.templates]
    form = response.context["form"]
    assert form.instance == data["booking"]
    assert response.context["booking"] == data["booking"]
    assert f"Редактирование бронирования №{data['booking'].pk}" in html
    assert "Сохранить изменения" in html and "Создать бронирование" not in html
    assert f'<option value="{data["future"].pk}" selected>' in html
    assert f'<option value="{data["park"].pk}" selected>' in html
    assert 'name="csrfmiddlewaretoken"' in html


def test_edit_uses_the_same_form_class_as_creation(data):
    form = Client().get(edit_url(data["booking"])).context["form"]
    assert isinstance(form, BookingForm)


@pytest.mark.parametrize("method", ["get", "post"])
def test_edit_of_missing_booking_gives_404(data, method):
    response = getattr(Client(), method)("/bookings/999999/edit/")
    assert response.status_code == 404


@pytest.mark.parametrize("status", [Booking.Status.CANCELLED, Booking.Status.COMPLETED])
def test_only_active_booking_can_be_opened_for_editing(data, status):
    Booking.objects.filter(pk=data["booking"].pk).update(status=status)
    assert Client().get(edit_url(data["booking"])).status_code == 404
    assert Client().post(edit_url(data["booking"]), {"venue": data["arena"].pk}).status_code == 404


# --- редактирование: POST ------------------------------------------------------


def test_changing_venue_updates_the_same_record(data):
    response = Client().post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["arena"].pk},
    )
    assert response.status_code == 302 and response["Location"] == "/bookings/"
    assert Booking.objects.count() == 1
    booking = Booking.objects.get()
    assert booking.pk == data["booking"].pk
    assert booking.venue == data["arena"]
    assert booking.status == Booking.Status.ACTIVE


def test_changing_festival_moves_booking_to_its_date(data):
    Client().post(
        edit_url(data["booking"]),
        {"festival": data["second"].pk, "venue": data["park"].pk},
    )
    booking = Booking.objects.get()
    assert booking.festival == data["second"]
    assert booking.booking_date == data["second"].date


def test_saving_without_changes_does_not_conflict_with_itself(data):
    response = Client().post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["park"].pk},
    )
    assert response.status_code == 302
    assert Booking.objects.count() == 1
    assert Booking.objects.get().pk == data["booking"].pk


def test_success_message_is_shown_after_redirect(data):
    response = Client().post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["arena"].pk},
        follow=True,
    )
    assert "Изменения сохранены." in squashed(response)


def test_edit_to_past_festival_is_rejected_and_record_is_unchanged(data):
    response = Client().post(
        edit_url(data["booking"]),
        {"festival": data["past"].pk, "venue": data["park"].pk},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["festival"] == [PAST]
    assert PAST in squashed(response)
    data["booking"].refresh_from_db()
    assert data["booking"].festival == data["future"]


def test_edit_to_venue_busy_with_another_active_booking_is_rejected(data):
    Booking.objects.create(festival=data["future"], venue=data["arena"])
    response = Client().post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["arena"].pk},
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors() == [BUSY]
    assert BUSY in squashed(response)
    data["booking"].refresh_from_db()
    assert data["booking"].venue == data["park"]


def test_cancelled_booking_of_other_venue_does_not_block_edit(data):
    Booking.objects.create(
        festival=data["future"], venue=data["arena"], status=Booking.Status.CANCELLED
    )
    response = Client().post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["arena"].pk},
    )
    assert response.status_code == 302
    assert Booking.objects.active().count() == 1


def test_invalid_data_keeps_entered_values_and_changes_nothing(data):
    response = Client().post(edit_url(data["booking"]), {"festival": data["second"].pk})
    assert list(response.context["form"].errors) == ["venue"]
    assert f'<option value="{data["second"].pk}" selected>' in squashed(response)
    data["booking"].refresh_from_db()
    assert data["booking"].festival == data["future"]


def test_status_cannot_be_changed_through_the_edit_form(data):
    Client().post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["arena"].pk, "status": "cancelled"},
    )
    assert Booking.objects.get().status == Booking.Status.ACTIVE


def test_database_conflict_during_edit_is_shown_as_form_error(data, monkeypatch):
    Booking.objects.create(festival=data["future"], venue=data["arena"])
    monkeypatch.setattr(Booking, "clean", lambda self: None)
    response = Client().post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["arena"].pk},
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors() == [BUSY]
    data["booking"].refresh_from_db()
    assert data["booking"].venue == data["park"]


def test_unrelated_integrity_error_is_not_hidden_during_edit(data, monkeypatch):
    def broken_save(self, *args, **kwargs):
        raise IntegrityError("другая ошибка базы данных")

    monkeypatch.setattr(BookingForm, "save", broken_save)
    with pytest.raises(IntegrityError, match="другая ошибка"):
        Client().post(
            edit_url(data["booking"]),
            {"festival": data["future"].pk, "venue": data["arena"].pk},
        )


def test_edit_post_without_csrf_token_is_forbidden(data):
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        edit_url(data["booking"]),
        {"festival": data["future"].pk, "venue": data["arena"].pk},
    )
    assert response.status_code == 403
    data["booking"].refresh_from_db()
    assert data["booking"].venue == data["park"]


# --- отмена ----------------------------------------------------------------------


def test_cancel_changes_status_and_keeps_the_record(data):
    response = Client().post(cancel_url(data["booking"]))
    assert response.status_code == 302 and response["Location"] == "/bookings/"
    booking = Booking.objects.get(pk=data["booking"].pk)  # запись не удалена
    assert booking.status == Booking.Status.CANCELLED
    assert booking.festival == data["future"] and booking.venue == data["park"]
    assert Booking.objects.count() == 1


def test_cancel_shows_message_once(data):
    client = Client()
    response = client.post(cancel_url(data["booking"]), follow=True)
    assert f"Бронирование №{data['booking'].pk} отменено." in squashed(response)
    assert "отменено." not in squashed(client.get("/bookings/")).replace("Отменено", "")


def test_cancel_by_get_request_is_not_allowed_and_changes_nothing(data):
    response = Client().get(cancel_url(data["booking"]))
    assert response.status_code == 405
    data["booking"].refresh_from_db()
    assert data["booking"].status == Booking.Status.ACTIVE


@pytest.mark.parametrize("method", ["put", "delete", "head"])
def test_cancel_accepts_only_post(data, method):
    response = getattr(Client(), method)(cancel_url(data["booking"]))
    assert response.status_code == 405
    data["booking"].refresh_from_db()
    assert data["booking"].status == Booking.Status.ACTIVE


def test_repeated_cancel_gives_404(data):
    assert Client().post(cancel_url(data["booking"])).status_code == 302
    assert Client().post(cancel_url(data["booking"])).status_code == 404


def test_cancel_of_completed_or_missing_booking_gives_404(data):
    data["booking"].complete()
    assert Client().post(cancel_url(data["booking"])).status_code == 404
    assert Client().post("/bookings/999999/cancel/").status_code == 404
    data["booking"].refresh_from_db()
    assert data["booking"].status == Booking.Status.COMPLETED


def test_cancel_without_csrf_token_is_forbidden(data):
    client = Client(enforce_csrf_checks=True)
    assert client.post(cancel_url(data["booking"])).status_code == 403
    data["booking"].refresh_from_db()
    assert data["booking"].status == Booking.Status.ACTIVE


def test_cancel_with_csrf_token_from_the_page_is_accepted(data):
    client = Client(enforce_csrf_checks=True)
    token = client.get("/bookings/").cookies["csrftoken"].value
    response = client.post(cancel_url(data["booking"]), {"csrfmiddlewaretoken": token})
    assert response.status_code == 302


def test_cancelled_booking_no_longer_blocks_the_venue(data):
    assert data["park"].is_available_on(data["future"].date) is False
    Client().post(cancel_url(data["booking"]))
    assert data["park"].is_available_on(data["future"].date) is True
    other = Festival.objects.create(
        name="В тот же день",
        date=data["future"].date,
        expected_attendees=10,
        organizer=data["future"].organizer,
    )
    created = Client().post("/bookings/create/", {"festival": other.pk, "venue": data["park"].pk})
    assert created.status_code == 302
    assert Booking.objects.active().count() == 1


# --- отображение в интерфейсе ------------------------------------------------------


def test_list_shows_actions_only_for_active_bookings(data):
    cancelled = Booking.objects.create(
        festival=data["second"], venue=data["park"], status=Booking.Status.CANCELLED
    )
    html = squashed(Client().get("/bookings/"))
    assert edit_url(data["booking"]) in html
    assert cancel_url(data["booking"]) in html
    assert edit_url(cancelled) not in html
    assert cancel_url(cancelled) not in html


def test_cancel_button_is_a_post_form_with_csrf_token(data):
    html = squashed(Client().get("/bookings/"))
    action = html.index(f'action="{cancel_url(data["booking"])}"')
    start, end = html.rindex("<form", 0, action), html.index("</form>", action)
    form = html[start:end]
    assert 'method="post"' in form
    assert 'name="csrfmiddlewaretoken"' in form
    assert "Отменить" in form


def test_cancelled_booking_stays_in_list_with_status_and_is_hidden_by_active_filter(data):
    Client().post(cancel_url(data["booking"]))
    response = Client().get("/bookings/")
    assert response.context["total_count"] == 1
    assert "Отменено" in squashed(response)
    assert Client().get("/bookings/", {"active": "1"}).context["total_count"] == 0


def test_detail_page_shows_actions_for_active_booking_only(data):
    url = f"/bookings/{data['booking'].pk}/"
    html = squashed(Client().get(url))
    assert edit_url(data["booking"]) in html and cancel_url(data["booking"]) in html
    data["booking"].cancel()
    html = squashed(Client().get(url))
    assert edit_url(data["booking"]) not in html and cancel_url(data["booking"]) not in html


def test_list_filters_sorting_and_pagination_still_work_after_changes(data):
    Client().post(
        edit_url(data["booking"]),
        {"festival": data["second"].pk, "venue": data["hall"].pk},
    )
    response = Client().get(
        "/bookings/", {"venue": data["hall"].pk, "sort": "venue", "dir": "desc", "page": 1}
    )
    assert [row["id"] for row in response.context["bookings"]] == [data["booking"].pk]
    assert response.context["error"] is None
