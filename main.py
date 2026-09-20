"""Точка запуска сервиса управления фестивальными площадками."""

from schedule import (
    cancel_booking,
    check_venue_suitability,
    create_booking,
    is_venue_available,
)
from storage import load_bookings, load_venues, save_bookings, save_venues
from utils import describe_function, input_date, input_int
from venues import (
    check_venue_capacity,
    filter_venues_by_capacity,
    find_venue,
    get_venue,
    sort_venues,
)

VENUES_FILE = "data/venues.json"
BOOKINGS_FILE = "data/bookings.json"


def show_venues(venues: dict[int, dict]) -> None:
    """Вывести список площадок."""
    if not venues:
        print("Список площадок пуст.")
        return
    for venue in venues.values():
        print(f'{venue["id"]}. {venue["name"]} — вместимость {venue["capacity"]} чел.')


def show_bookings(bookings: list[dict], venues: dict[int, dict]) -> None:
    """Вывести расписание бронирований с указанием площадки и даты."""
    if not bookings:
        print("Расписание пусто.")
        return
    for booking in bookings:
        venue_name = venues.get(booking["venue_id"], {}).get("name", "неизвестная площадка")
        print(
            f'{booking["id"]}. {booking["festival_name"]} '
            f'({booking["organizer_name"]}) — {venue_name}, '
            f'{booking["booking_date"]}, {booking["expected_attendees"]} посетителей'
        )


def print_menu() -> None:
    """Вывести меню приложения."""
    print("\n=== Сервис управления фестивальными площадками ===")
    print("1. Показать площадки")
    print("2. Показать площадки по возрастанию вместимости")
    print("3. Показать площадки с вместимостью не менее N")
    print("4. Найти площадку по названию")
    print("5. Проверить вместимость площадки")
    print("6. Проверить доступность площадки на дату")
    print("7. Забронировать площадку для фестиваля")
    print("8. Отменить бронирование")
    print("9. Показать расписание")
    print("10. Информация о функции (интроспекция)")
    print("0. Выход")


def main() -> None:
    """Точка запуска приложения: цикл меню и вызов функций проекта."""
    venues = load_venues(VENUES_FILE)
    bookings = load_bookings(BOOKINGS_FILE)

    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "0":
            save_venues(VENUES_FILE, venues)
            save_bookings(BOOKINGS_FILE, bookings)
            print("Данные сохранены. До встречи!")
            break

        elif choice == "1":
            show_venues(venues)

        elif choice == "2":
            for venue in sort_venues(venues):
                print(f'{venue["name"]} — {venue["capacity"]} чел.')

        elif choice == "3":
            min_capacity = input_int("Минимальная вместимость: ")
            for venue in filter_venues_by_capacity(venues, min_capacity):
                print(f'{venue["name"]} — {venue["capacity"]} чел.')

        elif choice == "4":
            query = input("Название или часть названия: ")
            found = find_venue(venues, query)
            if not found:
                print("Площадки не найдены.")
            for venue in found:
                print(f'{venue["id"]}. {venue["name"]} — {venue["capacity"]} чел.')

        elif choice == "5":
            venue_id = input_int("Идентификатор площадки: ")
            attendees = input_int("Ожидаемое число посетителей: ")
            try:
                suitable = check_venue_capacity(venues, venue_id, attendees)
                print("Подходит по вместимости" if suitable else "Вместимость превышена")
            except KeyError as error:
                print(error)

        elif choice == "6":
            venue_id = input_int("Идентификатор площадки: ")
            booking_date = input_date("Дата (ДД.ММ.ГГГГ): ")
            try:
                venue = get_venue(venues, venue_id)
                available = is_venue_available(bookings, venue_id, booking_date)
                print(check_venue_suitability(venue["capacity"], 0, available))
            except KeyError as error:
                print(error)

        elif choice == "7":
            venue_id = input_int("Идентификатор площадки: ")
            festival_name = input("Название фестиваля: ")
            organizer_name = input("Организатор: ")
            attendees = input_int("Ожидаемое число посетителей: ")
            booking_date = input_date("Дата (ДД.ММ.ГГГГ): ")
            try:
                booking = create_booking(
                    bookings, venues, venue_id, festival_name,
                    organizer_name, attendees, booking_date,
                )
                print(f'Бронирование создано, id={booking["id"]}')
            except (KeyError, ValueError) as error:
                print(f"Не удалось создать бронирование: {error}")

        elif choice == "8":
            booking_id = input_int("Идентификатор бронирования: ")
            if cancel_booking(bookings, booking_id):
                print("Бронирование отменено.")
            else:
                print("Бронирование не найдено.")

        elif choice == "9":
            show_bookings(bookings, venues)

        elif choice == "10":
            print(describe_function(create_booking))

        else:
            print("Неизвестный пункт меню, попробуйте снова.")


if __name__ == "__main__":
    main()
