from django.test import Client


def test_index_returns_page_with_bootstrap_and_navigation():
    response = Client().get("/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "<title>Festival Venue Service</title>" in html
    assert "bootstrap@5.3.3" in html
    assert 'name="viewport"' in html
    assert 'href="/venues/"' in html
    assert 'href="/bookings/"' in html


def test_index_has_links_to_sections():
    html = Client().get("/").content.decode()
    assert 'class="btn btn-primary me-2">Площадки</a>' in html
    assert 'class="btn btn-secondary">Бронирования</a>' in html
