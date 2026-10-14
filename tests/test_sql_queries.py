import re
import sqlite3

import pytest

from db.database import BASE_DIR

QUERIES_FILE = BASE_DIR / "sql" / "queries.sql"
PROJECT_DB = BASE_DIR / "data" / "festival_venue.sqlite"

# Число строк, которое должен вернуть каждый запрос на данных проекта.
EXPECTED_ROW_COUNTS = {
    1: 4,
    2: 3,
    3: 7,
    4: 2,
    5: 1,
    6: 4,
    7: 7,
    8: 1,
    9: 7,
    10: 8,
    11: 7,
    12: 1,
    13: 3,
    14: 2,
    15: 1,
    16: 1,
    17: 1,
    18: 4,
    19: 3,
    20: 1,
    21: 2,
    22: 3,
    23: 0,
}


def load_queries():
    """Разобрать sql/queries.sql: вернуть {номер: текст запроса без комментариев}."""
    text = QUERIES_FILE.read_text(encoding="utf-8")
    parts = re.split(r"^-- Запрос (\d+)\.", text, flags=re.MULTILINE)
    queries = {}
    for number, body in zip(parts[1::2], parts[2::2]):
        # первая строка — остаток заголовка «-- Запрос N. описание»
        lines = [line for line in body.splitlines()[1:] if not line.lstrip().startswith("--")]
        queries[int(number)] = "\n".join(lines).strip()
    return queries


@pytest.fixture(scope="module")
def project_db():
    connection = sqlite3.connect(f"file:{PROJECT_DB}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


QUERIES = load_queries()


def run(connection, number):
    return connection.execute(QUERIES[number]).fetchall()


def test_file_contains_at_least_ten_numbered_queries():
    assert len(QUERIES) >= 10
    assert sorted(QUERIES) == list(range(1, len(QUERIES) + 1))


def test_every_query_is_a_read_only_select_ending_with_semicolon():
    for number, query in QUERIES.items():
        assert query.startswith("SELECT"), number
        assert query.rstrip().endswith(";"), number


def test_every_query_has_a_description_comment():
    text = QUERIES_FILE.read_text(encoding="utf-8")
    for number in QUERIES:
        assert re.search(rf"^-- Запрос {number}\. \S", text, flags=re.MULTILINE), number


def test_minimum_two_queries_of_each_kind():
    def count(pattern):
        return sum(1 for q in QUERIES.values() if re.search(pattern, q, flags=re.IGNORECASE))

    lists = sum(1 for q in QUERIES.values() if not re.search(r"\b(WHERE|JOIN|GROUP BY)\b", q))
    assert lists >= 2, "списки (SELECT)"
    assert count(r"\bWHERE\b") >= 2, "WHERE"
    assert count(r"\bJOIN\b") >= 2, "JOIN"
    assert count(r"\b(COUNT|MIN|MAX|AVG|SUM)\(") >= 2, "агрегатные функции"
    assert count(r"\bGROUP BY\b") >= 2, "GROUP BY"
    assert count(r"\bHAVING\b") >= 1, "HAVING"


@pytest.mark.parametrize("number", sorted(EXPECTED_ROW_COUNTS))
def test_query_returns_expected_number_of_rows(project_db, number):
    assert len(run(project_db, number)) == EXPECTED_ROW_COUNTS[number]


def test_filter_and_join_results(project_db):
    assert [r["name"] for r in run(project_db, 4)] == ["Городской парк", "Набережная реки"]
    assert {r["name"] for r in run(project_db, 14)} == {"Городской парк", "Набережная реки"}
    assert [r["id"] for r in run(project_db, 7)] == [1, 2, 3, 4, 5, 7, 8]
    cancelled = [r["id"] for r in run(project_db, 10) if r["is_cancelled"]]
    assert cancelled == [6]
    assert run(project_db, 12)[0]["organizer_name"] == "АНО «Арт-Ивент»"


def test_aggregate_queries(project_db):
    assert run(project_db, 15)[0]["bookings_count"] == 7
    summary = tuple(run(project_db, 16)[0])
    assert summary == (4, 1000, 8000, 4000.0, 16000)
    assert run(project_db, 17)[0]["busy_count"] == 1


def test_group_by_and_having_results(project_db):
    by_venue = [(r["venue_name"], r["bookings_count"]) for r in run(project_db, 18)]
    assert by_venue[0] == ("Городской парк", 3)
    assert by_venue[-1] == ("Летняя эстрада", 0)  # LEFT JOIN сохраняет площадку без бронирований
    by_organizer = [(r["organizer_name"], r["total_attendees"]) for r in run(project_db, 19)]
    assert by_organizer[0] == ("АНО «Арт-Ивент»", 11500)
    popular = [(r["venue_name"], r["bookings_count"]) for r in run(project_db, 20)]
    assert popular == [("Городской парк", 3)]


def test_empty_result_is_not_an_error(project_db):
    assert run(project_db, 23) == []
