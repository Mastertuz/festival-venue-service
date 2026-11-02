from django.contrib import admin, messages

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # Столбцы списка: связанные объекты показываются через их __str__(),
    # вместимость и дата берутся методами-столбцами из связанных моделей.
    list_display = (
        "id",
        "festival",
        "venue",
        "venue_capacity",
        "festival_date",
        "status",
    )
    list_display_links = ("id",)

    # Поиск по связанным моделям: «__» переходит по внешнему ключу к полю другой модели.
    search_fields = (
        "festival__name",
        "venue__name",
        "festival__organizer__name",
    )
    list_filter = ("status", "festival__date", "venue")
    date_hierarchy = "festival__date"
    ordering = ("festival__date", "pk")
    list_per_page = 20

    # id показывается, но в форме не редактируется.
    readonly_fields = ("id",)

    # Поиск связанного объекта прямо в поле формы
    # (в FestivalAdmin и VenueAdmin настроен search_fields).
    autocomplete_fields = ("festival", "venue")

    # Один запрос с JOIN вместо отдельного запроса на фестиваль и площадку каждой строки списка.
    list_select_related = ("festival", "venue")

    actions = ("cancel_bookings", "complete_bookings", "restore_bookings")

    @admin.display(description="Вместимость площадки", ordering="venue__capacity")
    def venue_capacity(self, obj):
        return obj.venue.capacity

    @admin.display(description="Дата фестиваля", ordering="festival__date")
    def festival_date(self, obj):
        return obj.festival.date

    @admin.action(description="Отменить выбранные бронирования")
    def cancel_bookings(self, request, queryset):
        # Метод модели cancel() сохраняет только поле status, поэтому записи обходятся по одной.
        count = 0
        for booking in queryset:
            booking.cancel()
            count += 1
        self.message_user(request, f"Отменено бронирований: {count}.", messages.SUCCESS)

    @admin.action(description="Отметить выбранные бронирования завершёнными")
    def complete_bookings(self, request, queryset):
        count = 0
        for booking in queryset:
            booking.complete()
            count += 1
        self.message_user(request, f"Завершено бронирований: {count}.", messages.SUCCESS)

    @admin.action(description="Вернуть выбранные бронирования в активные")
    def restore_bookings(self, request, queryset):
        # Настройка админ-панели не заменяет бизнес-правило: перед возвратом в активные
        # проверяется, что площадка на эту дату не занята другим активным бронированием.
        restored = 0
        skipped = 0
        for booking in queryset.select_related("festival"):
            busy = (
                Booking.objects.active()
                .for_date(booking.festival.date)
                .filter(venue_id=booking.venue_id)
                .exclude(pk=booking.pk)
                .exists()
            )
            if busy:
                skipped += 1
                continue
            Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.ACTIVE)
            restored += 1
        self.message_user(request, f"Возвращено в активные: {restored}.", messages.SUCCESS)
        if skipped:
            self.message_user(
                request,
                f"Пропущено (площадка занята активным бронированием): {skipped}.",
                messages.WARNING,
            )
