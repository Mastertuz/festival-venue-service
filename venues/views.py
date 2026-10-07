from datetime import date

from django.shortcuts import render

from models.schedule import is_venue_available
from models.venues import find_venue_by_id
from storage import (
    load_bookings,
    load_festivals,
    load_organizers,
    load_venues,
)


def venues(request):
    venues_list = load_venues("data/venues.json")

    context = {
        "venues": venues_list,
    }

    return render(
        request,
        "venues/venue_list.html",
        context,
    )


def venue_detail(request, venue_id):
    venues_list = load_venues("data/venues.json")
    venue = find_venue_by_id(venues_list, venue_id)

    available = None
    if venue is not None:
        organizers_list = load_organizers("data/organizers.json")
        festivals_list = load_festivals("data/festivals.json", organizers_list)
        bookings_list = load_bookings(
            "data/bookings.json",
            festivals_list,
            venues_list,
        )
        available = is_venue_available(bookings_list, venue, date.today())

    context = {
        "venue": venue,
        "available": available,
    }

    return render(
        request,
        "venues/venue_detail.html",
        context,
        status=404 if venue is None else 200,
    )
