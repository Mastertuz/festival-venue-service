from datetime import date

import pytest

from models.festivals import (
    Festival,
    add_festival,
    filter_festivals_by_min_attendees,
    find_festival,
    get_festival,
    show_festivals,
    sort_festivals_by_date,
)
from models.organizers import Organizer, add_organizer


def make_organizers() -> list[Organizer]:
    organizers: list[Organizer] = []
    add_organizer(organizers, "АНО «Арт-Ивент»")
    return organizers


def test_festival_creation():
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    festival = Festival(1, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, organizer)
    assert festival.id == 1
    assert festival.date == date(2026, 6, 12)
    assert festival.organizer is organizer


def test_festival_str_includes_organizer():
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    festival = Festival(1, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, organizer)
    assert "Фестиваль уличной музыки" in str(festival)
    assert "АНО «Арт-Ивент»" in str(festival)


def test_add_festival():
    organizers = make_organizers()
    festivals: list[Festival] = []
    festival = add_festival(
        festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1,
    )
    assert festival.id == 1
    assert festival.organizer.id == 1


def test_add_festival_missing_organizer_raises_error():
    festivals: list[Festival] = []
    with pytest.raises(KeyError):
        add_festival(festivals, [], "Фестиваль", date(2026, 6, 12), 100, 99)


def test_get_festival_missing_raises_error():
    with pytest.raises(KeyError):
        get_festival([], 99)


def test_find_festival():
    organizers = make_organizers()
    festivals: list[Festival] = []
    add_festival(festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1)
    assert find_festival(festivals, "музыки")


def test_filter_festivals_by_min_attendees():
    organizers = make_organizers()
    festivals: list[Festival] = []
    add_festival(festivals, organizers, "Камерный концерт", date(2026, 5, 1), 100, 1)
    add_festival(festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1)
    result = filter_festivals_by_min_attendees(festivals, 1000)
    assert len(result) == 1
    assert result[0].name == "Фестиваль уличной музыки"


def test_sort_festivals_by_date():
    organizers = make_organizers()
    festivals: list[Festival] = []
    add_festival(festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1)
    add_festival(festivals, organizers, "Камерный концерт", date(2026, 5, 1), 100, 1)
    result = sort_festivals_by_date(festivals)
    assert [f.name for f in result] == ["Камерный концерт", "Фестиваль уличной музыки"]


def test_show_festivals(capsys):
    organizers = make_organizers()
    festivals: list[Festival] = []
    show_festivals(festivals)
    assert "пуст" in capsys.readouterr().out
    add_festival(festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1)
    show_festivals(festivals)
    assert "1. Фестиваль уличной музыки — 2026-06-12" in capsys.readouterr().out
