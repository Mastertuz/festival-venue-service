import pytest
from django.template.loader import render_to_string
from django.test import Client

from db.database import get_connection
from models.venues import Venue


def template_names(response):
    return [template.name for template in response.templates]


def test_venues_list_is_rendered_from_templates(web_data):
    response = Client().get("/venues/")
    names = template_names(response)
    assert response.status_code == 200
    assert "venues/venue_list.html" in names
    assert "venues/includes/venue_card.html" in names
    assert "base.html" in names


def test_venues_list_shows_venues_from_json(web_data, squash):
    html = squash(Client().get("/venues/"))
    assert "<title>Площадки – Festival Venue Service</title>" in html
    assert "Городской парк" in html
    assert "Вместимость: 5000 мест" in html
    assert 'href="/venues/1/"' in html
    assert 'href="/venues/2/"' in html


def test_venues_list_escapes_html_in_names(web_data):
    html = Client().get("/venues/").content.decode()
    assert "Арена &lt;b&gt;" in html
    assert "Арена <b>" not in html


def test_venues_list_shows_message_when_there_are_no_venues(empty_db):
    html = Client().get("/venues/").content.decode()
    assert "Площадки не найдены." in html


def test_venue_detail_shows_booked_venue_as_busy(web_data, squash):
    response = Client().get("/venues/1/")
    html = squash(response)
    assert response.status_code == 200
    assert "venues/venue_detail.html" in template_names(response)
    assert "<title> Городской парк – Festival Venue Service </title>" in html
    assert "<strong>Вместимость:</strong> 5000 мест" in html
    assert 'class="badge bg-danger">занята</span>' in html


def test_venue_detail_shows_free_venue_as_available(web_data, squash):
    html = squash(Client().get("/venues/2/"))
    assert 'class="badge bg-success">свободна</span>' in html


def test_venue_detail_has_link_back_to_list(web_data, squash):
    html = squash(Client().get("/venues/1/"))
    assert 'href="/venues/"' in html
    assert "← к списку площадок" in html


def test_venue_detail_unknown_id_returns_404(web_data):
    response = Client().get("/venues/999/")
    html = response.content.decode()
    assert response.status_code == 404
    assert "Площадка не найдена" in html
    assert "venues/venue_detail.html" in template_names(response)


def test_venue_detail_in_empty_database_returns_404(empty_db):
    assert Client().get("/venues/1/").status_code == 404


def test_venues_list_shows_count_with_length_filter(web_data, squash):
    html = squash(Client().get("/venues/"))
    assert "Всего площадок: 2" in html


def test_venue_card_uses_default_filter_for_empty_name():
    html = render_to_string("venues/includes/venue_card.html", {"venue": Venue(7, "", 100)})
    assert "Без названия" in html
    assert "Вместимость: 100 мест" in html


def test_venues_are_read_from_database_not_from_json(web_data):
    connection = get_connection()
    try:
        connection.execute("UPDATE venues SET name = 'Парк (обновлено)' WHERE id = 1")
        connection.commit()
    finally:
        connection.close()
    assert "Парк (обновлено)" in Client().get("/venues/").content.decode()
    assert "Парк (обновлено)" in Client().get("/venues/1/").content.decode()


def test_venues_can_be_filtered_by_min_capacity(web_data, squash):
    html = squash(Client().get("/venues/?min_capacity=3000"))
    assert "Городской парк" in html
    assert "Арена" not in html
    assert "Всего площадок: 1" in html
    assert 'value="3000"' in html


def test_min_capacity_filter_includes_boundary_value(web_data, squash):
    html = squash(Client().get("/venues/?min_capacity=2000"))
    assert "Всего площадок: 2" in html


def test_filter_with_no_matching_venues_shows_empty_message(web_data):
    html = Client().get("/venues/?min_capacity=100000").content.decode()
    assert "Площадки не найдены." in html


def test_invalid_filter_value_is_reported_and_ignored(web_data, squash):
    for value in ("abc", "-5", "1; DROP TABLE venues"):
        response = Client().get("/venues/", {"min_capacity": value})
        html = squash(response)
        assert response.status_code == 200, value
        assert "Вместимость должна быть целым неотрицательным числом." in html, value
        assert "Всего площадок: 2" in html, value
    connection = get_connection()
    try:
        assert connection.execute("SELECT COUNT(*) FROM venues").fetchone()[0] == 2
    finally:
        connection.close()


def test_pages_report_missing_database_clearly(db_path):
    with pytest.raises(FileNotFoundError):
        Client().get("/venues/")
