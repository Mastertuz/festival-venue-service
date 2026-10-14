-- ==========================================================================
-- Festival Venue Service: SQL-запросы проекта
--
-- Каждый запрос проверен в SQLite CLI:
--     sqlite3 data/festival_venue.sqlite
--     sqlite> .read sql/queries.sql
--
-- Значения в запросах (3000, '2026-11-07' и т. п.) — примеры для проверки в CLI.
-- В Django-представлениях такие значения передаются отдельными параметрами (?),
-- а не подставляются в текст запроса.
--
-- Схема: organizers(id, name)
--        venues(id, name, capacity)
--        festivals(id, name, date, expected_attendees, organizer_id)
--        bookings(id, festival_id, venue_id, is_cancelled)   -- 0 активно, 1 отменено
-- ==========================================================================


-- ==========================================================================
-- 1. ВЫБОРКА СПИСКОВ ОБЪЕКТОВ (SELECT, ORDER BY)
-- ==========================================================================

-- Запрос 1. Список всех площадок, по названию
-- Страница сайта: /venues/
SELECT
    id,
    name,
    capacity
FROM venues
ORDER BY name;

-- Запрос 2. Список организаторов, по названию
SELECT
    id,
    name
FROM organizers
ORDER BY name;

-- Запрос 3. Список фестивалей, по дате проведения
SELECT
    id,
    name,
    date,
    expected_attendees
FROM festivals
ORDER BY date;


-- ==========================================================================
-- 2. ФИЛЬТРАЦИЯ ДАННЫХ (WHERE)
-- ==========================================================================

-- Запрос 4. Площадки вместимостью не менее 3000 человек
-- Страница сайта: /venues/?min_capacity=3000
SELECT
    id,
    name,
    capacity
FROM venues
WHERE capacity >= 3000
ORDER BY capacity;

-- Запрос 5. Поиск площадок по части названия (LIKE)
SELECT
    id,
    name,
    capacity
FROM venues
WHERE name LIKE '%парк%'
ORDER BY name;

-- Запрос 6. Фестивали в заданный период (BETWEEN)
SELECT
    id,
    name,
    date
FROM festivals
WHERE date BETWEEN '2026-11-01' AND '2026-12-31'
ORDER BY date;

-- Запрос 7. Активные (не отменённые) бронирования
SELECT
    id,
    festival_id,
    venue_id
FROM bookings
WHERE is_cancelled = 0
ORDER BY id;

-- Запрос 8. Площадка по идентификатору
-- Страница сайта: /venues/<id>/
SELECT
    id,
    name,
    capacity
FROM venues
WHERE id = 1;


-- ==========================================================================
-- 3. СОЕДИНЕНИЕ ТАБЛИЦ (JOIN)
-- ==========================================================================

-- Запрос 9. Фестивали с названиями организаторов
SELECT
    festivals.id,
    festivals.name,
    festivals.date,
    organizers.name AS organizer_name
FROM festivals
JOIN organizers
    ON festivals.organizer_id = organizers.id
ORDER BY festivals.date;

-- Запрос 10. Полная информация о бронированиях: фестиваль, площадка, организатор.
-- Вместо идентификаторов запрос возвращает данные, готовые для отображения.
-- Страница сайта: /bookings/
SELECT
    bookings.id,
    festivals.name AS festival_name,
    festivals.date AS booking_date,
    venues.name AS venue_name,
    venues.capacity,
    organizers.name AS organizer_name,
    bookings.is_cancelled
FROM bookings
JOIN festivals
    ON bookings.festival_id = festivals.id
JOIN venues
    ON bookings.venue_id = venues.id
JOIN organizers
    ON festivals.organizer_id = organizers.id
ORDER BY festivals.date, bookings.id;

-- Запрос 11. То же, только активные бронирования
-- Страница сайта: /bookings/?active=1
SELECT
    bookings.id,
    festivals.name AS festival_name,
    festivals.date AS booking_date,
    venues.name AS venue_name,
    venues.capacity,
    organizers.name AS organizer_name,
    bookings.is_cancelled
FROM bookings
JOIN festivals
    ON bookings.festival_id = festivals.id
JOIN venues
    ON bookings.venue_id = venues.id
JOIN organizers
    ON festivals.organizer_id = organizers.id
WHERE bookings.is_cancelled = 0
ORDER BY festivals.date, bookings.id;

-- Запрос 12. Одно бронирование по идентификатору (JOIN + WHERE)
-- Страница сайта: /bookings/<id>/
SELECT
    bookings.id,
    festivals.name AS festival_name,
    festivals.date AS booking_date,
    venues.id AS venue_id,
    venues.name AS venue_name,
    organizers.name AS organizer_name,
    bookings.is_cancelled
FROM bookings
JOIN festivals
    ON bookings.festival_id = festivals.id
JOIN venues
    ON bookings.venue_id = venues.id
JOIN organizers
    ON festivals.organizer_id = organizers.id
WHERE bookings.id = 1;

-- Запрос 13. Ближайшие фестивали с организаторами (JOIN, WHERE, ORDER BY, LIMIT)
-- Страница сайта: / (главная)
SELECT
    festivals.id,
    festivals.name,
    festivals.date,
    organizers.name AS organizer_name
FROM festivals
JOIN organizers
    ON festivals.organizer_id = organizers.id
WHERE festivals.date >= '2026-10-14'
ORDER BY festivals.date
LIMIT 3;

-- Запрос 14. Площадки, свободные на выбранную дату и подходящие по вместимости.
-- Подзапрос NOT IN получает площадки с активным бронированием на эту дату.
-- Страница сайта: /venues/available/
SELECT
    venues.id,
    venues.name,
    venues.capacity
FROM venues
WHERE venues.capacity >= 1500
  AND venues.id NOT IN (
      SELECT bookings.venue_id
      FROM bookings
      JOIN festivals
          ON bookings.festival_id = festivals.id
      WHERE festivals.date = '2026-11-07'
        AND bookings.is_cancelled = 0
  )
ORDER BY venues.name;


-- ==========================================================================
-- 4. АГРЕГАТНЫЕ ФУНКЦИИ (COUNT, MIN, MAX, AVG, SUM)
-- ==========================================================================

-- Запрос 15. Количество активных бронирований
-- Страница сайта: / (главная), /bookings/statistics/
SELECT
    COUNT(*) AS bookings_count
FROM bookings
WHERE is_cancelled = 0;

-- Запрос 16. Сводные показатели площадок
-- Страница сайта: /bookings/statistics/
SELECT
    COUNT(*) AS venues_count,
    MIN(capacity) AS min_capacity,
    MAX(capacity) AS max_capacity,
    ROUND(AVG(capacity), 1) AS avg_capacity,
    SUM(capacity) AS total_capacity
FROM venues;

-- Запрос 17. Занята ли площадка 1 на дату фестиваля (COUNT с условием).
-- Результат 0 — площадка свободна, больше 0 — занята.
-- Страница сайта: /venues/<id>/
SELECT
    COUNT(*) AS busy_count
FROM bookings
JOIN festivals
    ON bookings.festival_id = festivals.id
WHERE bookings.venue_id = 1
  AND festivals.date = '2026-06-12'
  AND bookings.is_cancelled = 0;


-- ==========================================================================
-- 5. ГРУППИРОВКА (GROUP BY) И ФИЛЬТРАЦИЯ ГРУПП (HAVING)
-- ==========================================================================

-- Запрос 18. Количество активных бронирований по площадкам.
-- LEFT JOIN сохраняет площадки без бронирований (для них COUNT равен 0).
-- Страница сайта: /bookings/statistics/
SELECT
    venues.name AS venue_name,
    COUNT(bookings.id) AS bookings_count
FROM venues
LEFT JOIN bookings
    ON venues.id = bookings.venue_id
   AND bookings.is_cancelled = 0
GROUP BY venues.id, venues.name
ORDER BY bookings_count DESC, venues.name;

-- Запрос 19. Фестивали и ожидаемые посетители по организаторам
-- Страница сайта: /bookings/statistics/
SELECT
    organizers.name AS organizer_name,
    COUNT(festivals.id) AS festivals_count,
    SUM(festivals.expected_attendees) AS total_attendees
FROM organizers
JOIN festivals
    ON festivals.organizer_id = organizers.id
GROUP BY organizers.id, organizers.name
ORDER BY total_attendees DESC;

-- Запрос 20. Площадки с более чем 2 активными бронированиями (HAVING).
-- WHERE отбирает отдельные записи до группировки, HAVING — группы после неё.
-- Страница сайта: /bookings/statistics/
SELECT
    venues.name AS venue_name,
    COUNT(bookings.id) AS bookings_count
FROM venues
JOIN bookings
    ON venues.id = bookings.venue_id
WHERE bookings.is_cancelled = 0
GROUP BY venues.id, venues.name
HAVING COUNT(bookings.id) > 2
ORDER BY bookings_count DESC;


-- ==========================================================================
-- 6. ДОПОЛНИТЕЛЬНЫЕ ПРИЁМЫ (LIMIT и OFFSET, DISTINCT, IS NULL)
-- ==========================================================================

-- Запрос 21. Площадки по убыванию вместимости: две записи, начиная со второй
-- (для воспроизводимого порядка LIMIT и OFFSET используются вместе с ORDER BY)
SELECT
    id,
    name,
    capacity
FROM venues
ORDER BY capacity DESC
LIMIT 2 OFFSET 1;

-- Запрос 22. Площадки, у которых есть хотя бы одно активное бронирование
-- (DISTINCT убирает повторы: бронирований больше, чем площадок)
SELECT DISTINCT
    venues.name AS venue_name
FROM bookings
JOIN venues
    ON bookings.venue_id = venues.id
WHERE bookings.is_cancelled = 0
ORDER BY venues.name;

-- Запрос 23. Фестивали без единого активного бронирования (проверка IS NULL).
-- Для текущих данных результат пуст: у каждого фестиваля есть активное бронирование.
-- Пустой результат — не ошибка, а корректный ответ «подходящих записей нет».
SELECT
    festivals.id,
    festivals.name
FROM festivals
LEFT JOIN bookings
    ON bookings.festival_id = festivals.id
   AND bookings.is_cancelled = 0
WHERE bookings.id IS NULL
ORDER BY festivals.date;
