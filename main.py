"""Начальный сценарий: проверка возможности проведения фестиваля на площадке."""

from datetime import date

festival_name = "Фестиваль уличной музыки"
festival_date = date(2026, 6, 12)
expected_attendees_input = "4500"  # значение получено как строка (например, из формы)

venue_name = "Городской парк"
venue_capacity = 5000
is_venue_available = True

organizer_name = "АНО «Арт-Ивент»"

# преобразование типов: строка -> целое число
expected_attendees = int(expected_attendees_input)

# вычисление свободных мест как результат операции вычитания
free_capacity = venue_capacity - expected_attendees


def check_venue_suitability(capacity, attendees, is_available):
    if not is_available:
        return "Площадка недоступна на выбранную дату"
    elif attendees > capacity:
        return "Площадка не подходит: вместимость превышена"
    else:
        return "Площадка подходит для проведения фестиваля"


status = check_venue_suitability(venue_capacity, expected_attendees, is_venue_available)

print(f"Фестиваль: {festival_name}")
print(f"Дата проведения: {festival_date}")
print(f"Организатор: {organizer_name}")
print(f"Площадка: {venue_name}")
print(f"Вместимость площадки: {venue_capacity} чел.")
print(f"Ожидается посетителей: {expected_attendees} чел.")
print(f"Свободных мест: {free_capacity}")
print(f"Статус: {status}")
