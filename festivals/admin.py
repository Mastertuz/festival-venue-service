from django.contrib import admin
from django.db.models import Count

from bookings.models import Booking

from .models import Festival, Organizer


class OrganizerFestivalInline(admin.TabularInline):
    """Фестивали организатора в его карточке."""

    model = Festival
    fields = ("name", "date", "expected_attendees")
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "фестиваль"
    verbose_name_plural = "Фестивали организатора"

    def has_add_permission(self, request, obj=None):
        return False


class FestivalBookingInline(admin.TabularInline):
    """Бронирования фестиваля в его карточке: статус можно изменить, площадку — нет."""

    model = Booking
    fields = ("venue", "status")
    readonly_fields = ("venue",)
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "бронирование"
    verbose_name_plural = "Бронирования фестиваля"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "festivals_count")
    list_display_links = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 20
    readonly_fields = ("id",)
    inlines = (OrganizerFestivalInline,)

    def get_queryset(self, request):
        # Число фестивалей считается агрегатом в запросе списка, а не по одному на строку.
        return super().get_queryset(request).annotate(festivals_total=Count("festivals"))

    @admin.display(description="Фестивалей", ordering="festivals_total")
    def festivals_count(self, obj):
        return obj.festivals_total


@admin.register(Festival)
class FestivalAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "date", "expected_attendees", "organizer")
    list_display_links = ("name",)
    search_fields = ("name", "organizer__name")
    list_filter = ("date", "organizer")
    date_hierarchy = "date"
    ordering = ("date", "pk")
    list_per_page = 20
    readonly_fields = ("id",)
    autocomplete_fields = ("organizer",)
    list_select_related = ("organizer",)
    inlines = (FestivalBookingInline,)
