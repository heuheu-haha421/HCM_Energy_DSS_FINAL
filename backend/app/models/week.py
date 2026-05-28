from .result import model_failure, model_success
from datetime import date, datetime


class WeekModel:
    @staticmethod
    def _normalize_date(value):
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if hasattr(value, "date"):
            return value.date()

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return value

        return value

    @staticmethod
    def create_table(db):
        db.execute("""
            CREATE TABLE IF NOT EXISTS weeks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week TEXT NOT NULL UNIQUE,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL
            )
        """)

    @staticmethod
    def create_week(db, week, start_date, end_date):
        start_date = WeekModel._normalize_date(start_date)
        end_date   = WeekModel._normalize_date(end_date)

        existing = WeekModel.get_by_week(db, week)
        if existing:
            return model_failure(
                f"Week '{week}' already exists",
                created = False,
                week    = week,
            )

        with db.transaction():
            db.execute(
                "INSERT INTO weeks (week, start_date, end_date) VALUES (?, ?, ?)",
                (week, start_date, end_date)
            )
        return model_success(
            "Week created successfully",
            created = True,
            week    = week,
        )

    @staticmethod
    def get_or_create(db, week, start_date, end_date):
        existing = WeekModel.get_by_week(db, week)

        if existing:
            return existing["id"]

        WeekModel.create_week(
            db,
            week,
            WeekModel._normalize_date(start_date),
            WeekModel._normalize_date(end_date),
        )

        new_week = WeekModel.get_by_week(db, week)
        return new_week["id"]

    # ======================
    # DELETE WEEK (SAFE)
    # ======================
    @staticmethod
    def delete_week(db, week_id, cascade=True):
        week = db.fetch_one(
            "SELECT * FROM weeks WHERE id = ?",
            (week_id,)
        )

        if not week:
            return model_failure(
                f"Week id={week_id} not found",
                deleted = False,
                week_id = week_id,
            )
        
        with db.transaction():

            if cascade:
                db.execute("DELETE FROM energy_weekly WHERE week_id = ?", (week_id,))
                db.execute("DELETE FROM weather_weekly WHERE week_id = ?", (week_id,))

            db.execute(
                "DELETE FROM weeks WHERE id = ?",
                (week_id,)
            )

        return model_success(
            f"Week id={week_id} deleted",
            deleted = True,
            week_id = week_id,
        )

    # ======================
    # QUERY
    # ======================
    @staticmethod
    def get_by_week(db, week):
        return db.fetch_one(
            "SELECT * FROM weeks WHERE week = ?",
            (week,)
        )

    @staticmethod
    def get_all(db):
        return db.fetch_all("SELECT * FROM weeks")

    @staticmethod
    def get_latest(db):
        return db.fetch_one("""
            SELECT *
            FROM weeks
            ORDER BY id DESC
            LIMIT 1
        """)
