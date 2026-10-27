from datetime import date, timedelta

import pytest
from django.test import Client

from bookings.models import Booking
from festivals.models import Festival
from venues.models import Venue

pytestmark = pytest.mark.django_db


def template_names(response):
    return [template.name for template in response.templates]


def other_day():
    return (date.today() + timedelta(days=100)).isoformat()


def test_search_page_shows_only_form_without_parameters(orm_data, squash):
    response = Client().get("/venues/available/")
    html = squash(response)
    assert response.status_code == 200
    assert "venues/venue_available.html" in template_names(response)
    assert 'name="date"' in html
    assert 'name="attendees"' in html
    assert "Дата:" not in html
    assert "свободных площадок нет" not in html


def test_venue_booked_on_date_is_excluded(orm_data, squash):
    html = squash(Client().get("/venues/available/", {"date": date.today().isoformat()}))
    assert "Арена &lt;b&gt;" in html  # отменённое бронирование площадку не блокирует
    assert "Городской парк" not in html  # на эту дату у парка активное бронирование
    assert f"Дата: {date.today().strftime('%d.%m.%Y')}" in html


def test_all_venues_are_free_on_another_date(orm_data, squash):
    html = squash(Client().get("/venues/available/", {"date": other_day()}))
    assert "Городской парк" in html
    assert "Арена &lt;b&gt;" in html


def test_attendees_limit_filters_by_capacity(orm_data, squash):
    html = squash(Client().get("/venues/available/", {"date": other_day(), "attendees": 3000}))
    assert "Городской парк" in html
    assert "Арена" not in html
    assert "посетителей: 3000" in html


def test_boundary_capacity_is_included(orm_data, squash):
    html = squash(Client().get("/venues/available/", {"date": other_day(), "attendees": 5000}))
    assert "Городской парк" in html
    html = squash(Client().get("/venues/available/", {"date": other_day(), "attendees": 5001}))
    assert "На выбранную дату свободных площадок нет." in html


def test_search_without_results_shows_message(orm_data):
    response = Client().get(
        "/venues/available/", {"date": date.today().isoformat(), "attendees": 3000}
    )
    assert "На выбранную дату свободных площадок нет." in response.content.decode()


def test_search_in_empty_database_is_not_an_error(db):
    response = Client().get("/venues/available/", {"date": "2026-11-07"})
    assert response.status_code == 200
    assert "На выбранную дату свободных площадок нет." in response.content.decode()


def test_invalid_date_is_reported_without_search(orm_data, squash):
    for value in ("2026-13-45", "завтра", "2026-11-07' OR '1'='1"):
        html = squash(Client().get("/venues/available/", {"date": value}))
        assert "Укажите дату в формате ГГГГ-ММ-ДД." in html, value
        assert "Дата:" not in html, value


def test_invalid_attendees_is_reported_without_search(orm_data, squash):
    html = squash(Client().get("/venues/available/", {"date": "2026-11-07", "attendees": "много"}))
    assert "Число посетителей должно быть целым неотрицательным числом." in html
    assert "свободных площадок нет" not in html


def test_search_form_keeps_entered_values(orm_data, squash):
    html = squash(Client().get("/venues/available/", {"date": "2026-11-07", "attendees": 10}))
    assert 'value="2026-11-07"' in html
    assert 'value="10"' in html


def test_second_active_booking_on_other_day_does_not_block(orm_data, squash):
    festival = Festival.objects.create(
        name="Другой день",
        date=date.today() + timedelta(days=100),
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )
    Booking.objects.create(festival=festival, venue=orm_data["arena"])
    today = squash(Client().get("/venues/available/", {"date": date.today().isoformat()}))
    other = squash(Client().get("/venues/available/", {"date": other_day()}))
    assert "Арена &lt;b&gt;" in today
    assert "Арена" not in other
    assert "Городской парк" in other


def test_orm_query_for_free_venues_uses_exclude_and_filter(orm_data):
    booked = Booking.objects.filter(festival__date=date.today(), is_cancelled=False).values_list(
        "venue_id", flat=True
    )
    free = list(Venue.objects.exclude(pk__in=booked).values_list("name", flat=True))
    assert free == ["Арена <b>"]


def test_search_page_is_linked_from_venue_list(orm_data, squash):
    assert 'href="/venues/available/"' in squash(Client().get("/venues/"))


def test_available_route_is_not_taken_for_venue_id(orm_data):
    assert Client().get("/venues/available/").status_code == 200
    assert Client().get("/venues/%d/" % orm_data["park"].pk).status_code == 200
