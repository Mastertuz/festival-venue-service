from django.db import models
from django.db.models import Q


class Venue(models.Model):
    """Площадка, доступная для проведения фестиваля."""

    # Название площадки. max_length задаёт максимально допустимую длину строки.
    name = models.CharField(
        max_length=200,
        verbose_name="Название площадки",
    )

    # Вместимость: неотрицательное целое число (дополнительно запрещён ноль, см. Meta).
    capacity = models.PositiveIntegerField(
        verbose_name="Вместимость",
    )

    def __str__(self):
        # Текстовое представление объекта в админ-панели и Django shell.
        return self.name

    def is_suitable_for(self, expected_attendees):
        """Проверить, что вместимость не меньше ожидаемого числа посетителей."""
        return self.capacity >= expected_attendees

    def is_available_on(self, day):
        """Свободна ли площадка на дату: отменённые бронирования её не блокируют."""
        return not self.bookings.filter(
            festival__date=day,
            is_cancelled=False,
        ).exists()

    class Meta:
        ordering = ["name"]
        verbose_name = "Площадка"
        verbose_name_plural = "Площадки"
        constraints = [
            models.CheckConstraint(
                condition=Q(capacity__gt=0),
                name="venue_capacity_positive",
            ),
        ]
