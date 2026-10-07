from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape

from homepage.views import page
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


def badge_class(booking):
    return "bg-secondary" if booking.is_cancelled else "bg-success"


def bookings(request):
    items = ""
    for booking in load_all_bookings():
        url = reverse("bookings:detail", args=[booking.id])
        title = (
            f"{escape(booking.festival.name)} → {escape(booking.venue.name)}, "
            f"{booking.booking_date.isoformat()}"
        )
        items += f"""
        <li class="list-group-item d-flex justify-content-between">
            <a href="{url}">{title}</a>
            <span class="badge {badge_class(booking)}">{booking.status}</span>
        </li>
        """
    content = f"""
    <h1>Бронирования</h1>
    <ul class="list-group">
        {items}
    </ul>
    """
    return HttpResponse(page("Бронирования", content))


def booking_detail(request, booking_id):
    booking = find_booking_by_id(load_all_bookings(), booking_id)
    bookings_url = reverse("bookings:list")

    if booking is None:
        content = f"""
        <h1 class="text-danger">Бронирование не найдено</h1>
        <a href="{bookings_url}" class="btn btn-outline-secondary">
            ← к списку бронирований
        </a>
        """
        return HttpResponse(page("Бронирование не найдено", content), status=404)

    venue_url = reverse("venues:detail", args=[booking.venue.id])
    content = f"""
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">Бронирование №{booking.id}</h5>
            <p class="card-text">
                Фестиваль: {escape(booking.festival.name)}
            </p>
            <p class="card-text">
                Организатор: {escape(booking.festival.organizer.name)}
            </p>
            <p class="card-text">
                Площадка: <a href="{venue_url}">{escape(booking.venue.name)}</a>
            </p>
            <p class="card-text">
                Дата: {booking.booking_date.isoformat()}
            </p>
            <p class="card-text">
                Статус:
                <span class="badge {badge_class(booking)}">{booking.status}</span>
            </p>
            <a href="{bookings_url}" class="btn btn-outline-secondary">
                ← к списку бронирований
            </a>
        </div>
    </div>
    """
    return HttpResponse(page(f"Бронирование №{booking.id}", content), status=200)
