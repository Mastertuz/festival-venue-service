from django.test import Client


def template_names(response):
    return [template.name for template in response.templates]


def test_bookings_list_is_rendered_from_templates(web_data):
    response = Client().get("/bookings/")
    names = template_names(response)
    assert response.status_code == 200
    assert "bookings/booking_list.html" in names
    assert "bookings/includes/booking_status.html" in names
    assert "base.html" in names


def test_bookings_list_shows_bookings_with_status_badges(web_data, squash):
    html = squash(Client().get("/bookings/"))
    assert "<title>Бронирования – Festival Venue Service</title>" in html
    assert "Фестиваль уличной музыки → Городской парк" in html
    assert 'href="/bookings/1/"' in html
    assert 'href="/bookings/2/"' in html
    assert "badge bg-success booking-status booking-status-active" in html
    assert "badge bg-secondary booking-status booking-status-cancelled" in html
    assert "Активно" in html
    assert "Отменено" in html


def test_bookings_list_escapes_html_in_names(web_data):
    html = Client().get("/bookings/").content.decode()
    assert "Арена &lt;b&gt;" in html
    assert "Арена <b>" not in html


def test_bookings_list_shows_message_when_there_are_no_bookings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    html = Client().get("/bookings/").content.decode()
    assert "Бронирования не найдены." in html


def test_booking_detail_shows_related_objects(web_data, squash):
    response = Client().get("/bookings/1/")
    html = squash(response)
    assert response.status_code == 200
    assert "bookings/booking_detail.html" in template_names(response)
    assert "<title> Бронирование №1 – Festival Venue Service </title>" in html
    assert "<strong>Фестиваль:</strong> Фестиваль уличной музыки" in html
    assert "<strong>Организатор:</strong> АНО «Арт-Ивент»" in html
    assert 'href="/venues/1/"> Городской парк </a>' in html
    assert "Активно" in html


def test_booking_detail_shows_cancelled_status(web_data, squash):
    html = squash(Client().get("/bookings/2/"))
    assert "booking-status-cancelled" in html
    assert "Отменено" in html


def test_booking_detail_has_link_back_to_list(web_data, squash):
    html = squash(Client().get("/bookings/1/"))
    assert 'href="/bookings/"' in html
    assert "← к списку бронирований" in html


def test_booking_detail_unknown_id_returns_404(web_data):
    response = Client().get("/bookings/999/")
    assert response.status_code == 404
    assert "Бронирование не найдено" in response.content.decode()
    assert "bookings/booking_detail.html" in template_names(response)


def test_booking_detail_without_data_files_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Client().get("/bookings/1/").status_code == 404
