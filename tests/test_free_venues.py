from datetime import date, timedelta

from django.test import Client

from db.database import get_connection
from venues.views import FREE_VENUES_SQL


def template_names(response):
    return [template.name for template in response.templates]


def free_names(response):
    return response.content.decode()


def test_search_page_shows_only_form_without_parameters(web_data, squash):
    response = Client().get("/venues/available/")
    html = squash(response)
    assert response.status_code == 200
    assert "venues/venue_available.html" in template_names(response)
    assert 'name="date"' in html
    assert 'name="attendees"' in html
    assert "Дата:" not in html
    assert "свободных площадок нет" not in html


def test_venue_booked_on_date_is_excluded(web_data, squash):
    today = date.today().isoformat()
    html = squash(Client().get("/venues/available/", {"date": today}))
    assert "Арена &lt;b&gt;" in html  # отменённое бронирование площадку не блокирует
    assert "Городской парк" not in html  # на эту дату у парка активное бронирование
    assert f"Дата: {date.today().strftime('%d.%m.%Y')}" in html


def test_all_venues_are_free_on_another_date(web_data, squash):
    other = (date.today() + timedelta(days=100)).isoformat()
    html = squash(Client().get("/venues/available/", {"date": other}))
    assert "Городской парк" in html
    assert "Арена &lt;b&gt;" in html


def test_attendees_limit_filters_by_capacity(web_data, squash):
    other = (date.today() + timedelta(days=100)).isoformat()
    html = squash(Client().get("/venues/available/", {"date": other, "attendees": 3000}))
    assert "Городской парк" in html
    assert "Арена" not in html
    assert "посетителей: 3000" in html


def test_search_without_results_shows_message(web_data):
    html = free_names(
        Client().get("/venues/available/", {"date": date.today().isoformat(), "attendees": 3000})
    )
    assert "На выбранную дату свободных площадок нет." in html


def test_search_in_empty_database_is_not_an_error(empty_db):
    response = Client().get("/venues/available/", {"date": "2026-11-07"})
    assert response.status_code == 200
    assert "На выбранную дату свободных площадок нет." in response.content.decode()


def test_invalid_date_is_reported_without_search(web_data, squash):
    for value in ("2026-13-45", "завтра", "2026-11-07' OR '1'='1"):
        html = squash(Client().get("/venues/available/", {"date": value}))
        assert "Укажите дату в формате ГГГГ-ММ-ДД." in html, value
        assert "Дата:" not in html, value


def test_invalid_attendees_is_reported_without_search(web_data, squash):
    html = squash(Client().get("/venues/available/", {"date": "2026-11-07", "attendees": "много"}))
    assert "Число посетителей должно быть целым неотрицательным числом." in html
    assert "свободных площадок нет" not in html


def test_search_form_keeps_entered_values(web_data, squash):
    html = squash(Client().get("/venues/available/", {"date": "2026-11-07", "attendees": 10}))
    assert 'value="2026-11-07"' in html
    assert 'value="10"' in html


def test_sql_parameters_are_not_interpreted_as_sql(web_data):
    """Строка-«инъекция» в параметре — обычное значение, а не часть запроса."""
    connection = get_connection()
    try:
        payload = "2026-01-01' OR 1=1 --"
        rows = connection.execute(FREE_VENUES_SQL, [0, payload]).fetchall()
        # Подстановка в текст запроса исключила бы все площадки; параметр совпадений не даёт.
        assert len(rows) == 2
        assert connection.execute("SELECT COUNT(*) FROM venues").fetchone()[0] == 2
    finally:
        connection.close()


def test_search_page_is_linked_from_venue_list(web_data, squash):
    html = squash(Client().get("/venues/"))
    assert 'href="/venues/available/"' in html


def test_available_route_is_not_taken_for_venue_id(web_data):
    assert Client().get("/venues/available/").status_code == 200
    assert Client().get("/venues/1/").status_code == 200
