"""Создание файла базы данных SQLite и таблиц по sql/schema.sql.

Запуск из корня проекта: python -m db.init_db
Повторный запуск безопасен: таблицы создаются только если их ещё нет.
"""

from db.database import DB_PATH, get_connection, init_schema


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(must_exist=False)
    try:
        init_schema(conn)
        conn.commit()
    finally:
        conn.close()
    print(f"База данных готова: {DB_PATH}")


if __name__ == "__main__":
    main()
