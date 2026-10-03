from django.test import Client


def test_bookings_list_shows_bookings_with_status_badges(web_data):
    response = Client().get("/bookings/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "Фестиваль уличной музыки → Городской парк" in html
    assert 'href="/bookings/1/"' in html
    assert 'href="/bookings/2/"' in html
    assert 'class="badge bg-success">активно' in html
    assert 'class="badge bg-secondary">отменено' in html


def test_bookings_list_escapes_html_in_names(web_data):
    html = Client().get("/bookings/").content.decode()
    assert "Арена &lt;b&gt;" in html
    assert "Арена <b>" not in html


def test_booking_detail_shows_related_objects(web_data):
    response = Client().get("/bookings/1/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "<title>Бронирование №1</title>" in html
    assert "Фестиваль: Фестиваль уличной музыки" in html
    assert "Организатор: АНО «Арт-Ивент»" in html
    assert 'href="/venues/1/">Городской парк</a>' in html
    assert "активно" in html


def test_booking_detail_shows_cancelled_status(web_data):
    html = Client().get("/bookings/2/").content.decode()
    assert "bg-secondary" in html
    assert "отменено" in html


def test_booking_detail_unknown_id_returns_404(web_data):
    response = Client().get("/bookings/999/")
    assert response.status_code == 404
    assert "Бронирование не найдено" in response.content.decode()


def test_booking_pages_work_without_data_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Client().get("/bookings/").status_code == 200
    assert Client().get("/bookings/1/").status_code == 404
