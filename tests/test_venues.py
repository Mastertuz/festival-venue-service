import pytest

from models.venues import (
    Venue,
    add_venue,
    filter_venues_by_capacity,
    find_venue,
    get_venue,
    sort_venues,
)


def test_venue_creation():
    venue = Venue(1, "Городской парк", 5000)
    assert venue.id == 1
    assert venue.name == "Городской парк"
    assert venue.capacity == 5000


def test_venue_is_suitable_for():
    venue = Venue(1, "Городской парк", 5000)
    assert venue.is_suitable_for(4500)
    assert not venue.is_suitable_for(6000)


def test_venue_str():
    venue = Venue(1, "Городской парк", 5000)
    assert str(venue) == "Городской парк (вместимость 5000 чел.)"


def test_venue_validate_capacity():
    assert Venue.validate_capacity(30)
    assert not Venue.validate_capacity(0)
    assert not Venue.validate_capacity(-5)


def test_venue_from_data_and_to_data_roundtrip():
    data = {"id": 1, "name": "Городской парк", "capacity": 5000}
    venue = Venue.from_data(data)
    assert venue.to_data() == data


def test_add_venue():
    venues: list[Venue] = []
    venue = add_venue(venues, "Городской парк", 5000)
    assert venue.id == 1
    assert len(venues) == 1
    assert venues[0] is venue


def test_add_venue_invalid_capacity_raises_error():
    venues: list[Venue] = []
    with pytest.raises(ValueError):
        add_venue(venues, "Без вместимости", 0)


def test_find_venue():
    venues: list[Venue] = []
    add_venue(venues, "Городской парк", 5000)
    assert find_venue(venues, "парк")


def test_get_venue_missing_raises_error():
    venues: list[Venue] = []
    with pytest.raises(KeyError):
        get_venue(venues, 99)


def test_filter_venues_by_capacity():
    venues: list[Venue] = []
    add_venue(venues, "Малый зал", 300)
    add_venue(venues, "Большой парк", 5000)
    result = filter_venues_by_capacity(venues, 1000)
    assert len(result) == 1
    assert result[0].name == "Большой парк"


def test_sort_venues():
    venues: list[Venue] = []
    add_venue(venues, "Большой парк", 5000)
    add_venue(venues, "Малый зал", 300)
    result = sort_venues(venues)
    assert [venue.capacity for venue in result] == [300, 5000]
