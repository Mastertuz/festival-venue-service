from datetime import date

from django.shortcuts import render
from django.views.generic import TemplateView

from bookings.models import Booking
from festivals.models import Festival
from venue_service.utils import DataMixin


class HomePageView(DataMixin, TemplateView):
    """Главная страница: шаблон и данные сводки формирует классовое представление."""

    template_name = "homepage/index.html"
    title_page = "Главная"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Количество активных бронирований (агрегат count()) и три ближайших фестиваля вместе
        # с организаторами одним запросом (select_related); порядок по дате задан в Meta
        # модели, срез [:3] превращается в LIMIT 3.
        context["active_bookings_count"] = Booking.objects.active().count()
        context["next_festivals"] = Festival.objects.select_related("organizer").filter(
            date__gte=date.today()
        )[:3]
        return context


def page_not_found(request, exception):
    """Обработчик 404: страница проекта вместо служебной страницы Django."""
    return render(request, "homepage/404.html", status=404)
