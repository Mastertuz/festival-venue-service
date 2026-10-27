from django.db import models
from django.db.models import Q


class Organizer(models.Model):
    """Организатор: ответственное лицо или организация, проводящая фестивали."""

    # Первичный ключ id Django создаёт автоматически.
    name = models.CharField(
        max_length=200,
        verbose_name="Название организатора",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Организатор"
        verbose_name_plural = "Организаторы"


class Festival(models.Model):
    """Фестиваль: мероприятие, для которого подбирается и бронируется площадка."""

    name = models.CharField(
        max_length=200,
        verbose_name="Название фестиваля",
    )

    # DateField хранит дату, а не произвольную строку: при фильтрации значение
    # сравнивается с объектом date.
    date = models.DateField(
        verbose_name="Дата проведения",
    )

    expected_attendees = models.PositiveIntegerField(
        verbose_name="Ожидаемое число посетителей",
    )

    # Один организатор проводит несколько фестивалей (связь «многие к одному»).
    # PROTECT запрещает удалять организатора, у которого есть фестивали.
    # related_name даёт обратный доступ: organizer.festivals.all().
    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.PROTECT,
        related_name="festivals",
        verbose_name="Организатор",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["date", "pk"]
        verbose_name = "Фестиваль"
        verbose_name_plural = "Фестивали"
        constraints = [
            models.CheckConstraint(
                condition=Q(expected_attendees__gt=0),
                name="festival_expected_attendees_positive",
            ),
        ]
