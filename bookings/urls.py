from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.BookingListView.as_view(), name="list"),
    path("statistics/", views.statistics, name="statistics"),
    # Статические адреса стоят до маршрутов с <int:...>, чтобы не пересекаться с ними.
    path("create/", views.BookingCreateView.as_view(), name="create"),
    path("<int:booking_id>/", views.BookingDetailView.as_view(), name="detail"),
    path("<int:booking_id>/edit/", views.BookingUpdateView.as_view(), name="update"),
    path("<int:booking_id>/cancel/", views.booking_cancel, name="cancel"),
]
