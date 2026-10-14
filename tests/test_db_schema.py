import sqlite3

import pytest

import db.database
from db.database import get_connection, init_schema
from db.init_db import main as init_db_main

TABLES = {"organizers", "venues", "festivals", "bookings"}


@pytest.fixture
def conn(db_path):
    init_db_main()
    connection = get_connection()
    yield connection
    connection.close()


def table_names(connection):
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_init_db_creates_file_and_all_tables(db_path):
    assert not db_path.exists()
    init_db_main()
    assert db_path.exists()
    connection = get_connection()
    try:
        assert TABLES <= table_names(connection)
    finally:
        connection.close()


def test_schema_can_be_applied_twice(conn):
    init_schema(conn)
    init_schema(conn)
    assert TABLES <= table_names(conn)


def test_every_table_has_integer_primary_key_id(conn):
    for table in TABLES:
        columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
        pk = [column for column in columns if column["pk"]]
        assert [(c["name"], c["type"]) for c in pk] == [("id", "INTEGER")], table


def test_column_types_match_domain(conn):
    def types(table):
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {row["name"]: row["type"] for row in rows}

    assert types("venues") == {"id": "INTEGER", "name": "TEXT", "capacity": "INTEGER"}
    assert types("festivals")["date"] == "TEXT"
    assert types("bookings")["is_cancelled"] == "INTEGER"


def test_foreign_keys_are_defined(conn):
    def targets(table):
        rows = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        return {(row["from"], row["table"], row["to"]) for row in rows}

    assert targets("festivals") == {("organizer_id", "organizers", "id")}
    assert targets("bookings") == {
        ("festival_id", "festivals", "id"),
        ("venue_id", "venues", "id"),
    }


def test_foreign_key_checking_is_enabled(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_booking_with_unknown_festival_is_rejected(conn):
    conn.execute("INSERT INTO venues (id, name, capacity) VALUES (1, 'Парк', 100)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO bookings (id, festival_id, venue_id) VALUES (1, 99, 1)")


def test_check_constraints_reject_invalid_values(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO venues (id, name, capacity) VALUES (1, 'Парк', 0)")
    conn.execute("INSERT INTO organizers (id, name) VALUES (1, 'Организатор')")
    conn.execute("INSERT INTO venues (id, name, capacity) VALUES (1, 'Парк', 100)")
    conn.execute(
        "INSERT INTO festivals (id, name, date, expected_attendees, organizer_id) "
        "VALUES (1, 'Фестиваль', '2026-06-12', 50, 1)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO bookings (id, festival_id, venue_id, is_cancelled) VALUES (1, 1, 1, 2)"
        )


def test_is_cancelled_defaults_to_active(conn):
    conn.execute("INSERT INTO organizers (id, name) VALUES (1, 'Организатор')")
    conn.execute("INSERT INTO venues (id, name, capacity) VALUES (1, 'Парк', 100)")
    conn.execute(
        "INSERT INTO festivals (id, name, date, expected_attendees, organizer_id) "
        "VALUES (1, 'Фестиваль', '2026-06-12', 50, 1)"
    )
    conn.execute("INSERT INTO bookings (id, festival_id, venue_id) VALUES (1, 1, 1)")
    assert conn.execute("SELECT is_cancelled FROM bookings").fetchone()["is_cancelled"] == 0


def test_rows_are_accessible_by_column_name(conn):
    conn.execute("INSERT INTO venues (id, name, capacity) VALUES (1, 'Парк', 100)")
    row = conn.execute("SELECT id, name, capacity FROM venues").fetchone()
    assert isinstance(row, sqlite3.Row)
    assert (row["id"], row["name"], row["capacity"]) == (1, "Парк", 100)


def test_missing_database_is_an_error_and_is_not_created(db_path):
    with pytest.raises(FileNotFoundError):
        get_connection()
    assert not db_path.exists()


def test_connection_uses_module_level_db_path(db_path):
    assert db.database.DB_PATH == db_path
