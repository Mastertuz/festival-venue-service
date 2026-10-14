"""Подключение к базе данных SQLite индивидуального проекта."""

import sqlite3
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "festival_venue.sqlite"
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"


def get_connection(must_exist: bool = True) -> sqlite3.Connection:
    """Создать соединение с базой данных и настроить его.

    * row_factory = sqlite3.Row — к полям строки результата можно обращаться по именам
      (``row["name"]``, в шаблоне ``{{ row.name }}``);
    * PRAGMA foreign_keys = ON — SQLite проверяет внешние ключи (по умолчанию не проверяет).

    По умолчанию отсутствие файла базы — ошибка: иначе sqlite3.connect() молча создал бы
    пустую базу без таблиц. Для создания базы передают must_exist=False.
    """
    if must_exist and not Path(DB_PATH).exists():
        raise FileNotFoundError(
            f"База данных {DB_PATH} не найдена. "
            "Создайте её: python -m db.init_db, затем python -m db.import_json"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Выполнить sql/schema.sql: создать таблицы, которых ещё нет (IF NOT EXISTS)."""
    with open(SCHEMA_FILE, encoding="utf-8") as file:
        conn.executescript(file.read())


def row_with_dates(row: sqlite3.Row, *date_fields: str) -> dict:
    """Преобразовать строку результата в словарь, переведя указанные поля из строки
    формата YYYY-MM-DD в объект date (в SQLite даты хранятся текстом)."""
    result = dict(row)
    for field in date_fields:
        result[field] = date.fromisoformat(result[field])
    return result
