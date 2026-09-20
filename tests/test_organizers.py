import pytest

from models.organizers import (
    Organizer,
    add_organizer,
    find_organizer,
    get_organizer,
    show_organizers,
)


def test_organizer_creation():
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    assert organizer.id == 1
    assert organizer.name == "АНО «Арт-Ивент»"


def test_organizer_str():
    organizer = Organizer(1, "АНО «Арт-Ивент»")
    assert str(organizer) == "АНО «Арт-Ивент»"


def test_organizer_from_data_and_to_data_roundtrip():
    data = {"id": 1, "name": "АНО «Арт-Ивент»"}
    organizer = Organizer.from_data(data)
    assert organizer.to_data() == data


def test_add_organizer():
    organizers: list[Organizer] = []
    organizer = add_organizer(organizers, "АНО «Арт-Ивент»")
    assert organizer.id == 1
    assert len(organizers) == 1


def test_find_organizer():
    organizers: list[Organizer] = []
    add_organizer(organizers, "АНО «Арт-Ивент»")
    assert find_organizer(organizers, "арт")


def test_get_organizer():
    organizers: list[Organizer] = []
    add_organizer(organizers, "АНО «Арт-Ивент»")
    organizer = get_organizer(organizers, 1)
    assert organizer.name == "АНО «Арт-Ивент»"


def test_get_organizer_missing_raises_error():
    organizers: list[Organizer] = []
    with pytest.raises(KeyError):
        get_organizer(organizers, 99)


def test_show_organizers(capsys):
    organizers: list[Organizer] = []
    show_organizers(organizers)
    assert "пуст" in capsys.readouterr().out
    add_organizer(organizers, "АНО «Арт-Ивент»")
    show_organizers(organizers)
    assert "1. АНО «Арт-Ивент»" in capsys.readouterr().out
