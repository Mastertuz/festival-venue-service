from django.urls import path

from . import views

app_name = "venues"

urlpatterns = [
    path("", views.venues, name="list"),
    path("available/", views.available, name="available"),
    path("create/", views.venue_create, name="create"),
    # Старый адрес с числовым идентификатором перенаправляется на страницу со slug.
    path("<int:venue_id>/", views.venue_redirect, name="detail_by_id"),
    path("<slug:slug>/edit/", views.venue_update, name="update"),
    path("<slug:slug>/", views.venue_detail, name="detail"),
]
