from django.test import Client

from db.database import get_connection


def template_names(response):
    return [template.name for template in response.templates]


def add_active_bookings_for_first_venue(count):
    """Добавить фестивали и активные бронирования на площадку 1 (для проверки HAVING)."""
    connection = get_connection()
    try:
        for number in range(count):
            festival_id = 100 + number
            connection.execute(
                "INSERT INTO festivals (id, name, date, expected_attendees, organizer_id) "
                "VALUES (?, ?, ?, ?, 1)",
                [festival_id, f"Доп. фестиваль {number}", f"2030-01-{10 + number}", 100],
            )
            connection.execute(
                "INSERT INTO bookings (id, festival_id, venue_id) VALUES (?, ?, 1)",
                [200 + number, festival_id],
            )
        connection.commit()
    finally:
        connection.close()


def test_statistics_page_is_rendered_from_template(web_data):
    response = Client().get("/bookings/statistics/")
    assert response.status_code == 200
    assert "bookings/statistics.html" in template_names(response)
    assert "base.html" in template_names(response)


def test_statistics_shows_aggregates(web_data, squash):
    html = squash(Client().get("/bookings/statistics/"))
    assert "Активных бронирований" in html
    assert '<div class="fs-3">1</div>' in html  # активных бронирований
    assert "2000 – 5000" in html  # MIN и MAX вместимости
    assert "3500,0" in html  # AVG вместимости (в русской локали — десятичная запятая)


def test_statistics_counts_bookings_by_venue_with_zero_for_unbooked(web_data, squash):
    html = squash(Client().get("/bookings/statistics/"))
    assert "<td>Городской парк</td> <td>1</td>" in html
    # у площадки есть только отменённое бронирование: LEFT JOIN сохраняет её со значением 0
    assert "<td>Арена &lt;b&gt;</td> <td>0</td>" in html


def test_statistics_groups_festivals_by_organizer(web_data, squash):
    html = squash(Client().get("/bookings/statistics/"))
    assert "<td>АНО «Арт-Ивент»</td> <td>1</td> <td>4500</td>" in html


def test_popular_venues_use_having_threshold(web_data, squash):
    assert "Таких площадок нет." in squash(Client().get("/bookings/statistics/"))
    add_active_bookings_for_first_venue(2)  # вместе с исходным — 3 активных бронирования
    html = squash(Client().get("/bookings/statistics/"))
    assert "более 2 бронирований" in html
    assert "<span>Городской парк</span> <span>3</span>" in html
    assert "Таких площадок нет." not in html


def test_statistics_in_empty_database_shows_placeholders(empty_db, squash):
    response = Client().get("/bookings/statistics/")
    html = squash(response)
    assert response.status_code == 200
    assert "Данные отсутствуют." in html
    assert "— – —" in html  # MIN и MAX отсутствуют (NULL)


def test_statistics_is_in_navigation(web_data, squash):
    for url in ("/", "/venues/", "/bookings/", "/bookings/statistics/"):
        assert 'href="/bookings/statistics/">Статистика</a>' in squash(Client().get(url)), url


def test_statistics_route_is_not_taken_for_booking_id(web_data):
    assert Client().get("/bookings/statistics/").status_code == 200
    assert Client().get("/bookings/1/").status_code == 200
