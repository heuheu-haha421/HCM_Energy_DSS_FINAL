from .result import model_success


class HolidayModel:

    @staticmethod
    def create_table(db):
        db.execute("""
            CREATE TABLE IF NOT EXISTS holidays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start DATE NOT NULL,
                end DATE NOT NULL,
                type TEXT NOT NULL,
                UNIQUE(start, end, type)
            )
        """)

    @staticmethod
    def upsert_many(db, rows):
        params = [
            (
                r["start"],
                r["end"],
                r["type"],
            )
            for r in rows
        ]

        with db.transaction():
            cursor = db.execute_many("""
                INSERT INTO holidays (start, end, type)
                VALUES (?, ?, ?)
                ON CONFLICT(start, end, type) DO UPDATE SET
                    start = excluded.start,
                    end   = excluded.end,
                    type  = excluded.type
            """, params)

        return model_success(
            "Holidays upserted successfully",
            processed=len(rows),
            rowcount=cursor.rowcount,
        )

    @staticmethod
    def get_all(db):
        return db.fetch_all("""
            SELECT start, "end", type
            FROM holidays
            ORDER BY start
        """)
