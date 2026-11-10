from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.bookings, name="list"),
    path("statistics/", views.statistics, name="statistics"),
    # Статические адреса стоят до маршрутов с <int:...>, чтобы не пересекаться с ними.
    path("create/", views.booking_create, name="create"),
    path("<int:booking_id>/", views.booking_detail, name="detail"),
]
