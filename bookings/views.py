from django.http import HttpResponse


def bookings(request):
    return HttpResponse("Список бронирований")


def booking_detail(request, booking_id):
    return HttpResponse(f"Бронирование {booking_id}")
