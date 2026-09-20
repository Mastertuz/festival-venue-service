from models.venues import (
    add_venue,
    check_venue_capacity,
    filter_venues_by_capacity,
    find_venue,
    sort_venues,
)


def test_add_venue():
    venues = {}
    venue_id = add_venue(venues, "Городской парк", 5000)
    assert venue_id == 1
    assert len(venues) == 1


def test_find_venue():
    venues = {}
    add_venue(venues, "Городской парк", 5000)
    assert find_venue(venues, "парк")


def test_check_venue_capacity():
    venues = {}
    add_venue(venues, "Концертный зал", 2000)
    assert check_venue_capacity(venues, 1, 1500)
    assert not check_venue_capacity(venues, 1, 2500)


def test_filter_venues_by_capacity():
    venues = {}
    add_venue(venues, "Малый зал", 300)
    add_venue(venues, "Большой парк", 5000)
    result = filter_venues_by_capacity(venues, 1000)
    assert len(result) == 1
    assert result[0]["name"] == "Большой парк"


def test_sort_venues():
    venues = {}
    add_venue(venues, "Большой парк", 5000)
    add_venue(venues, "Малый зал", 300)
    result = sort_venues(venues)
    assert [venue["capacity"] for venue in result] == [300, 5000]
