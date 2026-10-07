from django.test import Client


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


def test_venues_list_shows_message_when_there_are_no_venues(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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


def test_venue_detail_without_data_files_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Client().get("/venues/1/").status_code == 404
