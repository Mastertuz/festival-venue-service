from datetime import date, timedelta

import pytest
from django.template.loader import render_to_string
from django.test import Client

from bookings.models import Booking
from festivals.models import Festival
from venues.models import Venue

pytestmark = pytest.mark.django_db


def template_names(response):
    return [template.name for template in response.templates]


def test_venues_list_is_rendered_from_templates(orm_data):
    response = Client().get("/venues/")
    names = template_names(response)
    assert response.status_code == 200
    assert "venues/venue_list.html" in names
    assert "venues/includes/venue_card.html" in names
    assert "base.html" in names


def test_venues_list_shows_venues_from_database(orm_data, squash):
    html = squash(Client().get("/venues/"))
    assert "<title>Площадки – Festival Venue Service</title>" in html
    assert "Городской парк" in html
    assert "Вместимость: 5000 мест" in html
    assert 'href="/venues/%d/"' % orm_data["park"].pk in html
    assert 'href="/venues/%d/"' % orm_data["arena"].pk in html


def test_venues_list_escapes_html_in_names(orm_data):
    html = Client().get("/venues/").content.decode()
    assert "Арена &lt;b&gt;" in html
    assert "Арена <b>" not in html


def test_venues_list_is_ordered_by_name(orm_data):
    Venue.objects.create(name="Аллея", capacity=10)
    names = [venue.name for venue in Client().get("/venues/").context["venues"]]
    assert names == ["Аллея", "Арена <b>", "Городской парк"]


def test_venues_list_shows_message_when_there_are_no_venues(db):
    html = Client().get("/venues/").content.decode()
    assert "Площадки не найдены." in html


def test_venue_detail_shows_booked_venue_as_busy(orm_data, squash):
    response = Client().get("/venues/%d/" % orm_data["park"].pk)
    html = squash(response)
    assert response.status_code == 200
    assert "venues/venue_detail.html" in template_names(response)
    assert "<title>Городской парк – Festival Venue Service</title>" in html
    assert "<strong>Вместимость:</strong> 5000 мест" in html
    assert 'class="badge bg-danger">занята</span>' in html


def test_venue_detail_shows_free_venue_as_available(orm_data, squash):
    html = squash(Client().get("/venues/%d/" % orm_data["arena"].pk))
    assert 'class="badge bg-success">свободна</span>' in html


def test_venue_detail_has_link_back_to_list(orm_data, squash):
    html = squash(Client().get("/venues/%d/" % orm_data["park"].pk))
    assert 'href="/venues/"' in html
    assert "← к списку площадок" in html


def test_venue_detail_shows_upcoming_bookings_via_reverse_relation(orm_data, squash):
    html = squash(Client().get("/venues/%d/" % orm_data["park"].pk))
    assert "Ближайшие бронирования" in html
    assert "Фестиваль уличной музыки" in html
    assert 'href="/bookings/%d/"' % orm_data["active"].pk in html


def test_cancelled_bookings_are_not_listed_as_upcoming(orm_data, squash):
    html = squash(Client().get("/venues/%d/" % orm_data["arena"].pk))
    assert "Ближайших бронирований нет." in html


def test_past_bookings_are_not_listed_as_upcoming(orm_data, squash):
    past = Festival.objects.create(
        name="Прошлогодний",
        date=date.today() - timedelta(days=10),
        expected_attendees=100,
        organizer=orm_data["organizer"],
    )
    Booking.objects.create(festival=past, venue=orm_data["arena"])
    html = squash(Client().get("/venues/%d/" % orm_data["arena"].pk))
    assert "Прошлогодний" not in html


def test_venue_detail_unknown_id_returns_404(orm_data):
    response = Client().get("/venues/999999/")
    assert response.status_code == 404
    assert "homepage/404.html" in template_names(response)


def test_venue_detail_in_empty_database_returns_404(db):
    assert Client().get("/venues/1/").status_code == 404


def test_venue_card_uses_default_filter_for_empty_name():
    html = render_to_string(
        "venues/includes/venue_card.html", {"venue": Venue(id=7, name="", capacity=100)}
    )
    assert "Без названия" in html
    assert "Вместимость: 100 мест" in html


def test_venues_list_shows_count_with_length_filter(orm_data, squash):
    assert "Всего площадок: 2" in squash(Client().get("/venues/"))


def test_venues_are_read_through_orm_not_from_json(orm_data):
    orm_data["park"].name = "Парк (обновлено)"
    orm_data["park"].save()
    assert "Парк (обновлено)" in Client().get("/venues/").content.decode()
    assert "Парк (обновлено)" in Client().get("/venues/%d/" % orm_data["park"].pk).content.decode()


def test_venues_can_be_filtered_by_min_capacity(orm_data, squash):
    html = squash(Client().get("/venues/?min_capacity=3000"))
    assert "Городской парк" in html
    assert "Арена" not in html
    assert "Всего площадок: 1" in html
    assert 'value="3000"' in html


def test_min_capacity_filter_includes_boundary_value(orm_data, squash):
    assert "Всего площадок: 2" in squash(Client().get("/venues/?min_capacity=2000"))
    assert "Всего площадок: 1" in squash(Client().get("/venues/?min_capacity=2001"))


def test_filtered_venues_are_sorted_by_capacity(orm_data):
    Venue.objects.create(name="Аллея", capacity=3000)
    capacities = [v.capacity for v in Client().get("/venues/?min_capacity=0").context["venues"]]
    assert capacities == sorted(capacities)


def test_filter_with_no_matching_venues_shows_empty_message(orm_data):
    html = Client().get("/venues/?min_capacity=100000").content.decode()
    assert "Площадки не найдены." in html


def test_invalid_filter_value_is_reported_and_ignored(orm_data, squash):
    for value in ("abc", "-5", "1; DROP TABLE venues_venue", "99999999999999999999"):
        response = Client().get("/venues/", {"min_capacity": value})
        html = squash(response)
        assert response.status_code == 200, value
        assert "Вместимость должна быть целым неотрицательным числом." in html, value
        assert "Всего площадок: 2" in html, value
    assert Venue.objects.count() == 2


def test_search_by_name_ignores_case_for_cyrillic(orm_data, squash):
    # Слово «Городской» в названии начинается с заглавной буквы, «парк» — со строчной.
    for query in ("парк", "ПАРК", "Парк", "городской", "ГОРОДСКОЙ", "ородской"):
        html = squash(Client().get("/venues/", {"q": query}))
        assert "Городской парк" in html, query
        assert "Арена" not in html, query


def test_search_finds_capitalised_word_by_lowercase_query(orm_data, squash):
    html = squash(Client().get("/venues/", {"q": "арена"}))
    assert "Арена &lt;b&gt;" in html
    assert "Городской" not in html


def test_search_by_name_finds_nothing_for_unknown_text(orm_data, squash):
    html = squash(Client().get("/venues/", {"q": "несуществующая"}))
    assert "Площадки не найдены." in html
    assert 'value="несуществующая"' in html


def test_search_and_capacity_filter_work_together(orm_data, squash):
    both = squash(Client().get("/venues/", {"q": "а", "min_capacity": 3000}))
    assert "Городской парк" in both
    assert "Арена" not in both


def test_search_treats_wildcards_as_plain_text(orm_data, squash):
    html = squash(Client().get("/venues/", {"q": "%"}))
    assert "Площадки не найдены." in html


def test_search_text_helper_works_for_related_fields_and_several_fields(orm_data):
    from venue_service.search import search_text

    by_festival = search_text(Booking.objects.all(), ["festival__name"], "УЛИЧНОЙ")
    assert by_festival.count() == 2
    several = search_text(
        Booking.objects.all(), ["venue__name", "festival__organizer__name"], "арт-"
    )
    assert several.count() == 2  # организатор «АНО «Арт-Ивент»» относится к обоим бронированиям
    assert search_text(Booking.objects.all(), ["venue__name"], "арена").count() == 1
    assert search_text(Booking.objects.all(), ["venue__name"], "").count() == 2
