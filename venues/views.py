from django.http import HttpResponse


def venues(request):
    return HttpResponse("Список площадок")


def venue_detail(request, venue_id):
    return HttpResponse(f"Площадка {venue_id}")
