from django.db import migrations
from django.utils.text import slugify
from unidecode import unidecode


def populate_venue_slugs(apps, schema_editor):
    """Заполнить slug существующих площадок: транслитерация названия и первичный ключ."""
    # Историческая модель соответствует состоянию схемы на момент миграции,
    # поэтому миграция остаётся рабочей и после дальнейших изменений models.py.
    Venue = apps.get_model("venues", "Venue")

    for venue in Venue.objects.order_by("pk"):
        base_slug = slugify(unidecode(venue.name)) or "venue"
        # Первичный ключ гарантирует уникальность даже у площадок с одинаковыми названиями.
        venue.slug = f"{base_slug}-{venue.pk}"
        venue.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("venues", "0004_venue_slug"),
    ]

    operations = [
        migrations.RunPython(populate_venue_slugs, migrations.RunPython.noop),
    ]
