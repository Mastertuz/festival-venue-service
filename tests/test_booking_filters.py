from datetime import date, timedelta

import pytest
from django.test import Client

from bookings.models import Booking
from festivals.models import Festival, Organizer
from venues.models import Venue

pytestmark = pytest.mark.django_db

DAY = date(2030, 1, 10)


@pytest.fixture
def many(db):
    """Восемь бронирований (7 активных и 1 отменённое), 2 организатора, 3 площадки."""
    art = Organizer.objects.create(name="Арт-Ивент")
    city = Organizer.objects.create(name="Городской центр")
    park = Venue.objects.create(name="Парк", capacity=5000)
    arena = Venue.objects.create(name="Арена", capacity=2000)
    hall = Venue.objects.create(name="Зал", capacity=300)
    plan = [
        ("Джаз", 0, city, arena, False),
        ("Кино", 1, art, park, False),
        ("Книги", 2, city, hall, False),
        ("Ночь", 3, art, park, False),
        ("Еда", 4, art, arena, False),
        ("Ремёсла", 5, city, hall, False),
        ("Танцы", 6, art, hall, False),
        ("Театр", 7, city, park, True),
    ]
    bookings = {}
    for name, offset, organizer, venue, cancelled in plan:
        festival = Festival.objects.create(
            name=name,
            date=DAY + timedelta(days=offset),
            expected_attendees=100,
            organizer=organizer,
        )
        bookings[name] = Booking.objects.create(
            festival=festival, venue=venue, is_cancelled=cancelled
        )
    return {
        "art": art,
        "city": city,
        "park": park,
        "arena": arena,
        "hall": hall,
        "bookings": bookings,
    }


def get(params=None):
    return Client().get("/bookings/", params or {})


def festival_names(response):
    return [row["festival_name"] for row in response.context["bookings"]]


def squashed(response):
    return " ".join(response.content.decode().split())


# --- пагинация ---------------------------------------------------------------


def test_first_page_has_five_bookings_and_total_is_shown(many):
    response = get()
    assert len(response.context["bookings"]) == 5
    assert "Всего бронирований: 8" in squashed(response)


def test_second_page_has_the_rest(many):
    assert festival_names(get({"page": 2})) == ["Ремёсла", "Танцы", "Театр"]


def test_navigation_is_shown_only_for_several_pages(many, orm_data):
    assert 'aria-label="Навигация по страницам"' in get().content.decode()
    Booking.objects.exclude(pk__in=[many["bookings"]["Джаз"].pk]).delete()
    assert "Навигация по страницам" not in get().content.decode()


def test_invalid_and_out_of_range_page_numbers_do_not_break_the_page(many):
    assert festival_names(get({"page": "abc"}))[0] == "Джаз"  # первая страница
    assert festival_names(get({"page": 999}))[-1] == "Театр"  # последняя страница
    assert festival_names(get({"page": 0}))[-1] == "Театр"  # номер меньше 1 — последняя страница
    assert get({"page": "abc"}).status_code == 200
    assert get({"page": 999}).status_code == 200


def test_navigation_links_keep_filters_and_sorting(many):
    html = get({"organizer": many["art"].pk, "sort": "festival", "page": 1}).content.decode()
    # у организатора «Арт-Ивент» 4 бронирования — одна страница, навигации нет
    assert "page-link" not in html
    html = get({"sort": "venue", "dir": "desc", "q": "а"}).content.decode()
    assert "page=2" in html
    link = [line for line in html.splitlines() if "page=2" in line][0]
    assert "sort=venue" in link and "dir=desc" in link and "q=" in link


def test_previous_and_next_buttons_are_disabled_on_edge_pages(many):
    first = squashed(get())
    last = squashed(get({"page": 2}))
    assert '<li class="page-item disabled"> <span class="page-link">Назад</span>' in first
    assert '<li class="page-item disabled"> <span class="page-link">Далее</span>' in last
    assert 'class="page-item active" aria-current="page"> <span class="page-link">2</span>' in last


# --- фильтры -----------------------------------------------------------------


def test_filter_by_date(many):
    assert festival_names(get({"date": "2030-01-12"})) == ["Книги"]


def test_filter_by_venue_uses_foreign_key(many):
    assert festival_names(get({"venue": many["hall"].pk})) == ["Книги", "Ремёсла", "Танцы"]


def test_filter_by_organizer_uses_related_field(many):
    names = festival_names(get({"organizer": many["art"].pk}))
    assert names == ["Кино", "Ночь", "Еда", "Танцы"]


def test_filter_active_only(many):
    response = get({"active": 1})
    assert "Театр" not in festival_names(response)
    assert response.context["total_count"] == 7


def test_several_filters_are_combined_with_and(many):
    response = get({"venue": many["park"].pk, "organizer": many["art"].pk})
    assert festival_names(response) == ["Кино", "Ночь"]
    both = get({"venue": many["park"].pk, "organizer": many["city"].pk, "active": 1})
    assert festival_names(both) == []  # у «Города» на парке только отменённый «Театр»


def test_combination_without_matches_shows_message_not_error(many):
    response = get({"venue": many["park"].pk, "date": "2030-01-12"})
    assert response.status_code == 200
    assert "Бронирования не найдены." in squashed(response)


def test_filter_form_keeps_selected_values(many):
    html = squashed(get({"venue": many["arena"].pk, "date": "2030-01-10", "q": "джаз"}))
    assert f'<option value="{many["arena"].pk}" selected' in html
    assert 'value="2030-01-10"' in html
    assert 'value="джаз"' in html


def test_invalid_date_is_reported_and_ignored(many):
    for value in ("2030-13-45", "завтра", "2030-01-10' OR '1'='1"):
        response = get({"date": value})
        assert "Укажите корректную дату." in squashed(response), value
        assert response.context["total_count"] == 8, value


def test_invalid_venue_and_organizer_are_reported_and_ignored(many):
    for param, message in (
        ("venue", "Выберите площадку из списка."),
        ("organizer", "Выберите организатора из списка."),
    ):
        for value in ("abc", "-1", "1 OR 1=1", "99999999999999999999"):
            response = get({param: value})
            assert message in squashed(response), (param, value)
            assert response.status_code == 200
            assert response.context["total_count"] == 8


def test_filter_by_unknown_identifier_gives_empty_result(many):
    assert get({"venue": 999999}).context["total_count"] == 0


# --- поиск -------------------------------------------------------------------


def test_search_by_festival_name_ignores_case(many):
    assert festival_names(get({"q": "ДЖАЗ"})) == ["Джаз"]
    assert festival_names(get({"q": "ремёсла"})) == ["Ремёсла"]


def test_search_by_venue_name(many):
    assert festival_names(get({"q": "арена"})) == ["Джаз", "Еда"]


def test_search_by_organizer_name(many):
    assert festival_names(get({"q": "городской центр"})) == ["Джаз", "Книги", "Ремёсла", "Театр"]


def test_search_checks_several_fields_at_once(many):
    # «ар» встречается в названиях площадок («Парк», «Арена») и организатора («Арт-Ивент»)
    expected = ["Джаз", "Кино", "Ночь", "Еда", "Танцы", "Театр"]
    names = festival_names(get({"q": "ар"})) + festival_names(get({"q": "ар", "page": 2}))
    assert names == expected
    assert get({"q": "ар"}).context["total_count"] == 6


def test_search_combined_with_filter(many):
    response = get({"q": "арт", "venue": many["park"].pk})
    assert festival_names(response) == ["Кино", "Ночь"]


def test_search_special_characters_are_plain_text(many):
    for value in ("%", "_", "' OR '1'='1", "\\"):
        assert get({"q": value}).context["total_count"] == 0, value


# --- сортировка --------------------------------------------------------------


def test_default_sort_is_by_date(many):
    assert festival_names(get())[:3] == ["Джаз", "Кино", "Книги"]


def test_sort_by_venue_then_identifier(many):
    response = get({"sort": "venue", "page": 1})
    venues = [row["venue_name"] for row in response.context["bookings"]]
    assert venues == sorted(venues)
    assert venues[0] == "Арена"


def test_sort_by_festival_name(many):
    names = festival_names(get({"sort": "festival"}))
    assert names == sorted(names)


def test_sort_by_organizer_name(many):
    organizers = [r["organizer_name"] for r in get({"sort": "organizer"}).context["bookings"]]
    assert organizers == sorted(organizers)


def test_descending_direction(many):
    ascending = festival_names(get({"sort": "festival", "page": 2}))
    descending = festival_names(get({"sort": "festival", "dir": "desc", "page": 2}))
    assert ascending != descending
    all_desc = [
        n
        for page in (1, 2)
        for n in festival_names(get({"sort": "festival", "dir": "desc", "page": page}))
    ]
    assert all_desc == sorted(all_desc, reverse=True)


def test_unknown_sort_value_falls_back_to_date(many):
    for value in ("festival__organizer__name", "id; DROP TABLE x", "-date", ""):
        response = get({"sort": value})
        assert response.status_code == 200, value
        assert festival_names(response)[:2] == ["Джаз", "Кино"], value
        assert response.context["sort"] == "date", value


def test_ties_are_broken_by_identifier(many):
    same_day = Festival.objects.create(
        name="В тот же день", date=DAY, expected_attendees=10, organizer=many["art"]
    )
    extra = Booking.objects.create(festival=same_day, venue=many["hall"])
    ids = [row["id"] for row in get().context["bookings"] if row["booking_date"] == DAY]
    assert ids == sorted(ids) and extra.pk in ids


def test_filter_sort_and_pagination_work_together(many):
    response = get({"active": 1, "sort": "festival", "dir": "desc", "page": 2})
    # 7 активных по убыванию названия: Танцы, Ремёсла, Ночь, Книги, Кино | Еда, Джаз
    assert festival_names(response) == ["Еда", "Джаз"]
    assert response.context["total_count"] == 7
    assert response.context["sort"] == "festival" and response.context["descending"]


def test_changing_one_parameter_changes_result(many):
    before = festival_names(get({"venue": many["hall"].pk}))
    after = festival_names(get({"venue": many["arena"].pk}))
    assert before != after


def test_query_count_does_not_depend_on_number_of_bookings(many, django_assert_num_queries):
    with django_assert_num_queries(4):
        get({"sort": "organizer"})
