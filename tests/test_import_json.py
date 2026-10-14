import json
import sqlite3

import pytest

import db.import_json as import_json
from db.database import BASE_DIR, get_connection, init_schema

ORGANIZERS = [{"id": 1, "name": "АНО «Арт-Ивент»"}]
VENUES = [
    {"id": 1, "name": "Городской парк", "capacity": 5000},
    {"id": 2, "name": "Арена", "capacity": 2000},
]
FESTIVALS = [
    {
        "id": 1,
        "name": "Фестиваль уличной музыки",
        "date": "2026-06-12",
        "expected_attendees": 4500,
        "organizer_id": 1,
    }
]
BOOKINGS = [
    {"id": 1, "festival_id": 1, "venue_id": 1, "is_cancelled": False},
    {"id": 2, "festival_id": 1, "venue_id": 2, "is_cancelled": True},
]


def write_json_files(directory, **overrides):
    """Записать JSON-файлы данных во временный каталог и вернуть их пути."""
    payloads = {
        "organizers": ORGANIZERS,
        "venues": VENUES,
        "festivals": FESTIVALS,
        "bookings": BOOKINGS,
    }
    payloads.update(overrides)
    paths = {}
    for name, records in payloads.items():
        path = directory / f"{name}.json"
        path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        paths[name] = path
    return paths


@pytest.fixture
def json_files(tmp_path, monkeypatch, db_path):
    paths = write_json_files(tmp_path)
    monkeypatch.setattr(import_json, "ORGANIZERS_FILE", paths["organizers"])
    monkeypatch.setattr(import_json, "VENUES_FILE", paths["venues"])
    monkeypatch.setattr(import_json, "FESTIVALS_FILE", paths["festivals"])
    monkeypatch.setattr(import_json, "BOOKINGS_FILE", paths["bookings"])
    return paths


def counts(db_file):
    connection = sqlite3.connect(db_file)
    try:
        return import_json.count_rows(connection)
    finally:
        connection.close()


def test_main_creates_database_and_imports_all_records(json_files, db_path):
    import_json.main()
    assert counts(db_path) == {"organizers": 1, "venues": 2, "festivals": 1, "bookings": 2}


def test_imported_values_match_json(json_files, db_path):
    import_json.main()
    connection = get_connection()
    try:
        venue = connection.execute("SELECT * FROM venues WHERE id = 1").fetchone()
        festival = connection.execute("SELECT * FROM festivals WHERE id = 1").fetchone()
    finally:
        connection.close()
    assert (venue["name"], venue["capacity"]) == ("Городской парк", 5000)
    assert festival["date"] == "2026-06-12"
    assert festival["organizer_id"] == 1


def test_boolean_is_cancelled_becomes_integer(json_files, db_path):
    import_json.main()
    connection = get_connection()
    try:
        rows = connection.execute("SELECT id, is_cancelled FROM bookings ORDER BY id").fetchall()
    finally:
        connection.close()
    assert [(row["id"], row["is_cancelled"]) for row in rows] == [(1, 0), (2, 1)]
    assert all(isinstance(row["is_cancelled"], int) for row in rows)


def test_import_is_repeatable_without_duplicates(json_files, db_path):
    import_json.main()
    import_json.main()
    assert counts(db_path) == {"organizers": 1, "venues": 2, "festivals": 1, "bookings": 2}


def test_import_order_matters_for_foreign_keys(json_files, db_path):
    connection = get_connection(must_exist=False)
    try:
        init_schema(connection)
        with pytest.raises(sqlite3.IntegrityError):
            import_json.import_bookings(connection)
    finally:
        connection.close()


def test_failed_import_is_rolled_back(json_files, db_path):
    import_json.main()
    broken = [{"id": 9, "festival_id": 99, "venue_id": 1, "is_cancelled": False}]
    json_files["bookings"].write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(sqlite3.IntegrityError):
        import_json.main()
    assert counts(db_path) == {"organizers": 1, "venues": 2, "festivals": 1, "bookings": 2}


def test_project_database_matches_project_json_files():
    """Файл data/festival_venue.sqlite содержит ровно то, что лежит в JSON-файлах."""
    data_dir = BASE_DIR / "data"
    connection = sqlite3.connect(data_dir / "festival_venue.sqlite")
    connection.row_factory = sqlite3.Row
    try:
        for table, columns in {
            "organizers": ("id", "name"),
            "venues": ("id", "name", "capacity"),
            "festivals": ("id", "name", "date", "expected_attendees", "organizer_id"),
            "bookings": ("id", "festival_id", "venue_id", "is_cancelled"),
        }.items():
            records = json.loads((data_dir / f"{table}.json").read_text(encoding="utf-8"))
            expected = [
                tuple(int(r[c]) if c == "is_cancelled" else r[c] for c in columns) for r in records
            ]
            rows = connection.execute(
                f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
            ).fetchall()
            assert [tuple(row) for row in rows] == sorted(expected), table
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()
