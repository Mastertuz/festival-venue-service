import json
from datetime import date
from pathlib import Path

from models.festivals import Festival
from models.organizers import Organizer
from models.schedule import Booking
from models.venues import Venue
from storage import (
    load_bookings,
    load_festivals,
    load_organizers,
    load_venues,
    save_bookings,
    save_festivals,
    save_organizers,
    save_venues,
)


def write_json(path: Path, data: list[dict]) -> str:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


def make_objects() -> tuple[list[Venue], list[Organizer], list[Festival]]:
    venues = [Venue(1, "Городской парк", 5000)]
    organizers = [Organizer(1, "АНО «Арт-Ивент»")]
    festivals = [Festival(1, "Фестиваль уличной музыки", date(2026, 6, 12), 4500, organizers[0])]
    return venues, organizers, festivals


def test_load_venues_creates_venue_objects(tmp_path):
    filename = write_json(tmp_path / "venues.json", [{"id": 1, "name": "Парк", "capacity": 5000}])
    venues = load_venues(filename)
    assert isinstance(venues[0], Venue)
    assert (venues[0].id, venues[0].name, venues[0].capacity) == (1, "Парк", 5000)


def test_save_and_load_venues_roundtrip(tmp_path):
    filename = str(tmp_path / "venues.json")
    save_venues(filename, [Venue(1, "Городской парк", 5000)])
    loaded = load_venues(filename)
    assert loaded[0].to_data() == {"id": 1, "name": "Городской парк", "capacity": 5000}


def test_save_and_load_organizers_roundtrip(tmp_path):
    filename = str(tmp_path / "organizers.json")
    save_organizers(filename, [Organizer(1, "АНО «Арт-Ивент»")])
    loaded = load_organizers(filename)
    assert isinstance(loaded[0], Organizer)
    assert loaded[0].name == "АНО «Арт-Ивент»"


def test_load_festivals_links_organizer_object(tmp_path):
    organizers = [Organizer(1, "АНО «Арт-Ивент»")]
    filename = write_json(tmp_path / "festivals.json", [{
        "id": 1, "name": "Фестиваль", "date": "2026-06-12",
        "expected_attendees": 4500, "organizer_id": 1,
    }])
    festivals = load_festivals(filename, organizers)
    assert festivals[0].organizer is organizers[0]
    assert festivals[0].date == date(2026, 6, 12)


def test_save_festivals_stores_organizer_id_and_iso_date(tmp_path):
    _, _, festivals = make_objects()
    filename = str(tmp_path / "festivals.json")
    save_festivals(filename, festivals)
    data = json.loads(Path(filename).read_text(encoding="utf-8"))
    assert data == [{
        "id": 1, "name": "Фестиваль уличной музыки", "date": "2026-06-12",
        "expected_attendees": 4500, "organizer_id": 1,
    }]


def test_load_festivals_skips_unknown_organizer(tmp_path):
    filename = write_json(tmp_path / "festivals.json", [{
        "id": 1, "name": "Фестиваль", "date": "2026-06-12",
        "expected_attendees": 100, "organizer_id": 99,
    }])
    assert load_festivals(filename, []) == []


def test_load_bookings_restores_links_and_state(tmp_path):
    venues, _, festivals = make_objects()
    filename = write_json(tmp_path / "bookings.json", [
        {"id": 1, "festival_id": 1, "venue_id": 1, "is_cancelled": True},
    ])
    bookings = load_bookings(filename, festivals, venues)
    assert bookings[0].festival is festivals[0]
    assert bookings[0].venue is venues[0]
    assert bookings[0].is_cancelled
    assert bookings[0].status == "отменено"


def test_save_bookings_stores_ids_not_objects(tmp_path):
    venues, _, festivals = make_objects()
    booking = Booking(1, festivals[0], venues[0])
    booking.cancel()
    filename = str(tmp_path / "bookings.json")
    save_bookings(filename, [booking])
    data = json.loads(Path(filename).read_text(encoding="utf-8"))
    assert data == [{"id": 1, "festival_id": 1, "venue_id": 1, "is_cancelled": True}]


def test_bookings_roundtrip_keeps_cancelled_state(tmp_path):
    venues, _, festivals = make_objects()
    booking = Booking(1, festivals[0], venues[0])
    booking.cancel()
    filename = str(tmp_path / "bookings.json")
    save_bookings(filename, [booking])
    loaded = load_bookings(filename, festivals, venues)
    assert loaded[0].is_cancelled


def test_load_bookings_skips_unknown_festival_or_venue(tmp_path):
    venues, _, festivals = make_objects()
    filename = write_json(tmp_path / "bookings.json", [
        {"id": 1, "festival_id": 99, "venue_id": 1, "is_cancelled": False},
        {"id": 2, "festival_id": 1, "venue_id": 99, "is_cancelled": False},
    ])
    assert load_bookings(filename, festivals, venues) == []


def test_load_missing_file_returns_empty_collection(tmp_path):
    assert load_venues(str(tmp_path / "нет_файла.json")) == []
    assert load_organizers(str(tmp_path / "нет_файла.json")) == []


def test_load_invalid_json_returns_empty_collection(tmp_path):
    filename = tmp_path / "broken.json"
    filename.write_text("{это не json", encoding="utf-8")
    assert load_venues(str(filename)) == []
    assert load_bookings(str(filename), [], []) == []
