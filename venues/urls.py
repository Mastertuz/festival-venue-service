from django.urls import path

from . import views

app_name = "venues"

urlpatterns = [
    path("", views.venues, name="list"),
    path("<int:venue_id>/", views.venue_detail, name="detail"),
]
