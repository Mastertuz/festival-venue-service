from django.contrib import admin

from .models import Festival, Organizer


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Festival)
class FestivalAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "expected_attendees", "organizer")
    list_filter = ("organizer",)
    search_fields = ("name",)
    list_select_related = ("organizer",)
