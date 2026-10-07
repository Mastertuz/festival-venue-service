from django.shortcuts import render

from models.schedule import find_booking_by_id
from storage import (
    load_bookings,
    load_festivals,
    load_organizers,
    load_venues,
)


def load_all_bookings():
    """Загрузить бронирования вместе со связанными фестивалями и площадками."""
    venues_list = load_venues("data/venues.json")
    organizers_list = load_organizers("data/organizers.json")
    festivals_list = load_festivals("data/festivals.json", organizers_list)
    return load_bookings("data/bookings.json", festivals_list, venues_list)


def bookings(request):
    bookings_list = load_all_bookings()

    context = {
        "bookings": bookings_list,
    }

    return render(
        request,
        "bookings/booking_list.html",
        context,
    )


def booking_detail(request, booking_id):
    bookings_list = load_all_bookings()

    booking = find_booking_by_id(
        bookings_list,
        booking_id,
    )

    context = {
        "booking": booking,
    }

    return render(
        request,
        "bookings/booking_detail.html",
        context,
        status=404 if booking is None else 200,
    )
