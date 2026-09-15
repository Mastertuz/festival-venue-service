"""Точка запуска сервиса управления фестивальными площадками."""

from models.festivals import add_festival, find_festival, sort_festivals_by_date
from models.organizers import add_organizer, iter_organizers
from models.schedule import cancel_booking, create_booking
from models.venues import (
    check_venue_capacity,
    filter_venues_by_capacity,
    find_venue,
    sort_venues,
)
from storage import (
    load_bookings,
    load_festivals,
    load_organizers,
    load_venues,
    save_bookings,
    save_festivals,
    save_organizers,
    save_venues,
)
from utils import describe_function, input_date, input_int

VENUES_FILE = "data/venues.json"
ORGANIZERS_FILE = "data/organizers.json"
FESTIVALS_FILE = "data/festivals.json"
BOOKINGS_FILE = "data/bookings.json"


def show_venues(venues: dict[int, dict]) -> None:
    """Вывести список площадок."""
    if not venues:
        print("Список площадок пуст.")
        return
    for venue in venues.values():
        print(f'{venue["id"]}. {venue["name"]} — вместимость {venue["capacity"]} чел.')


def show_organizers(organizers: dict[int, dict]) -> None:
    """Вывести список организаторов."""
    if not organizers:
        print("Список организаторов пуст.")
        return
    for organizer in iter_organizers(organizers):
        print(f'{organizer["id"]}. {organizer["name"]}')


def show_festivals(festivals: dict[int, dict], organizers: dict[int, dict]) -> None:
    """Вывести список фестивалей с указанием организатора."""
    if not festivals:
        print("Список фестивалей пуст.")
        return
    for festival in festivals.values():
        organizer = organizers.get(festival["organizer_id"], {})
        organizer_name = organizer.get("name", "неизвестный организатор")
        print(
            f'{festival["id"]}. {festival["name"]} — {festival["date"]}, '
            f'{festival["expected_attendees"]} посетителей, организатор: {organizer_name}'
        )


def show_bookings(
    bookings: list[dict], festivals: dict[int, dict], venues: dict[int, dict]
) -> None:
    """Вывести расписание с указанием фестиваля и площадки."""
    if not bookings:
        print("Расписание пусто.")
        return
    for booking in bookings:
        festival = festivals.get(booking["festival_id"], {})
        venue = venues.get(booking["venue_id"], {})
        festival_name = festival.get("name", "неизвестный фестиваль")
        venue_name = venue.get("name", "неизвестная площадка")
        print(f'{booking["id"]}. {festival_name} → {venue_name}, {festival.get("date", "?")}')


def print_menu() -> None:
    """Вывести меню приложения."""
    print("\n=== Сервис управления фестивальными площадками ===")
    print("1. Показать площадки")
    print("2. Показать площадки по возрастанию вместимости")
    print("3. Показать площадки с вместимостью не менее N")
    print("4. Найти площадку по названию")
    print("5. Проверить вместимость площадки")
    print("6. Показать организаторов")
    print("7. Добавить организатора")
    print("8. Показать фестивали")
    print("9. Добавить фестиваль")
    print("10. Найти фестиваль по названию")
    print("11. Показать фестивали, отсортированные по дате")
    print("12. Забронировать площадку для фестиваля")
    print("13. Отменить бронирование")
    print("14. Показать расписание")
    print("15. Информация о функции (интроспекция)")
    print("0. Выход")


def main() -> None:
    """Точка запуска приложения: цикл меню и вызов функций проекта."""
    venues = load_venues(VENUES_FILE)
    organizers = load_organizers(ORGANIZERS_FILE)
    festivals = load_festivals(FESTIVALS_FILE)
    bookings = load_bookings(BOOKINGS_FILE)

    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "0":
            save_venues(VENUES_FILE, venues)
            save_organizers(ORGANIZERS_FILE, organizers)
            save_festivals(FESTIVALS_FILE, festivals)
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
            show_organizers(organizers)

        elif choice == "7":
            name = input("Название организатора: ")
            organizer_id = add_organizer(organizers, name)
            print(f"Организатор добавлен, id={organizer_id}")

        elif choice == "8":
            show_festivals(festivals, organizers)

        elif choice == "9":
            name = input("Название фестиваля: ")
            festival_date = input_date("Дата (ДД.ММ.ГГГГ): ")
            attendees = input_int("Ожидаемое число посетителей: ")
            organizer_id = input_int("Идентификатор организатора: ")
            try:
                festival_id = add_festival(
                    festivals, organizers, name, festival_date, attendees, organizer_id,
                )
                print(f"Фестиваль добавлен, id={festival_id}")
            except KeyError as error:
                print(error)

        elif choice == "10":
            query = input("Название или часть названия: ")
            found = find_festival(festivals, query)
            if not found:
                print("Фестивали не найдены.")
            for festival in found:
                print(f'{festival["id"]}. {festival["name"]} — {festival["date"]}')

        elif choice == "11":
            for festival in sort_festivals_by_date(festivals):
                print(f'{festival["date"]} — {festival["name"]}')

        elif choice == "12":
            festival_id = input_int("Идентификатор фестиваля: ")
            venue_id = input_int("Идентификатор площадки: ")
            try:
                booking = create_booking(bookings, festivals, venues, festival_id, venue_id)
                print(f'Бронирование создано, id={booking["id"]}')
            except (KeyError, ValueError) as error:
                print(f"Не удалось создать бронирование: {error}")

        elif choice == "13":
            booking_id = input_int("Идентификатор бронирования: ")
            if cancel_booking(bookings, booking_id):
                print("Бронирование отменено.")
            else:
                print("Бронирование не найдено.")

        elif choice == "14":
            show_bookings(bookings, festivals, venues)

        elif choice == "15":
            print(describe_function(create_booking))

        else:
            print("Неизвестный пункт меню, попробуйте снова.")


if __name__ == "__main__":
    main()
