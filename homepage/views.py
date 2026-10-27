from datetime import date

from django.shortcuts import render

from bookings.models import Booking
from festivals.models import Festival


def index(request):
    context = {
        # Количество активных бронирований (агрегат count()).
        "active_bookings_count": Booking.objects.filter(is_cancelled=False).count(),
        # Три ближайших фестиваля вместе с организаторами одним запросом (select_related);
        # порядок по дате задан в Meta модели, срез [:3] превращается в LIMIT 3.
        "next_festivals": Festival.objects.select_related("organizer").filter(
            date__gte=date.today()
        )[:3],
    }

    return render(request, "homepage/index.html", context)


def page_not_found(request, exception):
    """Обработчик 404: страница проекта вместо служебной страницы Django."""
    return render(request, "homepage/404.html", status=404)
