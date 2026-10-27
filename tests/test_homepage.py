from datetime import date, timedelta

import pytest
from django.test import Client

from festivals.models import Festival

pytestmark = pytest.mark.django_db


def template_names(response):
    return [template.name for template in response.templates]


def test_index_is_rendered_from_templates(orm_data):
    response = Client().get("/")
    names = template_names(response)
    assert response.status_code == 200
    assert "homepage/index.html" in names
    assert "base.html" in names
    assert "includes/navigation.html" in names


def test_index_returns_page_with_bootstrap_and_navigation(orm_data, squash):
    html = squash(Client().get("/"))
    assert "<title>Главная – Festival Venue Service</title>" in html
    assert "bootstrap@5.3.3" in html
    assert 'name="viewport"' in html
    assert 'href="/venues/"' in html
    assert 'href="/bookings/"' in html


def test_index_has_links_to_sections(orm_data, squash):
    html = squash(Client().get("/"))
    assert 'class="btn btn-primary me-2"> Площадки </a>' in html
    assert 'class="btn btn-secondary"> Бронирования </a>' in html


def test_index_shows_active_bookings_count_from_database(orm_data, squash):
    assert "Активных бронирований: 1" in squash(Client().get("/"))


def test_index_shows_next_festivals_with_formatted_date(orm_data, squash):
    html = squash(Client().get("/"))
    assert "Фестиваль уличной музыки — АНО «Арт-Ивент»" in html
    assert date.today().strftime("%d.%m.%Y") in html


def test_index_shows_at_most_three_nearest_festivals(orm_data):
    for days in (5, 10, 15):
        Festival.objects.create(
            name=f"Будущий {days}",
            date=date.today() + timedelta(days=days),
            expected_attendees=10,
            organizer=orm_data["organizer"],
        )
    festivals = list(Client().get("/").context["next_festivals"])
    assert [f.name for f in festivals] == [
        "Фестиваль уличной музыки",
        "Будущий 5",
        "Будущий 10",
    ]


def test_past_festivals_are_not_shown_as_next(orm_data, squash):
    Festival.objects.create(
        name="Давний",
        date=date.today() - timedelta(days=1),
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )
    assert "Давний" not in squash(Client().get("/"))


def test_index_in_empty_database_shows_placeholders(db, squash):
    html = squash(Client().get("/"))
    assert "Активных бронирований: 0" in html
    assert "Ближайших фестивалей нет." in html


def test_index_uses_two_queries(orm_data, django_assert_num_queries):
    """Счётчик и ближайшие фестивали с организаторами — два запроса (select_related)."""
    with django_assert_num_queries(2):
        response = Client().get("/")
        response.content  # noqa: B018 — шаблон обращается к festival.organizer.name
