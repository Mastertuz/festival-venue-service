"""ПР11: форма фильтрации бронирований BookingFilterForm (forms.Form, GET-запрос)."""

from datetime import date

import pytest
from django.test import Client

from bookings.forms import DIRECTION_CHOICES, SORT_CHOICES, BookingFilterForm
from bookings.views import DEFAULT_SORT, SORT_FIELDS

pytestmark = pytest.mark.django_db


def squashed(response):
    return " ".join(response.content.decode().split())


def get(params=None):
    return Client().get("/bookings/", params or {})


# --- устройство формы --------------------------------------------------------


def test_form_fields_match_get_parameters_and_are_optional():
    form = BookingFilterForm()
    assert list(form.fields) == ["q", "date", "venue", "organizer", "sort", "dir", "active"]
    assert not any(field.required for field in form.fields.values())
    assert "page" not in form.fields  # номер страницы относится к пагинации, а не к фильтрам


def test_sort_choices_and_view_whitelist_have_the_same_values():
    assert [value for value, _ in SORT_CHOICES] == list(SORT_FIELDS)
    assert DEFAULT_SORT in SORT_FIELDS
    assert [value for value, _ in DIRECTION_CHOICES] == ["asc", "desc"]


def test_form_widgets_use_bootstrap_classes_and_date_input():
    form = BookingFilterForm()
    # Атрибут type виджет Input переносит в свойство input_type.
    assert form.fields["date"].widget.input_type == "date"
    assert form.fields["date"].widget.format == "%Y-%m-%d"
    for name in ("q", "date"):
        assert form.fields[name].widget.attrs["class"] == "form-control"
    for name in ("venue", "organizer", "sort", "dir"):
        assert form.fields[name].widget.attrs["class"] == "form-select"
    assert form.fields["active"].widget.attrs["class"] == "form-check-input"


def test_form_choice_fields_use_queryset_of_existing_objects(orm_data):
    form = BookingFilterForm()
    assert set(form.fields["venue"].queryset) == {orm_data["park"], orm_data["arena"]}
    assert list(form.fields["organizer"].queryset) == [orm_data["organizer"]]
    assert form.fields["venue"].empty_label == "Все площадки"
    assert form.fields["organizer"].empty_label == "Все организаторы"


# --- проверка данных ---------------------------------------------------------


def test_valid_data_is_converted_to_python_objects(orm_data):
    form = BookingFilterForm(
        {
            "date": "2030-01-10",
            "venue": orm_data["park"].pk,
            "organizer": orm_data["organizer"].pk,
            "sort": "venue",
            "dir": "desc",
            "active": "1",
            "q": "парк",
        }
    )
    assert form.is_valid(), form.errors
    cleaned = form.cleaned_data
    assert cleaned["date"] == date(2030, 1, 10)
    assert cleaned["venue"] == orm_data["park"]
    assert cleaned["organizer"] == orm_data["organizer"]
    assert cleaned["sort"] == "venue" and cleaned["dir"] == "desc"
    assert cleaned["active"] is True and cleaned["q"] == "парк"


def test_empty_form_is_valid_and_has_empty_values():
    form = BookingFilterForm({})
    assert form.is_valid()
    assert form.cleaned_data["date"] is None
    assert form.cleaned_data["venue"] is None
    assert form.cleaned_data["sort"] == ""
    assert form.cleaned_data["active"] is False


@pytest.mark.parametrize(
    "field, value",
    [
        ("date", "не_дата"),
        ("date", "2030-02-31"),
        ("venue", "999999"),
        ("venue", "abc"),
        ("organizer", "-1"),
        ("sort", "unknown"),
        ("sort", "festival__organizer__name"),
        ("dir", "up"),
        ("q", "я" * 101),
    ],
)
def test_invalid_values_are_rejected_with_error_on_the_field(orm_data, field, value):
    form = BookingFilterForm({field: value})
    assert not form.is_valid()
    assert list(form.errors) == [field]


def test_error_messages_are_in_russian(orm_data):
    form = BookingFilterForm({"date": "x", "venue": "99", "organizer": "99", "sort": "x"})
    assert not form.is_valid()
    assert form.errors["date"] == ["Укажите корректную дату."]
    assert form.errors["venue"] == ["Выберите площадку из списка."]
    assert form.errors["organizer"] == ["Выберите организатора из списка."]
    assert form.errors["sort"] == ["Выберите вариант сортировки из списка."]


def test_date_accepts_iso_and_local_formats():
    assert BookingFilterForm({"date": "2030-01-10"}).is_valid()
    local = BookingFilterForm({"date": "10.01.2030"})
    assert local.is_valid() and local.cleaned_data["date"] == date(2030, 1, 10)


# --- работа формы в представлении ---------------------------------------------


def test_page_is_opened_with_unbound_form_without_parameters(orm_data):
    response = get()
    form = response.context["form"]
    assert isinstance(form, BookingFilterForm)
    assert not form.is_bound
    assert response.context["error"] is None
    assert response.context["total_count"] == 2
    assert response.context["sort"] == DEFAULT_SORT


def test_form_is_bound_when_parameters_are_passed(orm_data):
    response = get({"sort": "venue"})
    form = response.context["form"]
    assert form.is_bound and form.is_valid()
    assert response.context["sort"] == "venue"


def test_only_page_parameter_is_not_a_form_error(orm_data):
    response = get({"page": "1"})
    assert response.context["error"] is None
    assert response.context["form"].is_valid()


def test_invalid_form_shows_general_and_field_errors_and_does_not_filter(orm_data):
    response = get({"date": "не_дата", "venue": orm_data["park"].pk, "active": "1"})
    html = squashed(response)
    assert response.status_code == 200
    assert response.context["error"] == "Проверьте введённые значения фильтров."
    assert "Проверьте введённые значения фильтров." in html
    assert "Укажите корректную дату." in html
    # непроверенные данные не используются: ни площадка, ни статус не применяются
    assert response.context["total_count"] == 2
    assert response.context["only_active"] is False


def test_unknown_sort_is_reported_and_default_sort_is_used(orm_data):
    response = get({"sort": "unknown"})
    assert "Выберите вариант сортировки из списка." in squashed(response)
    assert response.context["sort"] == DEFAULT_SORT
    assert response.status_code == 200


def test_unknown_direction_is_reported(orm_data):
    response = get({"dir": "up"})
    assert "Выберите порядок сортировки из списка." in squashed(response)
    assert response.context["descending"] is False


def test_valid_form_applies_all_filters_together(orm_data):
    response = get(
        {
            "venue": orm_data["park"].pk,
            "organizer": orm_data["organizer"].pk,
            "date": orm_data["festival"].date.isoformat(),
            "active": "1",
        }
    )
    assert response.context["error"] is None
    assert [row["id"] for row in response.context["bookings"]] == [orm_data["active"].pk]


def test_active_filter_still_uses_booking_queryset_method(orm_data):
    # Отменённое бронирование показывается в общем списке и скрывается фильтром «Только активные».
    assert get().context["total_count"] == 2
    assert get({"active": "1"}).context["total_count"] == 1


def test_filter_form_is_rendered_field_by_field_with_labels(orm_data):
    html = squashed(get())
    for label in (
        "Поиск",
        "Дата фестиваля",
        "Площадка",
        "Организатор",
        "Сортировать по",
        "Порядок",
        "Только активные",
    ):
        assert label in html, label
    assert 'type="date"' in html
    assert 'class="form-select"' in html
    assert "Все площадки" in html and "Все организаторы" in html


def test_selected_values_are_kept_in_the_rendered_form(orm_data):
    html = squashed(get({"venue": orm_data["arena"].pk, "sort": "festival", "dir": "desc"}))
    assert f'<option value="{orm_data["arena"].pk}" selected>' in html
    assert '<option value="festival" selected>' in html
    assert '<option value="desc" selected>' in html


def test_form_does_not_change_data_in_the_database(orm_data):
    from bookings.models import Booking

    before = list(Booking.objects.values_list("pk", "status"))
    get({"venue": orm_data["park"].pk, "sort": "date"})
    assert list(Booking.objects.values_list("pk", "status")) == before
