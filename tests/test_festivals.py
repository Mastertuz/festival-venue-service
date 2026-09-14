from datetime import date

import pytest

from models.festivals import (
    add_festival,
    filter_festivals_by_min_attendees,
    find_festival,
    sort_festivals_by_date,
)
from models.organizers import add_organizer


def make_organizers():
    organizers = {}
    add_organizer(organizers, "АНО «Арт-Ивент»")
    return organizers


def test_add_festival():
    organizers = make_organizers()
    festivals = {}
    festival_id = add_festival(
        festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1,
    )
    assert festival_id == 1
    assert festivals[1]["organizer_id"] == 1


def test_add_festival_missing_organizer_raises_error():
    festivals = {}
    with pytest.raises(KeyError):
        add_festival(festivals, {}, "Фестиваль", date(2026, 6, 12), 100, 99)


def test_find_festival():
    organizers = make_organizers()
    festivals = {}
    add_festival(festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1)
    assert find_festival(festivals, "музыки")


def test_filter_festivals_by_min_attendees():
    organizers = make_organizers()
    festivals = {}
    add_festival(festivals, organizers, "Камерный концерт", date(2026, 5, 1), 100, 1)
    add_festival(festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1)
    result = filter_festivals_by_min_attendees(festivals, 1000)
    assert len(result) == 1
    assert result[0]["name"] == "Фестиваль уличной музыки"


def test_sort_festivals_by_date():
    organizers = make_organizers()
    festivals = {}
    add_festival(festivals, organizers, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, 1)
    add_festival(festivals, organizers, "Камерный концерт", date(2026, 5, 1), 100, 1)
    result = sort_festivals_by_date(festivals)
    assert [f["name"] for f in result] == ["Камерный концерт", "Фестиваль уличной музыки"]
