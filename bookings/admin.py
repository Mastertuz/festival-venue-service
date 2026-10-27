from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "festival", "venue", "is_cancelled")
    list_filter = ("is_cancelled", "venue")
    list_select_related = ("festival", "venue")
