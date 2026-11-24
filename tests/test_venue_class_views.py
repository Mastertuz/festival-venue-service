"""ПР13: VenueDetailView, VenueCreateView и VenueUpdateView (классовые представления)."""

from datetime import timedelta
from io import BytesIO

import pytest
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import resolve
from django.utils import timezone
from django.views.generic import CreateView, DetailView, UpdateView
from PIL import Image

import venues.views as venue_views
from bookings.models import Booking
from festivals.models import Festival, Organizer
from venue_service.utils import DataMixin
from venues.forms import VenueForm
from venues.models import Venue
from venues.views import VenueCreateView, VenueDetailView, VenueUpdateView

pytestmark = pytest.mark.django_db


def squashed(response):
    return " ".join(response.content.decode().split())


def photo(name="photo.png"):
    buffer = BytesIO()
    Image.new("RGB", (30, 20), "navy").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def venue(media_root):
    return Venue.objects.create(name="Городской парк", capacity=5000)


# --- классы и маршруты ------------------------------------------------------------------------


def test_function_views_are_replaced_by_classes():
    for name in ("venue_detail", "venue_create", "venue_update"):
        assert not hasattr(venue_views, name), name
    assert resolve("/venues/create/").func.view_class is VenueCreateView
    assert resolve("/venues/gorodskoi-park-1/").func.view_class is VenueDetailView
    assert resolve("/venues/gorodskoi-park-1/edit/").func.view_class is VenueUpdateView


def test_detail_view_is_configured_as_in_the_task():
    assert issubclass(VenueDetailView, DetailView)
    assert VenueDetailView.__mro__.index(DataMixin) < VenueDetailView.__mro__.index(DetailView)
    assert VenueDetailView.model is Venue
    assert VenueDetailView.context_object_name == "venue"
    assert VenueDetailView.slug_field == "slug" and VenueDetailView.slug_url_kwarg == "slug"


def test_form_views_are_configured_as_in_the_task():
    for view, parent in ((VenueCreateView, CreateView), (VenueUpdateView, UpdateView)):
        mro = view.__mro__
        assert issubclass(view, parent) and issubclass(view, SuccessMessageMixin)
        assert mro.index(DataMixin) < mro.index(SuccessMessageMixin) < mro.index(parent)
        assert view.form_class is VenueForm and view.model is Venue
        assert view.template_name == "venues/venue_form.html"


# --- карточка ----------------------------------------------------------------------------------


def test_detail_shows_venue_by_slug_with_dynamic_title_and_context(venue):
    organizer = Organizer.objects.create(name="Орг")
    festival = Festival.objects.create(
        name="Будущий",
        date=timezone.localdate() + timedelta(days=5),
        expected_attendees=10,
        organizer=organizer,
    )
    Booking.objects.create(festival=festival, venue=venue)
    response = Client().get(venue.get_absolute_url())
    assert response.status_code == 200
    assert response.context["venue"] == venue
    assert response.context["title"] == "Городской парк"
    assert response.context["available"] is True
    assert [b.festival.name for b in response.context["upcoming_bookings"]] == ["Будущий"]
    assert "<title>Городской парк – Festival Venue Service</title>" in squashed(response)


def test_detail_of_unknown_slug_gives_404(media_root):
    assert Client().get("/venues/net-takoi-1/").status_code == 404


# --- создание ----------------------------------------------------------------------------------


def test_create_get_and_post(media_root):
    client = Client()
    response = client.get("/venues/create/")
    assert response.status_code == 200
    assert response.context["title"] == "Добавление площадки"
    assert "<title>Добавление площадки – Festival Venue Service</title>" in squashed(response)

    response = client.post(
        "/venues/create/", {"name": "Новая", "capacity": "500", "image": photo("a.png")}
    )
    venue = Venue.objects.get(name="Новая")
    assert response.status_code == 302 and response["Location"] == venue.get_absolute_url()
    assert venue.image.name == "venues/a.png"
    assert "Площадка добавлена." in squashed(client.get(response["Location"]))


def test_create_invalid_data_is_not_saved(media_root):
    response = Client().post("/venues/create/", {"name": "", "capacity": "0"})
    assert response.status_code == 200
    assert set(response.context["form"].errors) == {"name", "capacity"}
    assert Venue.objects.count() == 0


# --- редактирование ------------------------------------------------------------------------------


def test_update_get_has_dynamic_context(venue):
    response = Client().get(f"/venues/{venue.slug}/edit/")
    assert response.status_code == 200
    assert response.context["venue"] == venue
    assert response.context["title"] == "Редактирование площадки"
    assert "Редактирование площадки «Городской парк»" in squashed(response)


def test_update_changes_fields_and_keeps_slug(venue):
    old_slug = venue.slug
    response = Client().post(
        f"/venues/{venue.slug}/edit/", {"name": "Переименованный парк", "capacity": "5500"}
    )
    venue.refresh_from_db()
    assert response.status_code == 302 and response["Location"] == f"/venues/{old_slug}/"
    assert (venue.name, venue.capacity, venue.slug) == ("Переименованный парк", 5500, old_slug)


def test_update_replaces_image_and_removes_old_file(venue, media_root):
    Client().post(
        f"/venues/{venue.slug}/edit/",
        {"name": venue.name, "capacity": "5000", "image": photo("1.png")},
    )
    Client().post(
        f"/venues/{venue.slug}/edit/",
        {"name": venue.name, "capacity": "5000", "image": photo("2.png")},
    )
    venue.refresh_from_db()
    assert venue.image.name == "venues/2.png"
    assert sorted(path.name for path in (media_root / "venues").iterdir()) == ["2.png"]


def test_update_can_clear_image_and_unknown_slug_gives_404(venue, media_root):
    Client().post(
        f"/venues/{venue.slug}/edit/", {"name": venue.name, "capacity": "5000", "image": photo()}
    )
    Client().post(
        f"/venues/{venue.slug}/edit/",
        {"name": venue.name, "capacity": "5000", "image-clear": "on"},
    )
    venue.refresh_from_db()
    assert not venue.image
    assert not list((media_root / "venues").iterdir())
    assert Client().get("/venues/net-takoi-1/edit/").status_code == 404


def test_update_invalid_data_keeps_old_image(venue, media_root):
    Client().post(
        f"/venues/{venue.slug}/edit/", {"name": venue.name, "capacity": "5000", "image": photo()}
    )
    venue.refresh_from_db()
    old = venue.image.name
    response = Client().post(
        f"/venues/{venue.slug}/edit/", {"name": "", "capacity": "1", "image": photo("new.png")}
    )
    assert response.status_code == 200
    venue.refresh_from_db()
    assert venue.image.name == old and (media_root / old).exists()


def test_forms_require_csrf_token(venue):
    client = Client(enforce_csrf_checks=True)
    assert client.post("/venues/create/", {"name": "x", "capacity": "1"}).status_code == 403
    assert client.post(f"/venues/{venue.slug}/edit/", {"name": "x"}).status_code == 403
