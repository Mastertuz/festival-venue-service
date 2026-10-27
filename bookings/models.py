from django.db import models

from festivals.models import Festival
from venues.models import Venue


class Booking(models.Model):
    """Бронирование площадки под фестиваль (запись расписания)."""

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

    # Признак отмены. Новое бронирование по умолчанию активно.
    is_cancelled = models.BooleanField(
        default=False,
        verbose_name="Бронирование отменено",
    )

    @property
    def booking_date(self):
        """Дата бронирования — дата проведения фестиваля."""
        return self.festival.date

    def cancel(self):
        """Отметить бронирование отменённым и сохранить только это поле."""
        self.is_cancelled = True
        self.save(update_fields=["is_cancelled"])

    def __str__(self):
        return f"{self.festival} → {self.venue}"

    class Meta:
        # Сначала по дате фестиваля, затем по идентификатору.
        ordering = ["festival__date", "pk"]
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
