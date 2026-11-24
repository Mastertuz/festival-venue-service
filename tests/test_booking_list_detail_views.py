"""ПР13: BookingListView (ListView, пагинация, контекст) и BookingDetailView (DetailView)."""

import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.test import Client
from django.views.generic import DetailView, ListView

import bookings.views as booking_views
from bookings.models import Booking
from bookings.views import BookingDetailView, BookingListView
from festivals.models import Festival, Organizer
from venue_service.utils import DataMixin
from venues.models import Venue

pytestmark = pytest.mark.django_db

DAY = date(2031, 3, 1)


def squashed(response):
    return " ".join(response.content.decode().split())


@pytest.fixture
def seven(db):
    """Семь активных бронирований на разные даты (две страницы по пять записей)."""
    organizer = Organizer.objects.create(name="Организатор")
    venue = Venue.objects.create(name="Площадка", capacity=1000)
    bookings = []
    for index in range(7):
        festival = Festival.objects.create(
            name=f"Фестиваль {index}",
            date=DAY + timedelta(days=index),
            expected_attendees=10,
            organizer=organizer,
        )
        bookings.append(Booking.objects.create(festival=festival, venue=venue))
    return {"venue": venue, "organizer": organizer, "bookings": bookings}


# --- класс списка ------------------------------------------------------------------------


def test_list_view_class_is_configured_as_in_the_task():
    assert issubclass(BookingListView, ListView)
    assert BookingListView.__mro__.index(DataMixin) < BookingListView.__mro__.index(ListView)
    assert BookingListView.model is Booking
    assert BookingListView.template_name == "bookings/booking_list.html"
    assert BookingListView.context_object_name == "bookings"
    assert BookingListView.title_page == "Бронирования"
    assert BookingListView.extra_context == {
        "page_description": "Просмотр, поиск и фильтрация бронирований"
    }
    assert BookingListView.allow_empty is True
    assert "allow_empty" in vars(BookingListView)  # задан в самом классе


def test_pagination_size_comes_from_the_mixin_and_is_not_set_in_the_class():
    assert "paginate_by" not in vars(BookingListView)
    assert BookingListView.paginate_by == DataMixin.paginate_by == 5


def test_manual_paginator_is_removed_from_views():
    source = Path(booking_views.__file__).read_text(encoding="utf-8")
    assert "Paginator(" not in source
    assert "get_page(" not in source
    assert "BOOKINGS_PER_PAGE" not in source


def test_list_route_uses_the_class_based_view():
    from django.urls import resolve

    assert resolve("/bookings/").func.view_class is BookingListView


# --- пагинация ListView --------------------------------------------------------------------


def test_list_context_has_listview_pagination_variables(seven):
    response = Client().get("/bookings/")
    context = response.context
    assert response.status_code == 200
    assert len(context["bookings"]) == 5
    assert context["is_paginated"] is True
    assert context["page_obj"].number == 1
    assert context["paginator"].num_pages == 2
    assert context["paginator"].count == 7


def test_second_page_has_the_rest_and_navigation_marks_it(seven):
    response = Client().get("/bookings/", {"page": 2})
    assert [row["festival_name"] for row in response.context["bookings"]] == [
        "Фестиваль 5",
        "Фестиваль 6",
    ]
    assert 'aria-current="page"> <span class="page-link">2</span>' in squashed(response)


def test_navigation_is_hidden_when_one_page_is_enough(db, orm_data):
    response = Client().get("/bookings/")
    assert response.context["is_paginated"] is False
    assert "Навигация по страницам" not in response.content.decode()


def test_pagination_links_keep_filters_with_querystring_tag(seven):
    params = {"venue": seven["venue"].pk, "sort": "festival", "dir": "desc"}
    html = Client().get("/bookings/", params).content.decode()
    link = next(line for line in html.splitlines() if "page=2" in line)
    assert "venue=" in link and "sort=festival" in link and "dir=desc" in link
    assert "{% querystring" in Path("bookings/templates/bookings/booking_list.html").read_text()


def test_nonexistent_page_gives_404_and_empty_filter_result_is_not_404(seven):
    assert Client().get("/bookings/", {"page": 3}).status_code == 404
    # allow_empty = True: фильтр без результатов открывается и показывает сообщение
    response = Client().get("/bookings/", {"q": "нет такого"})
    assert response.status_code == 200
    assert "Бронирования не найдены." in squashed(response)
    assert response.context["total_count"] == 0


# --- дополнительный контекст --------------------------------------------------------------


def test_static_context_title_and_description(seven):
    response = Client().get("/bookings/")
    html = squashed(response)
    assert response.context["title"] == "Бронирования"
    assert response.context["page_description"] == "Просмотр, поиск и фильтрация бронирований"
    assert "<title>Бронирования – Festival Venue Service</title>" in html
    assert '<h1 class="mb-0">Бронирования</h1>' in html
    assert "Просмотр, поиск и фильтрация бронирований" in html


def test_dynamic_total_counts_all_rows_matching_filters_not_only_the_page(seven):
    client = Client()
    assert client.get("/bookings/").context["total_count"] == 7
    assert client.get("/bookings/", {"page": 2}).context["total_count"] == 7
    assert client.get("/bookings/", {"date": DAY.isoformat()}).context["total_count"] == 1
    assert "Всего бронирований: 7" in squashed(client.get("/bookings/"))


def test_dynamic_total_does_not_add_a_query(seven, django_assert_num_queries):
    # count и выборка страницы, списки площадок и организаторов в форме, счётчик процессора
    with django_assert_num_queries(5):
        Client().get("/bookings/")


def test_filter_state_is_exposed_in_context(seven):
    response = Client().get("/bookings/", {"sort": "venue", "dir": "desc", "active": "on"})
    assert response.context["sort"] == "venue"
    assert response.context["descending"] is True
    assert response.context["only_active"] is True
    assert response.context["error"] is None
    assert response.context["form"].is_bound


def test_invalid_filter_shows_error_and_does_not_filter(seven):
    response = Client().get("/bookings/", {"date": "не_дата"})
    assert response.context["error"] == "Проверьте введённые значения фильтров."
    assert response.context["total_count"] == 7


# --- карточка бронирования -----------------------------------------------------------------


def test_detail_view_class_is_configured_as_in_the_task():
    assert issubclass(BookingDetailView, DetailView)
    assert BookingDetailView.__mro__.index(DataMixin) < BookingDetailView.__mro__.index(DetailView)
    assert BookingDetailView.model is Booking
    assert BookingDetailView.template_name == "bookings/booking_detail.html"
    assert BookingDetailView.context_object_name == "booking"
    assert BookingDetailView.pk_url_kwarg == "booking_id"


def test_detail_route_uses_the_class_based_view():
    from django.urls import resolve

    match = resolve("/bookings/1/")
    assert match.func.view_class is BookingDetailView
    assert match.kwargs == {"booking_id": 1}


def test_detail_page_shows_booking_with_related_objects(seven):
    booking = seven["bookings"][0]
    response = Client().get(f"/bookings/{booking.pk}/")
    html = squashed(response)
    assert response.status_code == 200
    assert response.context["booking"] == booking
    assert "Фестиваль 0" in html and "Организатор" in html and "Площадка" in html
    assert re.search(r"01\.03\.2031", html)


def test_detail_title_is_built_dynamically_with_booking_number(seven):
    booking = seven["bookings"][3]
    response = Client().get(f"/bookings/{booking.pk}/")
    assert response.context["title"] == f"Бронирование №{booking.pk}"
    assert f"<title>Бронирование №{booking.pk} – Festival Venue Service</title>" in squashed(
        response
    )


def test_detail_loads_related_objects_in_one_query(seven):
    booking = seven["bookings"][0]
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    view = BookingDetailView()
    with CaptureQueriesContext(connection) as queries:
        obj = view.get_queryset().get(pk=booking.pk)
        obj.festival.organizer.name
        obj.venue.name
    assert len(queries) == 1


def test_detail_of_missing_booking_gives_404(seven):
    assert Client().get("/bookings/999999/").status_code == 404
