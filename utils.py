"""Вспомогательные функции для безопасного ввода данных пользователем."""

import inspect
from datetime import date, datetime
from typing import Callable


def input_int(prompt: str) -> int:
    """Запросить у пользователя целое число, повторяя запрос при ошибке."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Введите целое число.")


def input_date(prompt: str) -> date:
    """Запросить у пользователя дату в формате ДД.ММ.ГГГГ."""
    while True:
        try:
            return datetime.strptime(input(prompt), "%d.%m.%Y").date()
        except ValueError:
            print("Введите дату в формате ДД.ММ.ГГГГ, например 15.09.2026.")


def describe_function(func: Callable) -> str:
    """Вернуть сигнатуру и описание функции (интроспекция) для команды помощи."""
    return f"{func.__name__}{inspect.signature(func)}\n{inspect.getdoc(func)}"
