from django.test import Client


def test_venues_list_shows_venues_from_json(web_data):
    response = Client().get("/venues/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "Городской парк — вместимость 5000 мест" in html
    assert 'href="/venues/1/"' in html
    assert 'href="/venues/2/"' in html


def test_venues_list_escapes_html_in_names(web_data):
    html = Client().get("/venues/").content.decode()
    assert "Арена &lt;b&gt;" in html
    assert "Арена <b>" not in html


def test_venue_detail_shows_booked_venue_as_busy(web_data):
    response = Client().get("/venues/1/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "<title>Городской парк</title>" in html
    assert "<strong>Вместимость:</strong> 5000 мест" in html
    assert "bg-danger" in html
    assert "занята" in html


def test_venue_detail_shows_free_venue_as_available(web_data):
    html = Client().get("/venues/2/").content.decode()
    assert "bg-success" in html
    assert "свободна" in html


def test_venue_detail_unknown_id_returns_404(web_data):
    response = Client().get("/venues/999/")
    assert response.status_code == 404
    assert "Площадка не найдена" in response.content.decode()


def test_venue_pages_work_without_data_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Client().get("/venues/").status_code == 200
    assert Client().get("/venues/1/").status_code == 404
