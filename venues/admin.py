from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from bookings.models import Booking

from .models import Venue


class VenueBookingInline(admin.TabularInline):
    """Бронирования площадки в её карточке: статус можно изменить, состав — нет."""

    model = Booking
    fields = ("festival", "status")
    readonly_fields = ("festival",)
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "бронирование"
    verbose_name_plural = "Бронирования площадки"

    def has_add_permission(self, request, obj=None):
        # Новые бронирования создаются в разделе «Бронирования», где работает автопоиск
        # фестиваля и проверка занятости площадки.
        return False


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "capacity",
        "is_large",
        "active_bookings_count",
        "site_link",
    )
    # Название ведёт на страницу изменения; вместимость правится прямо в списке.
    list_display_links = ("name",)
    list_editable = ("capacity",)
    search_fields = ("name",)
    list_filter = ("is_large",)
    ordering = ("name",)
    list_per_page = 20

    # id и slug присваиваются автоматически, is_large вычисляет база данных.
    readonly_fields = ("id", "slug", "is_large")
    inlines = (VenueBookingInline,)

    # Ссылка «Смотреть на сайте» строится по Venue.get_absolute_url().
    view_on_site = True

    def get_queryset(self, request):
        # Число активных бронирований считается в самом запросе списка (annotate + Count
        # с условием), поэтому не требует отдельного запроса на каждую строку.
        return (
            super()
            .get_queryset(request)
            .annotate(
                active_bookings=Count("bookings", filter=Q(bookings__status=Booking.Status.ACTIVE))
            )
        )

    @admin.display(description="Активных бронирований", ordering="active_bookings")
    def active_bookings_count(self, obj):
        return obj.active_bookings

    @admin.display(description="Страница на сайте")
    def site_link(self, obj):
        return format_html('<a href="{}" target="_blank">Открыть</a>', obj.get_absolute_url())
