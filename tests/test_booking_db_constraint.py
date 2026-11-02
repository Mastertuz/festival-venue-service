"""ПР10: правило «одна площадка — одно активное бронирование на дату» на уровне базы данных."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from bookings.models import Booking
from festivals.models import Festival

TRIGGERS = {
    "booking_active_conflict_insert",
    "booking_active_conflict_update",
    "festival_date_conflict_update",
}

pytestmark = pytest.mark.django_db


def triggers():
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        return {row[0] for row in cursor.fetchall()}


@pytest.fixture
def same_day_festival(orm_data):
    """Второй фестиваль в ту же дату, что и основной (у площадки «парк» там активная запись)."""
    festival = orm_data["festival"]
    return Festival.objects.create(
        name="Второй фестиваль",
        date=festival.date,
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )


@pytest.fixture
def other_day_festival(orm_data):
    festival = orm_data["festival"]
    return Festival.objects.create(
        name="Другой день",
        date=festival.date.replace(year=festival.date.year + 1),
        expected_attendees=10,
        organizer=orm_data["organizer"],
    )


def test_triggers_exist_after_migrations():
    assert TRIGGERS <= triggers()


def test_database_rejects_second_active_booking_without_validation(orm_data, same_day_festival):
    # create() не вызывает clean(): правило срабатывает на уровне базы данных.
    with pytest.raises(IntegrityError, match="Площадка уже забронирована"), transaction.atomic():
        Booking.objects.create(festival=same_day_festival, venue=orm_data["park"])
    assert Booking.objects.count() == 2


def test_database_allows_cancelled_and_completed_duplicates(orm_data, same_day_festival):
    for status in (Booking.Status.CANCELLED, Booking.Status.COMPLETED):
        Booking.objects.create(festival=same_day_festival, venue=orm_data["park"], status=status)
    assert Booking.objects.filter(venue=orm_data["park"]).count() == 3


def test_database_allows_same_date_for_other_venue_and_other_date_for_same_venue(
    orm_data, same_day_festival, other_day_festival
):
    Booking.objects.create(festival=same_day_festival, venue=orm_data["arena"])
    Booking.objects.create(festival=other_day_festival, venue=orm_data["park"])
    assert Booking.objects.active().count() == 3


def test_database_rejects_returning_booking_to_active_by_update(orm_data, same_day_festival):
    cancelled = Booking.objects.create(
        festival=same_day_festival, venue=orm_data["park"], status=Booking.Status.CANCELLED
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=cancelled.pk).update(status=Booking.Status.ACTIVE)
    cancelled.refresh_from_db()
    assert cancelled.status == Booking.Status.CANCELLED


def test_database_rejects_moving_booking_to_busy_venue(orm_data, same_day_festival):
    booking = Booking.objects.create(festival=same_day_festival, venue=orm_data["arena"])
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=booking.pk).update(venue=orm_data["park"])


def test_database_rejects_moving_festival_to_busy_date(
    orm_data, same_day_festival, other_day_festival
):
    Booking.objects.create(festival=other_day_festival, venue=orm_data["park"])
    with pytest.raises(IntegrityError), transaction.atomic():
        Festival.objects.filter(pk=other_day_festival.pk).update(date=orm_data["festival"].date)
    other_day_festival.refresh_from_db()
    assert other_day_festival.date != orm_data["festival"].date


def test_moving_festival_to_free_date_is_allowed(orm_data, other_day_festival):
    Booking.objects.create(festival=other_day_festival, venue=orm_data["park"])
    free_date = other_day_festival.date.replace(year=other_day_festival.date.year + 1)
    Festival.objects.filter(pk=other_day_festival.pk).update(date=free_date)
    other_day_festival.refresh_from_db()
    assert other_day_festival.date == free_date


def test_festival_clean_rejects_date_busy_for_its_active_booking(orm_data, other_day_festival):
    Booking.objects.create(festival=other_day_festival, venue=orm_data["park"])
    other_day_festival.date = orm_data["festival"].date
    with pytest.raises(ValidationError, match="Площадка уже забронирована"):
        other_day_festival.clean()


def test_festival_clean_ignores_cancelled_bookings_and_keeps_free_dates(
    orm_data, other_day_festival
):
    Booking.objects.create(
        festival=other_day_festival, venue=orm_data["park"], status=Booking.Status.CANCELLED
    )
    other_day_festival.date = orm_data["festival"].date
    other_day_festival.clean()  # активных бронирований у фестиваля нет — конфликта нет
    orm_data["festival"].clean()  # собственная дата не конфликтует сама с собой


def test_admin_festival_form_rejects_busy_date(admin_client, orm_data, other_day_festival):
    Booking.objects.create(festival=other_day_festival, venue=orm_data["park"])
    response = admin_client.post(
        f"/admin/festivals/festival/{other_day_festival.pk}/change/",
        {
            "name": other_day_festival.name,
            "date": orm_data["festival"].date.isoformat(),
            "expected_attendees": "10",
            "organizer": str(orm_data["organizer"].pk),
            "bookings-TOTAL_FORMS": "1",
            "bookings-INITIAL_FORMS": "1",
            "bookings-MIN_NUM_FORMS": "0",
            "bookings-MAX_NUM_FORMS": "1000",
            "bookings-0-id": str(other_day_festival.bookings.get().pk),
            "bookings-0-festival": str(other_day_festival.pk),
            "bookings-0-status": "active",
        },
    )
    assert response.status_code == 200
    assert "Площадка уже забронирована на эту дату" in response.content.decode()


def test_triggers_are_removed_and_restored_by_migration_rollback(transactional_db):
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("bookings", "0005_booking_status_help_text")])
        assert not TRIGGERS & triggers()
    finally:
        MigrationExecutor(connection).migrate(latest)
    assert TRIGGERS <= triggers()
