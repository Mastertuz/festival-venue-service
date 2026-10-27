"""Разбор и проверка параметров GET-запроса, которые вводит пользователь."""

from datetime import date

MAX_NUMBER = 1_000_000_000


def parse_non_negative_int(value):
    """Разобрать целое неотрицательное число из параметра запроса.

    Возвращает пару (число или None, признак ошибки): пустое значение не считается ошибкой.
    Верхняя граница защищает от чисел, которые не помещаются в целое поле базы данных.
    """
    value = (value or "").strip()
    if not value:
        return None, False
    try:
        number = int(value)
    except ValueError:
        return None, True
    if not 0 <= number <= MAX_NUMBER:
        return None, True
    return number, False


def parse_iso_date(value):
    """Разобрать дату формата ГГГГ-ММ-ДД из параметра запроса: (date или None, признак ошибки)."""
    value = (value or "").strip()
    if not value:
        return None, False
    try:
        return date.fromisoformat(value), False
    except ValueError:
        return None, True
