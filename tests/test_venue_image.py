"""ПР11: загрузка и отображение изображений площадок (ImageField, форма, админ-панель)."""

import os
from io import BytesIO

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import Client
from PIL import Image

from venues.forms import VenueForm
from venues.models import Venue
from venues.validators import MAX_IMAGE_SIZE, validate_image_size

pytestmark = pytest.mark.django_db

CREATE = "/venues/create/"


def squashed(response):
    return " ".join(response.content.decode().split())


def image_bytes(size=(40, 30), fmt="PNG"):
    buffer = BytesIO()
    Image.new("RGB", size, "teal").save(buffer, fmt)
    return buffer.getvalue()


def image_file(name="photo.png", **kwargs):
    return SimpleUploadedFile(name, image_bytes(**kwargs), content_type="image/png")


def big_image_file():
    """Корректное изображение размером больше предела: шум почти не сжимается."""
    noise = Image.frombytes("RGB", (1000, 1000), os.urandom(3_000_000))
    buffer = BytesIO()
    noise.save(buffer, "PNG", compress_level=0)
    assert buffer.tell() > MAX_IMAGE_SIZE
    return SimpleUploadedFile("big.png", buffer.getvalue(), content_type="image/png")


def venue_data(**extra):
    return {"name": "Новая площадка", "capacity": "1500", **extra}


def stored_files(media_root):
    venues_dir = media_root / "venues"
    return sorted(path.name for path in venues_dir.iterdir()) if venues_dir.exists() else []


@pytest.fixture
def venue(media_root):
    """Площадка с загруженным изображением."""
    venue = Venue(name="Парк с фото", capacity=3000)
    venue.image.save("park.png", image_file("park.png"), save=False)
    venue.save()
    return venue


# --- модель, настройки и проверка размера ---------------------------------------


def test_image_field_is_optional_and_uploads_to_venues_directory():
    field = Venue._meta.get_field("image")
    assert isinstance(field, models.ImageField)
    assert field.upload_to == "venues/"
    assert field.blank is True and field.null is True
    assert validate_image_size in field.validators


def test_media_settings(settings):
    assert settings.MEDIA_URL == "/media/"
    assert settings.MEDIA_ROOT.name == "media"
    assert settings.MEDIA_ROOT != settings.STATIC_ROOT if hasattr(settings, "STATIC_ROOT") else True


def test_venue_without_image_has_empty_field(db):
    venue = Venue.objects.create(name="Без фото", capacity=10)
    assert not venue.image
    assert venue.image.name in (None, "")


def test_size_validator_accepts_limit_and_rejects_larger_file():
    class Fake:
        def __init__(self, size):
            self.size = size

    validate_image_size(Fake(MAX_IMAGE_SIZE))
    with pytest.raises(ValidationError, match="не должен превышать 2 МБ"):
        validate_image_size(Fake(MAX_IMAGE_SIZE + 1))


# --- форма ----------------------------------------------------------------------


def test_form_is_a_model_form_with_explicit_fields_and_without_service_fields():
    assert issubclass(VenueForm, forms.ModelForm)
    assert VenueForm.Meta.fields == ["name", "capacity", "image"]
    fields = VenueForm().fields
    assert "slug" not in fields and "is_large" not in fields


def test_form_labels_and_widgets():
    form = VenueForm()
    assert form.fields["image"].label == "Изображение"
    assert form.fields["image"].required is False
    assert form.fields["image"].widget.attrs["accept"] == "image/*"
    assert form.fields["image"].widget.attrs["class"] == "form-control"
    assert form.fields["capacity"].widget.attrs["min"] == 1


def test_form_accepts_valid_data_with_image(media_root):
    form = VenueForm(venue_data(), {"image": image_file()})
    assert form.is_valid(), form.errors


def test_form_rejects_zero_capacity_with_own_message():
    form = VenueForm(venue_data(capacity="0"))
    assert not form.is_valid()
    assert form.errors["capacity"] == ["Вместимость должна быть больше нуля."]


def test_form_rejects_negative_and_missing_values():
    assert "capacity" in VenueForm(venue_data(capacity="-5")).errors
    form = VenueForm({})
    assert set(form.errors) == {"name", "capacity"}  # изображение не обязательно


def test_form_rejects_file_that_is_not_an_image(media_root):
    fake = SimpleUploadedFile("photo.png", "это не изображение".encode(), content_type="image/png")
    form = VenueForm(venue_data(), {"image": fake})
    assert not form.is_valid()
    assert list(form.errors) == ["image"]


def test_form_rejects_image_with_wrong_extension(media_root):
    wrong = SimpleUploadedFile("notes.txt", image_bytes(), content_type="text/plain")
    form = VenueForm(venue_data(), {"image": wrong})
    assert not form.is_valid()
    assert list(form.errors) == ["image"]


def test_form_rejects_too_large_image(media_root):
    form = VenueForm(venue_data(), {"image": big_image_file()})
    assert not form.is_valid()
    assert form.errors["image"] == ["Размер изображения не должен превышать 2 МБ."]


# --- создание площадки -------------------------------------------------------------


def test_create_page_has_multipart_form_with_csrf_and_file_field(media_root):
    response = Client().get(CREATE)
    html = squashed(response)
    assert response.status_code == 200
    assert "venues/venue_form.html" in [t.name for t in response.templates]
    assert not response.context["form"].is_bound
    assert 'enctype="multipart/form-data"' in html
    assert 'name="csrfmiddlewaretoken"' in html
    assert 'type="file"' in html and 'name="image"' in html
    assert "Добавление площадки" in html and "Добавить площадку" in html


def test_create_with_image_saves_file_and_path(media_root):
    response = Client().post(CREATE, venue_data(image=image_file("scene.png")))
    venue = Venue.objects.get(name="Новая площадка")
    assert response.status_code == 302 and response["Location"] == venue.get_absolute_url()
    assert venue.image.name == "venues/scene.png"
    assert (media_root / "venues" / "scene.png").exists()
    assert venue.slug.startswith("novaia-ploshchadka-")


def test_created_image_is_a_real_image_file(media_root):
    Client().post(CREATE, venue_data(image=image_file("scene.png", size=(64, 48))))
    with Image.open(media_root / "venues" / "scene.png") as saved:
        assert saved.size == (64, 48)


def test_create_without_image_is_allowed(media_root):
    response = Client().post(CREATE, venue_data())
    venue = Venue.objects.get(name="Новая площадка")
    assert response.status_code == 302
    assert not venue.image
    assert stored_files(media_root) == []


def test_detail_page_shows_uploaded_image_or_placeholder(media_root):
    Client().post(CREATE, venue_data(image=image_file("scene.png")))
    venue = Venue.objects.get()
    html = squashed(Client().get(venue.get_absolute_url()))
    assert '<img src="/media/venues/scene.png"' in html
    assert f'alt="{venue.name}"' in html
    assert "Изображение не загружено." not in html

    plain = Venue.objects.create(name="Без фото", capacity=10)
    assert "Изображение не загружено." in squashed(Client().get(plain.get_absolute_url()))


def test_success_message_is_shown_after_creation(media_root):
    response = Client().post(CREATE, venue_data(), follow=True)
    assert "Площадка добавлена." in squashed(response)


@pytest.mark.parametrize(
    "data",
    [
        {"name": "", "capacity": "100"},
        {"name": "Площадка", "capacity": "0"},
        {"name": "Площадка", "capacity": "много"},
    ],
)
def test_invalid_data_is_not_saved_and_form_is_shown_again(media_root, data):
    response = Client().post(CREATE, {**data, "image": image_file()})
    assert response.status_code == 200
    assert response.context["form"].errors
    assert Venue.objects.count() == 0
    assert stored_files(media_root) == []


def test_invalid_image_is_reported_and_nothing_is_saved(media_root):
    fake = SimpleUploadedFile("photo.png", "это не изображение".encode(), content_type="image/png")
    response = Client().post(CREATE, venue_data(image=fake))
    assert response.status_code == 200
    assert "image" in response.context["form"].errors
    assert Venue.objects.count() == 0
    assert stored_files(media_root) == []


def test_too_large_image_is_reported_in_the_page(media_root):
    response = Client().post(CREATE, venue_data(image=big_image_file()))
    assert "Размер изображения не должен превышать 2 МБ." in squashed(response)
    assert Venue.objects.count() == 0


def test_files_with_same_name_get_different_stored_names(media_root):
    Client().post(CREATE, venue_data(name="Первая", image=image_file("same.png")))
    Client().post(CREATE, venue_data(name="Вторая", image=image_file("same.png")))
    names = {venue.image.name for venue in Venue.objects.all()}
    assert len(names) == 2 and len(stored_files(media_root)) == 2


def test_create_without_csrf_token_is_forbidden(media_root):
    client = Client(enforce_csrf_checks=True)
    assert client.post(CREATE, venue_data()).status_code == 403
    assert Venue.objects.count() == 0


def test_create_page_is_not_confused_with_venue_slug_routes(media_root):
    from django.urls import resolve, reverse

    assert reverse("venues:create") == CREATE
    assert resolve(CREATE).url_name == "create"
    assert Client().get("/venues/available/").status_code == 200


# --- редактирование и замена изображения ----------------------------------------------


def edit_url(venue):
    return f"/venues/{venue.slug}/edit/"


def test_edit_page_is_filled_and_shows_current_image(venue):
    response = Client().get(edit_url(venue))
    html = squashed(response)
    assert response.status_code == 200
    assert response.context["form"].instance == venue
    assert 'value="Парк с фото"' in html and 'value="3000"' in html
    assert venue.image.name in html
    assert "Сохранить изменения" in html


def test_edit_of_unknown_venue_gives_404(media_root):
    assert Client().get("/venues/net-takoi-1/edit/").status_code == 404
    assert Client().post("/venues/net-takoi-1/edit/", venue_data()).status_code == 404


def test_edit_changes_fields_but_keeps_slug_and_image(venue):
    old_slug, old_image = venue.slug, venue.image.name
    response = Client().post(edit_url(venue), {"name": "Переименованный парк", "capacity": "3500"})
    venue.refresh_from_db()
    assert response.status_code == 302
    assert (venue.name, venue.capacity) == ("Переименованный парк", 3500)
    assert venue.slug == old_slug and venue.image.name == old_image


def test_replacing_image_removes_the_old_file(venue, media_root):
    old_name = venue.image.name
    assert (media_root / old_name).exists()
    Client().post(edit_url(venue), {**venue_data(), "image": image_file("new.png")})
    venue.refresh_from_db()
    assert venue.image.name == "venues/new.png"
    assert (media_root / "venues" / "new.png").exists()
    assert not (media_root / old_name).exists()
    assert stored_files(media_root) == ["new.png"]


def test_image_can_be_cleared_with_checkbox(venue, media_root):
    Client().post(edit_url(venue), {**venue_data(), "image-clear": "on"})
    venue.refresh_from_db()
    assert not venue.image
    assert stored_files(media_root) == []


def test_invalid_edit_keeps_old_image_and_file(venue, media_root):
    old_name = venue.image.name
    response = Client().post(edit_url(venue), {"name": "", "capacity": "5", "image": image_file()})
    assert response.status_code == 200
    venue.refresh_from_db()
    assert venue.image.name == old_name and venue.name == "Парк с фото"
    assert (media_root / old_name).exists()


def test_detail_page_links_to_edit_form(venue):
    assert edit_url(venue) in squashed(Client().get(venue.get_absolute_url()))


def test_list_links_to_create_and_card_shows_image(venue):
    response = Client().get("/venues/")
    html = squashed(response)
    assert CREATE in html
    assert f'src="{venue.image.url}"' in html


# --- административная панель ---------------------------------------------------------


ADMIN_INLINE = {
    "bookings-TOTAL_FORMS": "0",
    "bookings-INITIAL_FORMS": "0",
    "bookings-MIN_NUM_FORMS": "0",
    "bookings-MAX_NUM_FORMS": "1000",
}


def test_admin_change_page_has_file_field_and_multipart_form(admin_client, venue):
    html = squashed(admin_client.get(f"/admin/venues/venue/{venue.pk}/change/"))
    assert 'enctype="multipart/form-data"' in html
    assert 'type="file"' in html and 'name="image"' in html
    assert f'<img src="{venue.image.url}"' in html  # предпросмотр загруженного изображения


def test_admin_uploads_image_for_existing_venue(admin_client, media_root):
    venue = Venue.objects.create(name="Без фото", capacity=100)
    response = admin_client.post(
        f"/admin/venues/venue/{venue.pk}/change/",
        {"name": venue.name, "capacity": "100", "image": image_file("admin.png"), **ADMIN_INLINE},
    )
    venue.refresh_from_db()
    assert response.status_code == 302
    assert venue.image.name == "venues/admin.png"
    assert (media_root / "venues" / "admin.png").exists()


def test_admin_replaces_image_and_site_shows_new_one(admin_client, media_root):
    venue = Venue.objects.create(name="С фото", capacity=100)
    for filename in ("first.png", "second.png"):
        admin_client.post(
            f"/admin/venues/venue/{venue.pk}/change/",
            {"name": venue.name, "capacity": "100", "image": image_file(filename), **ADMIN_INLINE},
        )
    venue.refresh_from_db()
    assert venue.image.name == "venues/second.png"
    assert 'src="/media/venues/second.png"' in squashed(Client().get(venue.get_absolute_url()))


def test_admin_changelist_has_image_column(admin_client, venue):
    response = admin_client.get("/admin/venues/venue/")
    assert "Есть изображение" in squashed(response)
