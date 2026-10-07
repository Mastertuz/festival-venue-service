from django.test import Client


def template_names(response):
    return [template.name for template in response.templates]


def test_index_is_rendered_from_templates():
    response = Client().get("/")
    names = template_names(response)
    assert response.status_code == 200
    assert "homepage/index.html" in names
    assert "base.html" in names
    assert "includes/navigation.html" in names


def test_index_returns_page_with_bootstrap_and_navigation(squash):
    response = Client().get("/")
    html = squash(response)
    assert "<title>Главная – Festival Venue Service</title>" in html
    assert "bootstrap@5.3.3" in html
    assert 'name="viewport"' in html
    assert 'href="/venues/"' in html
    assert 'href="/bookings/"' in html


def test_index_has_links_to_sections(squash):
    html = squash(Client().get("/"))
    assert 'class="btn btn-primary me-2"> Площадки </a>' in html
    assert 'class="btn btn-secondary"> Бронирования </a>' in html
