from django.conf import settings
from django.test import Client, RequestFactory
from django.test.utils import override_settings
from django.urls import get_callable

import homepage.views

# Собственную страницу 404 Django показывает только при DEBUG = False.
NO_DEBUG = override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])


def template_names(response):
    return [template.name for template in response.templates]


def test_handler404_is_configured_in_root_urlconf():
    from venue_service import urls

    assert urls.handler404 == "homepage.views.page_not_found"
    assert get_callable(urls.handler404) is homepage.views.page_not_found


def test_allowed_hosts_are_filled_for_local_machine():
    assert "localhost" in settings.ALLOWED_HOSTS
    assert "127.0.0.1" in settings.ALLOWED_HOSTS


@NO_DEBUG
def test_unknown_address_shows_custom_404_page(squash):
    response = Client().get("/nonexistent/")
    html = squash(response)
    assert response.status_code == 404
    assert "homepage/404.html" in template_names(response)
    assert "404 – страница не найдена" in html
    assert "Проверьте адрес или вернитесь на главную." in html
    assert "Not Found" not in html


@NO_DEBUG
def test_custom_404_page_uses_base_template_and_links_to_home(squash):
    response = Client().get("/nonexistent/")
    html = squash(response)
    assert "base.html" in template_names(response)
    assert "includes/navigation.html" in template_names(response)
    assert 'href="/" class="btn btn-primary"> На главную </a>' in html


@NO_DEBUG
def test_route_converter_mismatch_also_shows_custom_404_page():
    response = Client().get("/venues/abc/")
    assert response.status_code == 404
    assert "homepage/404.html" in template_names(response)


@NO_DEBUG
def test_missing_objects_keep_their_own_404_pages(web_data):
    venue = Client().get("/venues/999/")
    booking = Client().get("/bookings/999/")
    assert venue.status_code == booking.status_code == 404
    assert "Площадка не найдена" in venue.content.decode()
    assert "Бронирование не найдено" in booking.content.decode()
    assert "homepage/404.html" not in template_names(venue)


def test_page_not_found_view_returns_404_response():
    request = RequestFactory().get("/nonexistent/")
    response = homepage.views.page_not_found(request, Exception("not found"))
    assert response.status_code == 404
