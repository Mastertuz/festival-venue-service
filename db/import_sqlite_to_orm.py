"""Перенос данных из исходной базы ПР7 (SQLite) в таблицы Django, управляемые ORM.

Запуск из корня проекта после применения миграций:
    python db/import_sqlite_to_orm.py

Исходная база data/festival_venue.sqlite открывается только для чтения и не изменяется.
Записи создаются средствами ORM с сохранением идентификаторов, поэтому внешние ключи
остаются корректными. Порядок переноса повторяет зависимости: организаторы, площадки,
фестивали, затем бронирования. Повторный запуск обновляет записи с теми же идентификаторами
и не создаёт дублей.
"""

import os
import sys
from datetime import date
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent

# Корень проекта нужен в путях поиска модулей, если скрипт запущен как файл.
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "venue_service.settings")
django.setup()

from django.db import transaction  # noqa: E402

from bookings.models import Booking  # noqa: E402
from db.inspect_source_db import SOURCE_DB, inspect, open_source  # noqa: E402
from festivals.models import Festival, Organizer  # noqa: E402
from venues.models import Venue  # noqa: E402

ORGANIZERS_SQL = "SELECT id, name FROM organizers ORDER BY id"
VENUES_SQL = "SELECT id, name, capacity FROM venues ORDER BY id"
FESTIVALS_SQL = """
    SELECT id, name, date, expected_attendees, organizer_id
    FROM festivals
    ORDER BY id
"""
BOOKINGS_SQL = "SELECT id, festival_id, venue_id, is_cancelled FROM bookings ORDER BY id"


def transfer(source_path=None):
    """Перенести данные в базу Django и вернуть число записей каждой модели."""
    with open_source(source_path or SOURCE_DB) as source:
        problems = inspect(source)["problems"]
        if problems:
            raise ValueError("Исходные данные содержат ошибки: " + "; ".join(problems))
        organizers = source.execute(ORGANIZERS_SQL).fetchall()
        venues = source.execute(VENUES_SQL).fetchall()
        festivals = source.execute(FESTIVALS_SQL).fetchall()
        bookings = source.execute(BOOKINGS_SQL).fetchall()

    # Одна транзакция: при ошибке все изменения откатываются, частичный перенос не сохранится.
    with transaction.atomic():
        for row in organizers:
            Organizer.objects.update_or_create(
                pk=row["id"],
                defaults={"name": row["name"]},
            )
        for row in venues:
            Venue.objects.update_or_create(
                pk=row["id"],
                defaults={"name": row["name"], "capacity": row["capacity"]},
            )
        for row in festivals:
            Festival.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "name": row["name"],
                    # В исходной базе дата — строка ГГГГ-ММ-ДД, а DateField ждёт объект date.
                    "date": date.fromisoformat(row["date"]),
                    "expected_attendees": row["expected_attendees"],
                    "organizer_id": row["organizer_id"],
                },
            )
        for row in bookings:
            Booking.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "festival_id": row["festival_id"],
                    "venue_id": row["venue_id"],
                    "is_cancelled": bool(row["is_cancelled"]),
                },
            )

    return {
        "organizers": Organizer.objects.count(),
        "venues": Venue.objects.count(),
        "festivals": Festival.objects.count(),
        "bookings": Booking.objects.count(),
    }


def main():
    counts = transfer()
    print("Перенос данных завершён.")
    print(f"Организаторов: {counts['organizers']}")
    print(f"Площадок: {counts['venues']}")
    print(f"Фестивалей: {counts['festivals']}")
    print(f"Бронирований: {counts['bookings']}")


if __name__ == "__main__":
    main()
