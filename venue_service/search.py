"""Поиск по текстовым полям средствами ORM с учётом регистра кириллицы.

Встроенные средства SQLite (LIKE и функция LOWER) различают регистр только у латиницы, поэтому
lookup icontains и функция Lower() находят «арена» не в «Арена», а только в «арена». Здесь
в SQLite регистрируется функция UNICODE_LOWER на основе str.lower() и описано ORM-выражение
UnicodeLower, которое её вызывает.
"""

from django.db.backends.signals import connection_created
from django.db.models import Func, Q
from django.dispatch import receiver


def _unicode_lower(value):
    return value.lower() if value is not None else None


@receiver(connection_created)
def register_unicode_lower(sender, connection, **kwargs):
    """Регистрирует функцию UNICODE_LOWER в каждом новом соединении с SQLite."""
    if connection.vendor == "sqlite":
        connection.connection.create_function(
            "UNICODE_LOWER", 1, _unicode_lower, deterministic=True
        )


class UnicodeLower(Func):
    """Приведение текста к нижнему регистру с поддержкой Unicode (для SQLite)."""

    function = "UNICODE_LOWER"
    arity = 1


def search_text(queryset, fields, text):
    """Отобрать записи, у которых хотя бы в одном из полей fields встречается text.

    Регистр не учитывается, в том числе для кириллицы: поля приводятся к нижнему регистру
    выражением UnicodeLower, искомая строка — методом str.lower(). Пустой запрос возвращает
    queryset без изменений. Поля могут принадлежать связанным моделям: "festival__name",
    "venue__name". Символы % и _ в запросе трактуются как обычный текст.
    """
    text = (text or "").strip().lower()
    if not text:
        return queryset
    aliases = {f"search_{index}": UnicodeLower(field) for index, field in enumerate(fields)}
    condition = Q()
    for alias in aliases:
        condition |= Q(**{f"{alias}__contains": text})
    return queryset.alias(**aliases).filter(condition)
