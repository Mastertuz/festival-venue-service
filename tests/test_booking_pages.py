from datetime import date, timedelta

import pytest
from django.test import Client

from bookings.models import Booking
from festivals.models import Festival

pytestmark = pytest.mark.django_db


def template_names(response):
    return [template.name for template in response.templates]


def test_bookings_list_is_rendered_from_templates(orm_data):
    response = Client().get("/bookings/")
    names = template_names(response)
    assert response.status_code == 200
    assert "bookings/booking_list.html" in names
    assert "bookings/includes/booking_status.html" in names
    assert "base.html" in names


def test_bookings_list_shows_bookings_with_status_badges(orm_data, squash):
    html = squash(Client().get("/bookings/"))
    assert "<title>Бронирования – Festival Venue Service</title>" in html
    assert "Фестиваль уличной музыки → Городской парк" in html
    assert 'href="/bookings/%d/"' % orm_data["active"].pk in html
    assert 'href="/bookings/%d/"' % orm_data["cancelled"].pk in html
    assert "badge bg-success booking-status booking-status-active" in html
    assert "badge bg-secondary booking-status booking-status-cancelled" in html
    assert "Активно" in html
    assert "Отменено" in html


def test_bookings_list_escapes_html_in_names(orm_data):
    html = Client().get("/bookings/").content.decode()
    assert "Арена &lt;b&gt;" in html
    assert "Арена <b>" not in html


def test_bookings_list_shows_message_when_there_are_no_bookings(db):
    html = Client().get("/bookings/").content.decode()
    assert "Бронирования не найдены." in html


def test_bookings_list_rows_are_dictionaries_with_related_names(orm_data):
    rows = list(Client().get("/bookings/").context["bookings"])
    assert set(rows[0]) == {
        "id",
        "festival_name",
        "booking_date",
        "venue_name",
        "capacity",
        "organizer_name",
        "is_cancelled",
    }
    assert rows[0]["organizer_name"] == "АНО «Арт-Ивент»"
    assert isinstance(rows[0]["booking_date"], date)


def test_bookings_are_ordered_by_festival_date_then_id(orm_data):
    earlier = Festival.objects.create(
        name="Ранний",
        date=date.today() - timedelta(days=5),
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )
    early_booking = Booking.objects.create(festival=earlier, venue=orm_data["park"])
    ids = [row["id"] for row in Client().get("/bookings/").context["bookings"]]
    assert ids == [early_booking.pk, orm_data["active"].pk, orm_data["cancelled"].pk]


def test_booking_dates_are_formatted_with_date_filter(orm_data, squash):
    expected = date.today().strftime("%d.%m.%Y")
    assert expected in squash(Client().get("/bookings/"))
    detail = squash(Client().get("/bookings/%d/" % orm_data["active"].pk))
    assert f"<strong>Дата:</strong> {expected}" in detail


def test_bookings_list_shows_count_with_length_filter(orm_data, squash):
    assert "Всего бронирований: 2" in squash(Client().get("/bookings/"))


def test_bookings_can_be_limited_to_active_ones(orm_data, squash):
    html = squash(Client().get("/bookings/?active=1"))
    assert "Всего бронирований: 1" in html
    assert 'href="/bookings/%d/"' % orm_data["active"].pk in html
    assert 'href="/bookings/%d/"' % orm_data["cancelled"].pk not in html
    assert "Отменено" not in html


def test_booking_list_shows_all_bookings_by_default(orm_data, squash):
    html = squash(Client().get("/bookings/"))
    assert "Всего бронирований: 2" in html
    assert 'name="active"' in html and "checked" not in html


def test_booking_list_query_count(orm_data, django_assert_num_queries):
    """Число записей, страница бронирований, список площадок и список организаторов для формы."""
    with django_assert_num_queries(4):
        Client().get("/bookings/")


def test_booking_detail_shows_related_objects(orm_data, squash):
    pk = orm_data["active"].pk
    response = Client().get("/bookings/%d/" % pk)
    html = squash(response)
    assert response.status_code == 200
    assert "bookings/booking_detail.html" in template_names(response)
    assert f"<title>Бронирование №{pk} – Festival Venue Service</title>" in html
    assert "<strong>Фестиваль:</strong> Фестиваль уличной музыки" in html
    assert "<strong>Организатор:</strong> АНО «Арт-Ивент»" in html
    assert 'href="/venues/%d/"> Городской парк </a>' % orm_data["park"].pk in html
    assert "Активно" in html


def test_booking_detail_shows_cancelled_status(orm_data, squash):
    html = squash(Client().get("/bookings/%d/" % orm_data["cancelled"].pk))
    assert "booking-status-cancelled" in html
    assert "Отменено" in html


def test_booking_detail_has_link_back_to_list(orm_data, squash):
    html = squash(Client().get("/bookings/%d/" % orm_data["active"].pk))
    assert 'href="/bookings/"' in html
    assert "← к списку бронирований" in html


def test_booking_detail_unknown_id_returns_404(orm_data):
    response = Client().get("/bookings/999999/")
    assert response.status_code == 404
    assert "homepage/404.html" in template_names(response)


def test_booking_detail_in_empty_database_returns_404(db):
    assert Client().get("/bookings/1/").status_code == 404


def test_booking_detail_uses_select_related_single_query(orm_data, django_assert_num_queries):
    """Бронирование, фестиваль, организатор и площадка загружаются одним запросом."""
    with django_assert_num_queries(1):
        response = Client().get("/bookings/%d/" % orm_data["active"].pk)
        assert response.status_code == 200


def test_bookings_are_read_through_orm(orm_data):
    orm_data["active"].cancel()
    assert "Отменено" in Client().get("/bookings/%d/" % orm_data["active"].pk).content.decode()
    assert "Всего бронирований: 0" in " ".join(
        Client().get("/bookings/?active=1").content.decode().split()
    )
