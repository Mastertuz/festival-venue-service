"""Функции сохранения и загрузки данных проекта в формате JSON."""

import json


def load_venues(filename: str) -> dict[int, dict]:
    """Загрузить площадки из JSON-файла.

    Если файл отсутствует или содержит некорректный JSON,
    возвращается пустой словарь площадок.
    """
    try:
        with open(filename, encoding="utf-8") as file:
            venues_list = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {venue["id"]: venue for venue in venues_list}


def save_venues(filename: str, venues: dict[int, dict]) -> None:
    """Сохранить площадки в JSON-файл."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(list(venues.values()), file, ensure_ascii=False, indent=2)


def load_bookings(filename: str) -> list[dict]:
    """Загрузить бронирования из JSON-файла.

    Если файл отсутствует или содержит некорректный JSON,
    возвращается пустой список бронирований.
    """
    try:
        with open(filename, encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_bookings(filename: str, bookings: list[dict]) -> None:
    """Сохранить бронирования в JSON-файл."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(bookings, file, ensure_ascii=False, indent=2)
