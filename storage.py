"""Функции сохранения и загрузки данных проекта в формате JSON."""

import json


def _load_dict(filename: str) -> dict[int, dict]:
    """Загрузить список записей из JSON-файла в словарь, индексированный по id.

    Если файл отсутствует или содержит некорректный JSON,
    возвращается пустой словарь.
    """
    try:
        with open(filename, encoding="utf-8") as file:
            records = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {record["id"]: record for record in records}


def _save_dict(filename: str, records: dict[int, dict]) -> None:
    """Сохранить словарь записей в JSON-файл в виде списка."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(list(records.values()), file, ensure_ascii=False, indent=2)


def load_venues(filename: str) -> dict[int, dict]:
    """Загрузить площадки из JSON-файла."""
    return _load_dict(filename)


def save_venues(filename: str, venues: dict[int, dict]) -> None:
    """Сохранить площадки в JSON-файл."""
    _save_dict(filename, venues)


def load_organizers(filename: str) -> dict[int, dict]:
    """Загрузить организаторов из JSON-файла."""
    return _load_dict(filename)


def save_organizers(filename: str, organizers: dict[int, dict]) -> None:
    """Сохранить организаторов в JSON-файл."""
    _save_dict(filename, organizers)


def load_festivals(filename: str) -> dict[int, dict]:
    """Загрузить фестивали из JSON-файла."""
    return _load_dict(filename)


def save_festivals(filename: str, festivals: dict[int, dict]) -> None:
    """Сохранить фестивали в JSON-файл."""
    _save_dict(filename, festivals)


def load_bookings(filename: str) -> list[dict]:
    """Загрузить расписание (бронирования) из JSON-файла.

    Если файл отсутствует или содержит некорректный JSON,
    возвращается пустой список.
    """
    try:
        with open(filename, encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_bookings(filename: str, bookings: list[dict]) -> None:
    """Сохранить расписание (бронирования) в JSON-файл."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(bookings, file, ensure_ascii=False, indent=2)
