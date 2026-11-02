"""ПР10: статусы бронирования (TextChoices), менеджер BookingQuerySet и перенос данных."""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from bookings.models import Booking
from festivals.models import Festival, Organizer
from venues.models import Venue

TODAY = date.today()


@pytest.fixture
def statuses(db):
    """Три бронирования одной площадки на разные даты со статусами active, cancelled, completed."""
    organizer = Organizer.objects.create(name="Организатор")
    venue = Venue.objects.create(name="Парк", capacity=4000)
    result = {"venue": venue}
    for offset, (key, status) in enumerate(
        [
            ("active", Booking.Status.ACTIVE),
            ("cancelled", Booking.Status.CANCELLED),
            ("completed", Booking.Status.COMPLETED),
        ]
    ):
        festival = Festival.objects.create(
            name=f"Фестиваль {key}",
            date=TODAY + timedelta(days=offset),
            expected_attendees=100,
            organizer=organizer,
        )
        result[key] = Booking.objects.create(festival=festival, venue=venue, status=status)
    return result


def test_status_choices_have_codes_and_russian_labels():
    assert Booking.Status.ACTIVE == "active"
    assert Booking.Status.ACTIVE.label == "Активно"
    assert Booking.Status.CANCELLED.label == "Отменено"
    assert Booking.Status.COMPLETED.label == "Завершено"
    assert Booking.Status.values == ["active", "cancelled", "completed"]


def test_new_booking_is_active_and_has_no_is_cancelled_field(statuses):
    booking = Booking.objects.create(festival=statuses["active"].festival, venue=statuses["venue"])
    assert booking.status == Booking.Status.ACTIVE
    assert "is_cancelled" not in {field.name for field in Booking._meta.get_fields()}


def test_get_status_display_returns_human_readable_name(statuses):
    assert statuses["cancelled"].get_status_display() == "Отменено"
    assert statuses["completed"].get_status_display() == "Завершено"


def test_manager_methods_return_only_matching_records(statuses):
    assert list(Booking.objects.active()) == [statuses["active"]]
    assert list(Booking.objects.cancelled()) == [statuses["cancelled"]]
    assert list(Booking.objects.completed()) == [statuses["completed"]]


def test_all_still_returns_every_booking_including_history(statuses):
    assert Booking.objects.all().count() == 3
    counts = (
        Booking.objects.active().count()
        + Booking.objects.cancelled().count()
        + Booking.objects.completed().count()
    )
    assert counts == Booking.objects.count()


def test_for_date_uses_festival_date_and_can_be_chained(statuses):
    assert list(Booking.objects.for_date(TODAY)) == [statuses["active"]]
    assert list(Booking.objects.for_date(TODAY + timedelta(days=1))) == [statuses["cancelled"]]
    assert Booking.objects.active().for_date(TODAY + timedelta(days=1)).count() == 0


def test_queryset_methods_are_available_on_related_manager(statuses):
    assert list(statuses["venue"].bookings.active()) == [statuses["active"]]
    assert statuses["venue"].bookings.cancelled().count() == 1


def test_cancel_and_complete_save_only_status(statuses):
    booking = statuses["active"]
    booking.cancel()
    assert Booking.objects.get(pk=booking.pk).status == Booking.Status.CANCELLED
    booking.complete()
    assert Booking.objects.get(pk=booking.pk).status == Booking.Status.COMPLETED


def test_only_active_booking_blocks_the_venue(statuses):
    venue = statuses["venue"]
    assert venue.is_available_on(TODAY) is False  # активное
    assert venue.is_available_on(TODAY + timedelta(days=1)) is True  # отменённое
    assert venue.is_available_on(TODAY + timedelta(days=2)) is True  # завершённое


def test_free_venues_page_ignores_cancelled_and_completed_bookings(statuses):
    def free(day):
        response = Client().get("/venues/available/", {"date": day.isoformat()})
        return [venue.name for venue in response.context["venues"]]

    assert free(TODAY) == []
    assert free(TODAY + timedelta(days=1)) == ["Парк"]
    assert free(TODAY + timedelta(days=2)) == ["Парк"]


def test_statistics_counts_each_status(statuses):
    response = Client().get("/bookings/statistics/")
    assert response.context["status_counts"] == {
        "total_bookings": 3,
        "active_bookings": 1,
        "cancelled_bookings": 1,
        "completed_bookings": 1,
    }
    assert response.context["active_bookings_count"] == 1
    html = " ".join(response.content.decode().split())
    assert "Отменённых" in html and "Завершённых" in html


def test_statistics_by_venue_counts_only_active_bookings(statuses):
    response = Client().get("/bookings/statistics/")
    assert list(response.context["by_venue"]) == [{"venue_name": "Парк", "bookings_count": 1}]


def test_booking_list_only_active_filter_uses_status(statuses):
    response = Client().get("/bookings/", {"active": "1"})
    assert [row["id"] for row in response.context["bookings"]] == [statuses["active"].pk]
    assert Client().get("/bookings/").context["total_count"] == 3


@pytest.mark.parametrize(
    ("status", "badge"),
    [("active", "Активно"), ("cancelled", "Отменено"), ("completed", "Завершено")],
)
def test_status_badge_is_shown_for_every_status(statuses, status, badge):
    booking = statuses[status]
    html = " ".join(Client().get("/bookings/%d/" % booking.pk).content.decode().split())
    assert f"booking-status-{status}" in html
    assert badge in html


def test_clean_rejects_second_active_booking_for_same_venue_and_date(statuses):
    duplicate = Booking(festival=statuses["active"].festival, venue=statuses["venue"])
    with pytest.raises(ValidationError):
        duplicate.clean()


def test_clean_allows_cancelled_booking_on_busy_date_and_own_record(statuses):
    festival = statuses["active"].festival
    Booking(festival=festival, venue=statuses["venue"], status=Booking.Status.CANCELLED).clean()
    statuses["active"].clean()  # бронирование не конфликтует само с собой


def test_data_migration_moves_is_cancelled_to_status(transactional_db):
    """Миграция 0003 переносит is_cancelled в status; миграция 0004 удаляет старое поле."""
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    before = [("bookings", "0002_booking_status")]
    after = [("bookings", "0003_migrate_booking_statuses")]
    try:
        executor.migrate(before)
        old_apps = MigrationExecutor(connection).loader.project_state(before).apps
        Organizer = old_apps.get_model("festivals", "Organizer")
        Festival = old_apps.get_model("festivals", "Festival")
        OldBooking = old_apps.get_model("bookings", "Booking")
        organizer = Organizer.objects.create(name="Старый организатор")
        festival = Festival.objects.create(
            name="Старый фестиваль",
            date=TODAY,
            expected_attendees=10,
            organizer=organizer,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO venues_venue (id, name, capacity, slug) "
                "VALUES (1, 'Парк', 10, 'park-1')"
            )
        active = OldBooking.objects.create(festival_id=festival.pk, venue_id=1, is_cancelled=False)
        cancelled = OldBooking.objects.create(
            festival_id=festival.pk, venue_id=1, is_cancelled=True
        )
        # До переноса новое поле у обеих записей содержит значение по умолчанию.
        assert {active.status, cancelled.status} == {"active"}

        executor = MigrationExecutor(connection)
        executor.migrate(after)
        new_apps = MigrationExecutor(connection).loader.project_state(after).apps
        NewBooking = new_apps.get_model("bookings", "Booking")
        assert NewBooking.objects.get(pk=active.pk).status == "active"
        assert NewBooking.objects.get(pk=cancelled.pk).status == "cancelled"
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
    columns = [
        column.name
        for column in connection.introspection.get_table_description(
            connection.cursor(), "bookings_booking"
        )
    ]
    assert "is_cancelled" not in columns and "status" in columns
