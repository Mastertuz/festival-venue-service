-- ==========================================
-- Festival Venue Service: структура базы данных
-- Сущности: организаторы, площадки, фестивали, бронирования
-- ==========================================

-- Организатор проводит фестивали
CREATE TABLE IF NOT EXISTS organizers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- Площадка, доступная для проведения фестиваля
CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0)
);

-- Фестиваль: дата хранится строкой YYYY-MM-DD (допускает сравнение и сортировку в SQL)
CREATE TABLE IF NOT EXISTS festivals (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    expected_attendees INTEGER NOT NULL CHECK (expected_attendees > 0),
    organizer_id INTEGER NOT NULL,
    FOREIGN KEY (organizer_id) REFERENCES organizers(id)
);

-- Бронирование площадки под фестиваль; дата бронирования = дата фестиваля.
-- is_cancelled: 0 - бронирование активно, 1 - отменено
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY,
    festival_id INTEGER NOT NULL,
    venue_id INTEGER NOT NULL,
    is_cancelled INTEGER NOT NULL DEFAULT 0 CHECK (is_cancelled IN (0, 1)),
    FOREIGN KEY (festival_id) REFERENCES festivals(id),
    FOREIGN KEY (venue_id) REFERENCES venues(id)
);

-- Индексы ускоряют поиск по внешним ключам и по дате
CREATE INDEX IF NOT EXISTS idx_festivals_date ON festivals(date);
CREATE INDEX IF NOT EXISTS idx_bookings_venue_id ON bookings(venue_id);
CREATE INDEX IF NOT EXISTS idx_bookings_festival_id ON bookings(festival_id);
