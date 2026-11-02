"""ПР10: slug площадки, get_absolute_url(), вычисляемое поле is_large и контекстный процессор."""

import importlib

import pytest
from django.apps import apps
from django.db import IntegrityError, connection, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

from venues.models import LARGE_VENUE_CAPACITY, Venue

pytestmark = pytest.mark.django_db


def test_slug_is_transliterated_and_ends_with_primary_key(orm_data):
    park, arena = orm_data["park"], orm_data["arena"]
    assert park.slug == f"gorodskoi-park-{park.pk}"
    assert arena.slug.startswith("arena-b") and arena.slug.endswith(f"-{arena.pk}")


def test_slug_contains_only_latin_letters_digits_and_hyphens(db):
    venue = Venue.objects.create(name="Концертный зал «Арена» №1!", capacity=100)
    assert venue.slug == f"kontsertnyi-zal-arena-no-1-{venue.pk}"
    assert all(char.isascii() and (char.isalnum() or char == "-") for char in venue.slug)


def test_venues_with_equal_names_get_different_slugs(db):
    first = Venue.objects.create(name="Парк", capacity=10)
    second = Venue.objects.create(name="Парк", capacity=20)
    assert first.slug != second.slug


def test_slug_without_letters_falls_back_to_default(db):
    venue = Venue.objects.create(name="***", capacity=10)
    assert venue.slug == f"venue-{venue.pk}"


def test_slug_is_not_changed_by_rename_or_repeated_save(orm_data):
    park = orm_data["park"]
    old_slug = park.slug
    park.name = "Новое название"
    park.save()
    park.refresh_from_db()
    assert park.slug == old_slug


def test_slug_is_unique_in_database(orm_data):
    clone = Venue(name="Другая", capacity=10, slug=orm_data["park"].slug)
    with pytest.raises(IntegrityError), transaction.atomic():
        clone.save()


def test_slug_is_not_editable_in_forms():
    assert Venue._meta.get_field("slug").editable is False


def test_get_absolute_url_uses_named_route(orm_data):
    park = orm_data["park"]
    assert park.get_absolute_url() == f"/venues/{park.slug}/"
    assert park.get_absolute_url() == reverse("venues:detail", kwargs={"slug": park.slug})
    assert resolve(park.get_absolute_url()).view_name == "venues:detail"


def test_detail_page_opens_by_slug(orm_data):
    response = Client().get(orm_data["park"].get_absolute_url())
    assert response.status_code == 200
    assert response.context["venue"] == orm_data["park"]


def test_old_numeric_address_redirects_permanently_to_slug_address(orm_data):
    response = Client().get("/venues/%d/" % orm_data["park"].pk)
    assert response.status_code == 301
    assert response["Location"] == orm_data["park"].get_absolute_url()


def test_unknown_slug_and_unknown_id_return_404(orm_data):
    assert Client().get("/venues/net-takoi-ploshchadki/").status_code == 404
    assert Client().get("/venues/999999/").status_code == 404


def test_available_route_is_not_taken_by_slug_route(orm_data):
    assert resolve("/venues/available/").view_name == "venues:available"


def test_list_cards_link_to_slug_addresses(orm_data):
    html = " ".join(Client().get("/venues/").content.decode().split())
    assert 'href="%s"' % orm_data["park"].get_absolute_url() in html
    assert 'href="/venues/%d/"' % orm_data["park"].pk not in html


def test_booking_page_links_to_venue_by_slug(orm_data):
    html = " ".join(Client().get("/bookings/%d/" % orm_data["active"].pk).content.decode().split())
    assert 'href="%s"' % orm_data["park"].get_absolute_url() in html


def test_populate_migration_function_restores_empty_slugs(orm_data):
    module = importlib.import_module("venues.migrations.0005_populate_venue_slugs")
    park = orm_data["park"]
    original = park.slug
    Venue.objects.filter(pk=park.pk).update(slug="")
    module.populate_venue_slugs(apps, None)
    park.refresh_from_db()
    assert park.slug == original


# --- GeneratedField is_large ---


def test_is_large_is_computed_by_database_from_capacity(orm_data):
    assert LARGE_VENUE_CAPACITY == 3000
    assert orm_data["park"].is_large is True  # 5000
    assert orm_data["arena"].is_large is False  # 2000


def test_is_large_is_recalculated_after_capacity_change(orm_data):
    arena = orm_data["arena"]
    arena.capacity = 3000
    arena.save()
    arena.refresh_from_db()
    assert arena.is_large is True
    arena.capacity = 2999
    arena.save()
    arena.refresh_from_db()
    assert arena.is_large is False


def test_is_large_can_not_be_set_manually_and_is_not_editable():
    field = Venue._meta.get_field("is_large")
    assert field.editable is False
    assert field.generated is True
    assert field.db_persist is True


def test_is_large_is_a_stored_generated_column_in_sqlite():
    with connection.cursor() as cursor:
        cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'venues_venue'")
        sql = cursor.fetchone()[0]
    assert "GENERATED ALWAYS" in sql and "STORED" in sql


def test_is_large_can_be_used_in_queries(orm_data):
    assert list(Venue.objects.filter(is_large=True)) == [orm_data["park"]]


# --- Контекстный процессор site_context ---


def test_context_processor_is_registered_in_settings():
    from django.conf import settings

    processors = settings.TEMPLATES[0]["OPTIONS"]["context_processors"]
    assert "homepage.context_processors.site_context" in processors


@pytest.mark.parametrize("url", ["/", "/venues/", "/bookings/", "/bookings/statistics/"])
def test_site_name_and_venues_count_are_available_on_pages(orm_data, url):
    response = Client().get(url)
    assert response.context["site_name"] == "Festival Venue Service"
    assert response.context["venues_count"] == 2


def test_navigation_shows_actual_venues_count(orm_data):
    html = " ".join(Client().get("/").content.decode().split())
    assert ">Площадки (2)</a>" in html
    Venue.objects.create(name="Третья", capacity=10)
    html = " ".join(Client().get("/").content.decode().split())
    assert ">Площадки (3)</a>" in html


def test_context_processor_makes_one_count_query(db):
    from django.test import RequestFactory

    from homepage.context_processors import site_context

    with CaptureQueriesContext(connection) as queries:
        data = site_context(RequestFactory().get("/"))
    assert len(queries) == 1
    assert "COUNT" in queries[0]["sql"].upper()
    assert data == {"site_name": "Festival Venue Service", "venues_count": 0}


def test_base_template_uses_site_name_in_logo_and_footer(orm_data):
    html = " ".join(Client().get("/").content.decode().split())
    assert 'alt="Festival Venue Service"' in html
    assert '<span id="current-year"></span> Festival Venue Service' in html
