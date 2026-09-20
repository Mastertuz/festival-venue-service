import pytest

from models.organizers import add_organizer, find_organizer, get_organizer


def test_add_organizer():
    organizers = {}
    organizer_id = add_organizer(organizers, "АНО «Арт-Ивент»")
    assert organizer_id == 1
    assert len(organizers) == 1


def test_find_organizer():
    organizers = {}
    add_organizer(organizers, "АНО «Арт-Ивент»")
    assert find_organizer(organizers, "арт")


def test_get_organizer():
    organizers = {}
    add_organizer(organizers, "АНО «Арт-Ивент»")
    organizer = get_organizer(organizers, 1)
    assert organizer["name"] == "АНО «Арт-Ивент»"


def test_get_organizer_missing_raises_error():
    organizers = {}
    with pytest.raises(KeyError):
        get_organizer(organizers, 99)
