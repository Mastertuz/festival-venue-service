from django.db import models
from django.db.models import Case, Q, Value, When
from django.urls import reverse
from django.utils.text import slugify
from unidecode import unidecode

# Площадка считается большой при вместимости не менее этого значения (учебный порог).
LARGE_VENUE_CAPACITY = 3000


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
        help_text="Максимальное число посетителей, которое может находиться на площадке.",
    )

    # Вычисляемое поле: значение формирует база данных на основе capacity и хранит в таблице
    # (db_persist=True). Вручную его не задают и в формах оно не редактируется.
    is_large = models.GeneratedField(
        expression=Case(
            When(capacity__gte=LARGE_VENUE_CAPACITY, then=Value(True)),
            default=Value(False),
            output_field=models.BooleanField(),
        ),
        output_field=models.BooleanField(),
        db_persist=True,
        verbose_name="Большая площадка",
    )

    # Текстовый идентификатор для адреса страницы: транслитерация названия и первичный ключ,
    # например «gorodskoi-park-1». Формируется в save(); вручную не редактируется.
    # unique=True: два адреса площадок совпасть не могут (ограничение на уровне базы данных).
    slug = models.SlugField(
        max_length=180,
        unique=True,
        editable=False,
        verbose_name="URL-идентификатор",
    )

    def __str__(self):
        # Текстовое представление объекта в админ-панели и Django shell.
        return self.name

    def save(self, *args, **kwargs):
        """Сохранить площадку; slug формируется один раз, при его отсутствии."""
        if not self.slug:
            base_slug = slugify(unidecode(self.name)) or "venue"
            if self.pk:
                self.slug = f"{base_slug}-{self.pk}"
            else:
                # Первичного ключа ещё нет: сначала сохраняем запись, затем дописываем id.
                super().save(*args, **kwargs)
                self.slug = f"{base_slug}-{self.pk}"
                super().save(update_fields=["slug"])
                return
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Адрес подробной страницы площадки: /venues/<slug>/."""
        return reverse("venues:detail", kwargs={"slug": self.slug})

    def is_suitable_for(self, expected_attendees):
        """Проверить, что вместимость не меньше ожидаемого числа посетителей."""
        return self.capacity >= expected_attendees

    def is_available_on(self, day):
        """Свободна ли площадка на дату: отменённые бронирования её не блокируют."""
        return not self.bookings.active().for_date(day).exists()

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
