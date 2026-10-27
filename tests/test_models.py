from datetime import date, timedelta

import pytest
from django.contrib import admin
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from bookings.models import Booking
from festivals.models import Festival, Organizer
from venues.models import Venue

pytestmark = pytest.mark.django_db


def test_str_returns_names(orm_data):
    assert str(orm_data["organizer"]) == "АНО «Арт-Ивент»"
    assert str(orm_data["park"]) == "Городской парк"
    assert str(orm_data["festival"]) == "Фестиваль уличной музыки"
    assert str(orm_data["active"]) == "Фестиваль уличной музыки → Городской парк"


def test_primary_key_is_created_automatically(orm_data):
    assert orm_data["park"].pk == orm_data["park"].id
    assert Venue._meta.pk.name == "id"


def test_default_ordering_from_meta(orm_data):
    names = [venue.name for venue in Venue.objects.all()]
    assert names == sorted(names)
    later = Festival.objects.create(
        name="Поздний",
        date=date.today() + timedelta(days=30),
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )
    earlier = Festival.objects.create(
        name="Ранний",
        date=date.today() - timedelta(days=30),
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )
    ordered = list(Festival.objects.all())
    assert ordered[0] == earlier and ordered[-1] == later


def test_date_is_stored_as_date_object(orm_data):
    festival = Festival.objects.get(pk=orm_data["festival"].pk)
    assert isinstance(festival.date, date)


def test_check_constraints_reject_invalid_values(db):
    with pytest.raises(IntegrityError), transaction.atomic():
        Venue.objects.create(name="Нулевая", capacity=0)
    organizer = Organizer.objects.create(name="Организатор")
    with pytest.raises(IntegrityError), transaction.atomic():
        Festival.objects.create(
            name="Пустой", date=date.today(), expected_attendees=0, organizer=organizer
        )


def test_booking_is_active_by_default(orm_data):
    booking = Booking.objects.create(festival=orm_data["festival"], venue=orm_data["park"])
    assert booking.is_cancelled is False


def test_foreign_keys_give_access_to_related_objects(orm_data):
    booking = Booking.objects.get(pk=orm_data["active"].pk)
    assert booking.venue.name == "Городской парк"
    assert booking.festival.organizer.name == "АНО «Арт-Ивент»"
    assert booking.venue_id == orm_data["park"].pk


def test_related_name_gives_reverse_access(orm_data):
    assert list(orm_data["park"].bookings.all()) == [orm_data["active"]]
    assert orm_data["festival"].bookings.count() == 2
    assert list(orm_data["organizer"].festivals.all()) == [orm_data["festival"]]


def test_booking_date_is_festival_date(orm_data):
    assert orm_data["active"].booking_date == orm_data["festival"].date


def test_cancel_saves_only_is_cancelled(orm_data):
    booking = orm_data["active"]
    booking.cancel()
    assert booking.is_cancelled is True
    assert Booking.objects.get(pk=booking.pk).is_cancelled is True


def test_venue_availability_ignores_cancelled_bookings(orm_data):
    today = date.today()
    assert orm_data["park"].is_available_on(today) is False
    assert orm_data["arena"].is_available_on(today) is True  # бронирование отменено
    assert orm_data["park"].is_available_on(today + timedelta(days=1)) is True


def test_venue_is_suitable_for_attendees(orm_data):
    assert orm_data["park"].is_suitable_for(5000) is True
    assert orm_data["park"].is_suitable_for(5001) is False


def test_protect_forbids_deleting_referenced_objects(orm_data):
    with pytest.raises(ProtectedError):
        orm_data["park"].delete()
    with pytest.raises(ProtectedError):
        orm_data["festival"].delete()
    with pytest.raises(ProtectedError):
        orm_data["organizer"].delete()
    orm_data["active"].delete()
    orm_data["park"].delete()  # после удаления бронирования площадку удалить можно
    assert not Venue.objects.filter(name="Городской парк").exists()


def test_crud_operations(db):
    venue = Venue.objects.create(name="Тестовая", capacity=100)  # Create
    assert Venue.objects.filter(name="Тестовая").exists()  # Read
    venue.capacity = 150
    assert Venue.objects.get(pk=venue.pk).capacity == 100  # в памяти не равно в базе
    venue.save()  # Update
    assert Venue.objects.get(pk=venue.pk).capacity == 150
    venue.delete()  # Delete
    assert not Venue.objects.filter(pk=venue.pk).exists()


def test_get_and_filter_differ(orm_data):
    with pytest.raises(Venue.DoesNotExist):
        Venue.objects.get(pk=999)
    assert list(Venue.objects.filter(pk=999)) == []
    Venue.objects.create(name="Городской парк", capacity=1)
    with pytest.raises(Venue.MultipleObjectsReturned):
        Venue.objects.get(name="Городской парк")


def test_models_are_registered_in_admin():
    for model in (Organizer, Venue, Festival, Booking):
        assert admin.site.is_registered(model)


def test_models_match_migrations():
    """makemigrations --check завершается без ошибки, если все изменения моделей учтены."""
    call_command("makemigrations", "--check", "--dry-run")


def test_migrations_create_expected_tables(db):
    from django.db import connection

    tables = set(connection.introspection.table_names())
    assert {
        "venues_venue",
        "festivals_organizer",
        "festivals_festival",
        "bookings_booking",
    } <= tables
