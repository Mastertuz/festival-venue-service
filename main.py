"""Точка запуска сервиса управления фестивальными площадками."""

from models import Booking, Festival, Organizer, Venue
from models.festivals import (
    add_festival,
    find_festival,
    get_festival,
    show_festivals,
    sort_festivals_by_date,
)
from models.organizers import add_organizer, show_organizers
from models.schedule import (
    cancel_booking,
    check_venue_suitability,
    create_booking,
    is_venue_available,
    show_bookings,
)
from models.venues import (
    check_venue_capacity,
    filter_venues_by_capacity,
    find_venue,
    get_venue,
    show_venues,
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


def create_new_booking(
    bookings: list[Booking], festivals: list[Festival], venues: list[Venue]
) -> None:
    """Пользовательский сценарий бронирования.

    Находит объекты Festival и Venue по идентификаторам, проверяет
    возможность бронирования и создаёт Booking функцией create_booking().
    """
    festival_id = input_int("Идентификатор фестиваля: ")
    venue_id = input_int("Идентификатор площадки: ")

    try:
        festival = get_festival(festivals, festival_id)
        venue = get_venue(venues, venue_id)
    except KeyError as error:
        print(error.args[0])
        return

    if not is_venue_available(bookings, venue, festival.date):
        print("Не удалось создать бронирование: площадка уже занята на эту дату.")
        return

    booking = create_booking(bookings, festival, venue)
    if booking is None:
        print("Не удалось создать бронирование: вместимость площадки превышена.")
    else:
        print(f"Бронирование создано, id={booking.id}")


def print_menu() -> None:
    """Вывести меню приложения."""
    print("\n=== Сервис управления фестивальными площадками ===")
    print("1. Показать площадки")
    print("2. Показать площадки по возрастанию вместимости")
    print("3. Показать площадки с вместимостью не менее N")
    print("4. Найти площадку по названию")
    print("5. Проверить вместимость площадки")
    print("6. Проверить доступность площадки на дату фестиваля")
    print("7. Показать организаторов")
    print("8. Добавить организатора")
    print("9. Показать фестивали")
    print("10. Добавить фестиваль")
    print("11. Найти фестиваль по названию")
    print("12. Показать фестивали, отсортированные по дате")
    print("13. Забронировать площадку для фестиваля")
    print("14. Отменить бронирование")
    print("15. Показать расписание")
    print("16. Информация о функции (интроспекция)")
    print("0. Выход")


def main() -> None:
    """Точка запуска приложения: цикл меню и вызов функций проекта."""
    venues: list[Venue] = load_venues(VENUES_FILE)
    organizers: list[Organizer] = load_organizers(ORGANIZERS_FILE)
    festivals: list[Festival] = load_festivals(FESTIVALS_FILE, organizers)
    bookings: list[Booking] = load_bookings(BOOKINGS_FILE, festivals, venues)

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
                print(venue)

        elif choice == "3":
            min_capacity = input_int("Минимальная вместимость: ")
            for venue in filter_venues_by_capacity(venues, min_capacity):
                print(venue)

        elif choice == "4":
            query = input("Название или часть названия: ")
            found_venues = find_venue(venues, query)
            if not found_venues:
                print("Площадки не найдены.")
            for venue in found_venues:
                print(f"{venue.id}. {venue}")

        elif choice == "5":
            venue_id = input_int("Идентификатор площадки: ")
            attendees = input_int("Ожидаемое число посетителей: ")
            try:
                suitable = check_venue_capacity(venues, venue_id, attendees)
                print("Подходит по вместимости" if suitable else "Вместимость превышена")
            except KeyError as error:
                print(error.args[0])

        elif choice == "6":
            festival_id = input_int("Идентификатор фестиваля: ")
            venue_id = input_int("Идентификатор площадки: ")
            try:
                festival = get_festival(festivals, festival_id)
                venue = get_venue(venues, venue_id)
            except KeyError as error:
                print(error.args[0])
            else:
                print(check_venue_suitability(venue, festival, bookings))

        elif choice == "7":
            show_organizers(organizers)

        elif choice == "8":
            name = input("Название организатора: ")
            organizer = add_organizer(organizers, name)
            print(f"Организатор добавлен, id={organizer.id}")

        elif choice == "9":
            show_festivals(festivals)

        elif choice == "10":
            name = input("Название фестиваля: ")
            festival_date = input_date("Дата (ДД.ММ.ГГГГ): ")
            attendees = input_int("Ожидаемое число посетителей: ")
            organizer_id = input_int("Идентификатор организатора: ")
            try:
                festival = add_festival(
                    festivals, organizers, name, festival_date, attendees, organizer_id,
                )
                print(f"Фестиваль добавлен, id={festival.id}")
            except KeyError as error:
                print(error.args[0])

        elif choice == "11":
            query = input("Название или часть названия: ")
            found_festivals = find_festival(festivals, query)
            if not found_festivals:
                print("Фестивали не найдены.")
            for festival in found_festivals:
                print(f"{festival.id}. {festival}")

        elif choice == "12":
            for festival in sort_festivals_by_date(festivals):
                print(festival)

        elif choice == "13":
            create_new_booking(bookings, festivals, venues)

        elif choice == "14":
            booking_id = input_int("Идентификатор бронирования: ")
            if cancel_booking(bookings, booking_id):
                print("Бронирование отменено.")
            else:
                print("Бронирование не найдено.")

        elif choice == "15":
            show_bookings(bookings)

        elif choice == "16":
            print(describe_function(create_booking))

        else:
            print("Неизвестный пункт меню, попробуйте снова.")


if __name__ == "__main__":
    main()
