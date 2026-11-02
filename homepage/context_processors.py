"""Контекстные процессоры: общие данные для всех шаблонов проекта."""

from venues.models import Venue

SITE_NAME = "Festival Venue Service"


def site_context(request):
    """Передать в шаблоны название сервиса и актуальное число площадок.

    request — текущий запрос; Django передаёт его процессору автоматически.
    Число площадок считается запросом count() к базе данных при каждом формировании контекста.
    """
    return {
        "site_name": SITE_NAME,
        "venues_count": Venue.objects.count(),
    }
