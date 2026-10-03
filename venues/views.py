from datetime import date

from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape

from homepage.views import page
from models.schedule import is_venue_available
from models.venues import find_venue_by_id
from storage import (
    load_bookings,
    load_festivals,
    load_organizers,
    load_venues,
)


def venues(request):
    items = ""
    for venue in load_venues("data/venues.json"):
        url = reverse("venue_detail", args=[venue.id])
        text = f"{escape(venue.name)} — вместимость {venue.capacity} мест"
        items += f'<li class="list-group-item"><a href="{url}">{text}</a></li>'
    content = f"""
    <h1>Площадки</h1>
    <ul class="list-group">{items}</ul>
    """
    return HttpResponse(page("Площадки", content))


def venue_detail(request, venue_id):
    venues_list = load_venues("data/venues.json")
    venue = find_venue_by_id(venues_list, venue_id)
    venues_url = reverse("venues")

    if venue is None:
        content = f"""
        <h1 class="text-danger">Площадка не найдена</h1>
        <a href="{venues_url}" class="btn btn-outline-secondary">
            ← к списку площадок
        </a>
        """
        return HttpResponse(page("Площадка не найдена", content), status=404)

    organizers_list = load_organizers("data/organizers.json")
    festivals_list = load_festivals("data/festivals.json", organizers_list)
    bookings_list = load_bookings(
        "data/bookings.json",
        festivals_list,
        venues_list,
    )
    available = is_venue_available(bookings_list, venue, date.today())
    status = "свободна" if available else "занята"
    badge = "bg-success" if available else "bg-danger"

    content = f"""
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">{escape(venue.name)}</h5>
            <p class="card-text">
                <strong>ID:</strong> {venue.id}
            </p>
            <p class="card-text">
                <strong>Вместимость:</strong> {venue.capacity} мест
            </p>
            <p class="card-text">
                Доступность на текущую дату:
                <span class="badge {badge}">{status}</span>
            </p>
            <a href="{venues_url}" class="btn btn-outline-secondary">
                ← к списку площадок
            </a>
        </div>
    </div>
    """
    return HttpResponse(page(venue.name, content), status=200)
