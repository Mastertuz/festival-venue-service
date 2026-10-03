from django.http import HttpResponse


def index(request):
    return HttpResponse("Festival Venue Service - сервис управления фестивальными площадками")
