"""Инспекция исходной базы ПР7 перед переносом данных в Django ORM (только чтение).

Запуск из корня проекта: python db/inspect_source_db.py
Скрипт выводит таблицы, столбцы, число записей и проверяет, что данные можно переносить:
ссылки на существующие записи, значения is_cancelled, формат дат.
"""

import sqlite3
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DB = BASE_DIR / "data" / "festival_venue.sqlite"

TABLES_SQL = """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name NOT LIKE 'sqlite_%'
    ORDER BY name;
"""

# Имя таблицы нельзя передать параметром, поэтому запросы подсчёта записаны явно.
COUNT_SQL = {
    "organizers": "SELECT COUNT(*) FROM organizers",
    "venues": "SELECT COUNT(*) FROM venues",
    "festivals": "SELECT COUNT(*) FROM festivals",
    "bookings": "SELECT COUNT(*) FROM bookings",
}

COLUMNS_SQL = 'SELECT name, type, "notnull", pk FROM pragma_table_info(?)'

# Проверки целостности: каждый запрос должен вернуть пустой результат.
CHECKS_SQL = {
    "фестивали со ссылкой на несуществующего организатора": """
        SELECT festivals.id FROM festivals
        LEFT JOIN organizers ON festivals.organizer_id = organizers.id
        WHERE organizers.id IS NULL""",
    "бронирования со ссылкой на несуществующий фестиваль": """
        SELECT bookings.id FROM bookings
        LEFT JOIN festivals ON bookings.festival_id = festivals.id
        WHERE festivals.id IS NULL""",
    "бронирования со ссылкой на несуществующую площадку": """
        SELECT bookings.id FROM bookings
        LEFT JOIN venues ON bookings.venue_id = venues.id
        WHERE venues.id IS NULL""",
    "бронирования со значением is_cancelled не 0 и не 1": """
        SELECT id FROM bookings WHERE is_cancelled NOT IN (0, 1)""",
}

DATES_SQL = "SELECT id, date FROM festivals"


def open_source(path=None):
    """Открыть исходную базу только для чтения; ошибка, если файла нет."""
    path = Path(path or SOURCE_DB)
    if not path.exists():
        raise FileNotFoundError(f"Исходная база не найдена: {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def inspect(connection):
    """Вернуть сведения об исходной базе: таблицы, столбцы, число записей, проблемы."""
    report = {"tables": {}, "counts": {}, "problems": []}
    for (table_name,) in connection.execute(TABLES_SQL).fetchall():
        columns = connection.execute(COLUMNS_SQL, [table_name]).fetchall()
        report["tables"][table_name] = [tuple(column) for column in columns]
        if table_name in COUNT_SQL:
            report["counts"][table_name] = connection.execute(COUNT_SQL[table_name]).fetchone()[0]

    for description, query in CHECKS_SQL.items():
        bad_ids = [row[0] for row in connection.execute(query).fetchall()]
        if bad_ids:
            report["problems"].append(f"{description}: {bad_ids}")

    for festival_id, value in connection.execute(DATES_SQL).fetchall():
        try:
            date.fromisoformat(value)
        except ValueError:
            report["problems"].append(f"фестиваль {festival_id}: дата «{value}» не ГГГГ-ММ-ДД")
    return report


def main():
    with open_source() as connection:
        report = inspect(connection)

    for table_name, columns in report["tables"].items():
        print(f"\nТаблица: {table_name}")
        print("Столбцы:")
        for name, column_type, not_null, primary_key in columns:
            print(
                f"  имя={name}, тип={column_type}, NOT NULL={not_null}, PRIMARY KEY={primary_key}"
            )
        if table_name in report["counts"]:
            print(f"Количество записей: {report['counts'][table_name]}")

    print("\nПроверка целостности:")
    if report["problems"]:
        for problem in report["problems"]:
            print(f"  ПРОБЛЕМА: {problem}")
    else:
        print("  проблем не найдено: данные можно переносить")


if __name__ == "__main__":
    main()
