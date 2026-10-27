from datetime import date, timedelta

import pytest
from django.test import Client

from bookings.models import Booking
from festivals.models import Festival

pytestmark = pytest.mark.django_db


def template_names(response):
    return [template.name for template in response.templates]


def add_active_bookings_for(venue, organizer, count):
    """Добавить фестивали и активные бронирования на площадку (для проверки условия по агрегату)."""
    for number in range(count):
        festival = Festival.objects.create(
            name=f"Доп. фестиваль {number}",
            date=date.today() + timedelta(days=10 + number),
            expected_attendees=100,
            organizer=organizer,
        )
        Booking.objects.create(festival=festival, venue=venue)


def test_statistics_page_is_rendered_from_template(orm_data):
    response = Client().get("/bookings/statistics/")
    assert response.status_code == 200
    assert "bookings/statistics.html" in template_names(response)
    assert "base.html" in template_names(response)


def test_statistics_shows_aggregates(orm_data, squash):
    html = squash(Client().get("/bookings/statistics/"))
    assert "Активных бронирований" in html
    assert '<div class="fs-3">1</div>' in html  # активных бронирований
    assert "2000 – 5000" in html  # MIN и MAX вместимости
    assert "3500,0" in html  # AVG вместимости (в русской локали — десятичная запятая)


def test_aggregate_values_in_context(orm_data):
    summary = Client().get("/bookings/statistics/").context["summary"]
    assert summary == {
        "venues_count": 2,
        "min_capacity": 2000,
        "max_capacity": 5000,
        "avg_capacity": 3500.0,
        "total_capacity": 7000,
    }


def test_statistics_counts_bookings_by_venue_with_zero_for_unbooked(orm_data, squash):
    html = squash(Client().get("/bookings/statistics/"))
    assert "<td>Городской парк</td> <td>1</td>" in html
    # у площадки есть только отменённое бронирование: она остаётся в списке со значением 0
    assert "<td>Арена &lt;b&gt;</td> <td>0</td>" in html


def test_by_venue_is_sorted_by_count_descending(orm_data):
    rows = list(Client().get("/bookings/statistics/").context["by_venue"])
    assert [(r["venue_name"], r["bookings_count"]) for r in rows] == [
        ("Городской парк", 1),
        ("Арена <b>", 0),
    ]


def test_cancelled_bookings_are_not_counted(orm_data):
    orm_data["active"].cancel()
    rows = {
        r["venue_name"]: r["bookings_count"]
        for r in Client().get("/bookings/statistics/").context["by_venue"]
    }
    assert rows == {"Городской парк": 0, "Арена <b>": 0}


def test_statistics_groups_festivals_by_organizer(orm_data, squash):
    html = squash(Client().get("/bookings/statistics/"))
    assert "<td>АНО «Арт-Ивент»</td> <td>1</td> <td>4500</td>" in html


def test_organizer_without_festivals_is_not_in_statistics(orm_data):
    from festivals.models import Organizer

    Organizer.objects.create(name="Без фестивалей")
    names = [
        r["organizer_name"] for r in Client().get("/bookings/statistics/").context["by_organizer"]
    ]
    assert names == ["АНО «Арт-Ивент»"]


def test_popular_venues_use_threshold_on_aggregate(orm_data, squash):
    assert "Таких площадок нет." in squash(Client().get("/bookings/statistics/"))
    add_active_bookings_for(orm_data["park"], orm_data["organizer"], 2)  # вместе с исходным — 3
    html = squash(Client().get("/bookings/statistics/"))
    assert "более 2 бронирований" in html
    assert "<span>Городской парк</span> <span>3</span>" in html
    assert "Таких площадок нет." not in html


def test_threshold_is_strict_greater_than(orm_data):
    add_active_bookings_for(orm_data["park"], orm_data["organizer"], 1)  # ровно 2
    assert list(Client().get("/bookings/statistics/").context["popular"]) == []


def test_statistics_in_empty_database_shows_placeholders(db, squash):
    response = Client().get("/bookings/statistics/")
    html = squash(response)
    assert response.status_code == 200
    assert "Данные отсутствуют." in html
    assert "— – —" in html  # MIN и MAX отсутствуют (NULL)


def test_statistics_makes_five_queries(orm_data, django_assert_num_queries):
    with django_assert_num_queries(5):
        response = Client().get("/bookings/statistics/")
        context = response.context
        list(context["by_venue"]), list(context["by_organizer"]), list(context["popular"])


def test_statistics_is_in_navigation(orm_data, squash):
    for url in ("/", "/venues/", "/bookings/", "/bookings/statistics/"):
        assert 'href="/bookings/statistics/">Статистика</a>' in squash(Client().get(url)), url


def test_statistics_route_is_not_taken_for_booking_id(orm_data):
    assert Client().get("/bookings/statistics/").status_code == 200
    assert Client().get("/bookings/%d/" % orm_data["active"].pk).status_code == 200
