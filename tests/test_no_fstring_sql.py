import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXECUTE_METHODS = {"execute", "executemany", "executescript"}
SOURCES = [
    *sorted((ROOT / "db").glob("*.py")),
    ROOT / "homepage" / "views.py",
    ROOT / "venues" / "views.py",
    ROOT / "bookings" / "views.py",
]


def unsafe_sql_calls(path):
    """Найти вызовы execute*(), в которых SQL собирается f-строкой, + или .format()."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    problems = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in EXECUTE_METHODS or not node.args:
            continue
        query = node.args[0]
        if isinstance(query, ast.JoinedStr):
            problems.append((node.lineno, "f-строка"))
        elif isinstance(query, ast.BinOp):
            problems.append((node.lineno, "конкатенация или %"))
        elif (
            isinstance(query, ast.Call)
            and isinstance(query.func, ast.Attribute)
            and query.func.attr == "format"
        ):
            problems.append((node.lineno, ".format()"))
    return problems


def test_sql_is_never_built_from_user_values_with_string_formatting():
    for path in SOURCES:
        assert unsafe_sql_calls(path) == [], path.name


def test_guard_detects_fstring_sql(tmp_path):
    sample = tmp_path / "bad.py"
    sample.write_text('conn.execute(f"SELECT * FROM venues WHERE id = {x}")\n', encoding="utf-8")
    assert unsafe_sql_calls(sample) == [(1, "f-строка")]
