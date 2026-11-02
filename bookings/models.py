from django.core.exceptions import ValidationError
from django.db import models

from festivals.models import Festival
from venues.models import Venue


class BookingQuerySet(models.QuerySet):
    """Набор запросов для работы с бронированиями."""

    def active(self):
        """Только активные бронирования (блокируют площадку на дату фестиваля)."""
        return self.filter(status=self.model.Status.ACTIVE)

    def cancelled(self):
        """Только отменённые бронирования."""
        return self.filter(status=self.model.Status.CANCELLED)

    def completed(self):
        """Только завершённые бронирования."""
        return self.filter(status=self.model.Status.COMPLETED)

    def for_date(self, selected_date):
        """Бронирования на указанную дату: дата берётся у фестиваля (festival__date)."""
        return self.filter(festival__date=selected_date)


class BookingManager(models.Manager.from_queryset(BookingQuerySet)):
    """Менеджер бронирований: методы BookingQuerySet доступны через Booking.objects."""


class Booking(models.Model):
    """Бронирование площадки под фестиваль (запись расписания)."""

    class Status(models.TextChoices):
        """Состояния бронирования: в базе хранится код, пользователю показывается название."""

        ACTIVE = "active", "Активно"
        CANCELLED = "cancelled", "Отменено"
        COMPLETED = "completed", "Завершено"

    # Фестиваль, для которого оформлено бронирование.
    # related_name="bookings" даёт обратный доступ: festival.bookings.all().
    festival = models.ForeignKey(
        Festival,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Фестиваль",
    )

    # Забронированная площадка: venue.bookings.all() — её бронирования.
    # PROTECT: площадку с бронированиями нельзя удалить — история сохраняется.
    venue = models.ForeignKey(
        Venue,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Площадка",
    )

    # Статус бронирования: активное, отменённое или завершённое.
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Статус бронирования",
        help_text="Отменённое и завершённое бронирование не блокирует площадку на дату.",
    )

    # Менеджер с методами active(), cancelled(), completed(), for_date().
    # Booking.objects.all() по-прежнему возвращает все записи, включая отменённые.
    objects = BookingManager()

    @property
    def booking_date(self):
        """Дата бронирования — дата проведения фестиваля."""
        return self.festival.date

    def clean(self):
        """Правило предметной области: одна площадка — одно активное бронирование на дату."""
        super().clean()
        if self.status != self.Status.ACTIVE or not (self.festival_id and self.venue_id):
            return
        conflicts = (
            Booking.objects.active()
            .for_date(self.festival.date)
            .filter(venue_id=self.venue_id)
            .exclude(pk=self.pk)
        )
        if conflicts.exists():
            raise ValidationError(
                "Площадка уже забронирована на эту дату: есть активное бронирование."
            )

    def cancel(self):
        """Отметить бронирование отменённым и сохранить только это поле."""
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])

    def complete(self):
        """Отметить бронирование завершённым и сохранить только это поле."""
        self.status = self.Status.COMPLETED
        self.save(update_fields=["status"])

    def __str__(self):
        return f"{self.festival} → {self.venue}"

    class Meta:
        # Сначала по дате фестиваля, затем по идентификатору.
        ordering = ["festival__date", "pk"]
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
