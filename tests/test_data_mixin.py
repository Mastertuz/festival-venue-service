"""ПР13: примесь DataMixin и главная страница на TemplateView."""

import pytest
from django.test import Client, RequestFactory
from django.views.generic import ListView, TemplateView

from homepage.views import HomePageView
from venue_service.utils import DataMixin

pytestmark = pytest.mark.django_db


class TitledView(DataMixin, TemplateView):
    template_name = "homepage/index.html"
    title_page = "Первая страница"


class OtherView(DataMixin, TemplateView):
    template_name = "homepage/index.html"
    title_page = "Вторая страница"


class UntitledView(DataMixin, TemplateView):
    template_name = "homepage/index.html"


class WithExtraView(DataMixin, TemplateView):
    template_name = "homepage/index.html"
    title_page = "С данными"
    extra_context = {"page_description": "Описание"}


# --- примесь ---------------------------------------------------------------------------


def test_mixin_defaults():
    assert DataMixin.title_page is None
    assert DataMixin.paginate_by == 5
    assert DataMixin.extra_context == {}


def test_title_page_goes_to_extra_context():
    view = TitledView()
    assert view.extra_context == {"title": "Первая страница"}


def test_views_do_not_share_extra_context():
    first, second, plain = TitledView(), OtherView(), UntitledView()
    assert first.extra_context == {"title": "Первая страница"}
    assert second.extra_context == {"title": "Вторая страница"}
    assert "title" not in plain.extra_context
    # общий словарь класса не изменяется
    assert DataMixin.extra_context == {}
    assert TitledView.extra_context == {}


def test_own_extra_context_is_kept_and_not_mutated():
    view = WithExtraView()
    assert view.extra_context == {"page_description": "Описание", "title": "С данными"}
    assert WithExtraView.extra_context == {"page_description": "Описание"}


def test_get_mixin_context_adds_title_and_values():
    context = TitledView().get_mixin_context({"a": 1}, b=2)
    assert context == {"a": 1, "title": "Первая страница", "b": 2}
    assert "title" not in UntitledView().get_mixin_context({"a": 1})


def test_get_mixin_context_can_be_used_for_dynamic_titles():
    class DynamicView(DataMixin, TemplateView):
        title_page = "Базовый"

    context = DynamicView().get_mixin_context({}, title="Динамический")
    assert context["title"] == "Динамический"


def test_mixin_comes_first_so_its_paginate_by_wins():
    class PlainList(ListView):
        model = None

    class MixedList(DataMixin, ListView):
        model = None

    assert PlainList.paginate_by is None
    assert MixedList.paginate_by == 5
    assert MixedList.__mro__.index(DataMixin) < MixedList.__mro__.index(ListView)


def test_paginate_by_can_be_overridden_in_subclass():
    class SmallList(DataMixin, ListView):
        model = None
        paginate_by = 2

    assert SmallList.paginate_by == 2


# --- главная страница: TemplateView ----------------------------------------------------


def test_home_page_is_a_template_view_with_mixin():
    assert issubclass(HomePageView, TemplateView)
    assert issubclass(HomePageView, DataMixin)
    assert HomePageView.template_name == "homepage/index.html"
    assert HomePageView.__mro__.index(DataMixin) < HomePageView.__mro__.index(TemplateView)


def test_home_page_route_uses_class_based_view():
    from django.urls import resolve

    match = resolve("/")
    assert match.view_name == "homepage:index"
    assert match.func.view_class is HomePageView


def test_home_page_renders_template_and_context(orm_data):
    response = Client().get("/")
    html = " ".join(response.content.decode().split())
    assert response.status_code == 200
    assert "homepage/index.html" in [t.name for t in response.templates]
    assert response.context["title"] == "Главная"
    assert response.context["active_bookings_count"] == 1
    assert [f.name for f in response.context["next_festivals"]] == ["Фестиваль уличной музыки"]
    assert "<title>Главная – Festival Venue Service</title>" in html


def test_home_page_title_is_the_same_for_two_requests(orm_data):
    client = Client()
    first = client.get("/").context["title"]
    client.get("/venues/")
    assert client.get("/").context["title"] == first == "Главная"


def test_home_page_context_is_built_in_get_context_data():
    request = RequestFactory().get("/")
    view = HomePageView()
    view.setup(request)
    context = view.get_context_data()
    assert {"title", "active_bookings_count", "next_festivals"} <= set(context)
