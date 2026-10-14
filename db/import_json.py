"""Перенос данных проекта из JSON-файлов в таблицы базы данных SQLite.

Запуск из корня проекта: python -m db.import_json
Скрипт создаёт таблицы (если их ещё нет) и заново заполняет базу данными из JSON:
повторный запуск не приводит к дублированию записей.
"""

import json
import sqlite3

from db.database import BASE_DIR, DB_PATH, get_connection, init_schema

DATA_DIR = BASE_DIR / "data"
ORGANIZERS_FILE = DATA_DIR / "organizers.json"
VENUES_FILE = DATA_DIR / "venues.json"
FESTIVALS_FILE = DATA_DIR / "festivals.json"
BOOKINGS_FILE = DATA_DIR / "bookings.json"

# Очистка в порядке, обратном зависимостям: сначала таблицы со ссылками на другие.
CLEAR_STATEMENTS = (
    "DELETE FROM bookings",
    "DELETE FROM festivals",
    "DELETE FROM venues",
    "DELETE FROM organizers",
)


def load_json(filename):
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def clear_tables(conn: sqlite3.Connection) -> None:
    for statement in CLEAR_STATEMENTS:
        conn.execute(statement)


def import_organizers(conn: sqlite3.Connection) -> None:
    organizers = load_json(ORGANIZERS_FILE)
    conn.executemany(
        """
        INSERT INTO organizers (
            id,
            name
        )
        VALUES (?, ?)
        """,
        [(organizer["id"], organizer["name"]) for organizer in organizers],
    )


def import_venues(conn: sqlite3.Connection) -> None:
    venues = load_json(VENUES_FILE)
    conn.executemany(
        """
        INSERT INTO venues (
            id,
            name,
            capacity
        )
        VALUES (?, ?, ?)
        """,
        [(venue["id"], venue["name"], venue["capacity"]) for venue in venues],
    )


def import_festivals(conn: sqlite3.Connection) -> None:
    festivals = load_json(FESTIVALS_FILE)
    conn.executemany(
        """
        INSERT INTO festivals (
            id,
            name,
            date,
            expected_attendees,
            organizer_id
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                festival["id"],
                festival["name"],
                festival["date"],
                festival["expected_attendees"],
                festival["organizer_id"],
            )
            for festival in festivals
        ],
    )


def import_bookings(conn: sqlite3.Connection) -> None:
    bookings = load_json(BOOKINGS_FILE)
    conn.executemany(
        """
        INSERT INTO bookings (
            id,
            festival_id,
            venue_id,
            is_cancelled
        )
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                booking["id"],
                booking["festival_id"],
                booking["venue_id"],
                int(booking.get("is_cancelled", False)),
            )
            for booking in bookings
        ],
    )


def import_all(conn: sqlite3.Connection) -> None:
    """Перенести все данные. Порядок важен: сначала таблицы, на которые ссылаются другие."""
    clear_tables(conn)
    import_organizers(conn)
    import_venues(conn)
    import_festivals(conn)
    import_bookings(conn)


def count_rows(conn: sqlite3.Connection) -> dict:
    return {
        "organizers": conn.execute("SELECT COUNT(*) FROM organizers").fetchone()[0],
        "venues": conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0],
        "festivals": conn.execute("SELECT COUNT(*) FROM festivals").fetchone()[0],
        "bookings": conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
    }


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(must_exist=False)
    try:
        init_schema(conn)
        import_all(conn)
        conn.commit()
        counts = count_rows(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Импорт завершён: " + ", ".join(f"{table} — {count}" for table, count in counts.items()))


if __name__ == "__main__":
    main()
