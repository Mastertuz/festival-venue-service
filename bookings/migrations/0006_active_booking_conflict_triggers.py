from django.db import migrations

# Правило «одна площадка — одно активное бронирование на дату» на уровне базы данных.
# Дата хранится у фестиваля, поэтому обычный UniqueConstraint по таблице бронирований
# построить нельзя; в SQLite правило задаётся триггерами, которые отменяют операцию
# (RAISE(ABORT)). Django превращает такую ошибку в django.db.IntegrityError.
MESSAGE = "Площадка уже забронирована на эту дату: есть активное бронирование."

CONFLICT_FOR_BOOKING = """
    SELECT 1
    FROM bookings_booking AS other
    JOIN festivals_festival AS other_festival ON other_festival.id = other.festival_id
    WHERE other.venue_id = NEW.venue_id
      AND other.status = 'active'
      AND other.id <> NEW.id
      AND other_festival.date = (
          SELECT date FROM festivals_festival WHERE id = NEW.festival_id
      )
"""

CONFLICT_FOR_FESTIVAL_DATE = """
    SELECT 1
    FROM bookings_booking AS own
    JOIN bookings_booking AS other
        ON other.venue_id = own.venue_id
       AND other.id <> own.id
       AND other.status = 'active'
    JOIN festivals_festival AS other_festival ON other_festival.id = other.festival_id
    WHERE own.festival_id = NEW.id
      AND own.status = 'active'
      AND other_festival.date = NEW.date
"""

FORWARD_SQL = [
    f"""
    CREATE TRIGGER booking_active_conflict_insert
    BEFORE INSERT ON bookings_booking
    WHEN NEW.status = 'active' AND EXISTS ({CONFLICT_FOR_BOOKING})
    BEGIN
        SELECT RAISE(ABORT, '{MESSAGE}');
    END;
    """,
    f"""
    CREATE TRIGGER booking_active_conflict_update
    BEFORE UPDATE OF status, venue_id, festival_id ON bookings_booking
    WHEN NEW.status = 'active' AND EXISTS ({CONFLICT_FOR_BOOKING})
    BEGIN
        SELECT RAISE(ABORT, '{MESSAGE}');
    END;
    """,
    f"""
    CREATE TRIGGER festival_date_conflict_update
    BEFORE UPDATE OF date ON festivals_festival
    WHEN NEW.date <> OLD.date AND EXISTS ({CONFLICT_FOR_FESTIVAL_DATE})
    BEGIN
        SELECT RAISE(ABORT, '{MESSAGE}');
    END;
    """,
]

REVERSE_SQL = [
    "DROP TRIGGER IF EXISTS booking_active_conflict_insert;",
    "DROP TRIGGER IF EXISTS booking_active_conflict_update;",
    "DROP TRIGGER IF EXISTS festival_date_conflict_update;",
]


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0005_booking_status_help_text"),
        ("festivals", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
