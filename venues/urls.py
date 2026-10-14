from django.urls import path

from . import views

app_name = "venues"

urlpatterns = [
    path("", views.venues, name="list"),
    path("available/", views.available, name="available"),
    path("<int:venue_id>/", views.venue_detail, name="detail"),
]
