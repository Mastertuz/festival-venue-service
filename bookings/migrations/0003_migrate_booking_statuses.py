from django.db import migrations


def migrate_booking_statuses(apps, schema_editor):
    """Перенести признак отмены is_cancelled в поле status."""
    # Историческая модель соответствует состоянию схемы на момент миграции.
    Booking = apps.get_model("bookings", "Booking")

    # Отменённые бронирования получают статус «cancelled».
    Booking.objects.filter(is_cancelled=True).update(status="cancelled")

    # Все остальные существующие бронирования считаются активными.
    # Статус «completed» по прошедшей дате автоматически не назначается:
    # для этого нужно отдельное правило предметной области.
    Booking.objects.filter(is_cancelled=False).update(status="active")


def reverse_booking_statuses(apps, schema_editor):
    """Откат: восстановить is_cancelled по статусу."""
    Booking = apps.get_model("bookings", "Booking")

    Booking.objects.filter(status="cancelled").update(is_cancelled=True)
    Booking.objects.exclude(status="cancelled").update(is_cancelled=False)


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0002_booking_status"),
    ]

    operations = [
        migrations.RunPython(migrate_booking_statuses, reverse_booking_statuses),
    ]
