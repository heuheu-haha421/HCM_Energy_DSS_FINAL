from .result import model_success


class WeatherWeeklyModel:

    @staticmethod
    def create_table(db):
        db.execute("""
        CREATE TABLE IF NOT EXISTS weather_weekly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_id INTEGER NOT NULL,

            temp REAL,
            tmin REAL,
            tmax REAL,
            rhum REAL,
            prcp REAL,
            wspd REAL,
            pres REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(week_id),
            FOREIGN KEY (week_id) REFERENCES weeks(id)
        )
        """)

    # ======================
    # UPSERT ONE (FIXED)
    # ======================
    @staticmethod
    def upsert(db, data: dict):
        week_id = data.get("week_id")
        temp    = data.get("temp")
        tmin    = data.get("tmin")
        tmax    = data.get("tmax")
        rhum    = data.get("rhum")
        prcp    = data.get("prcp")
        wspd    = data.get("wspd")
        pres    = data.get("pres")

        with db.transaction():
            cursor = db.execute("""
                INSERT INTO weather_weekly (
                    week_id, temp, tmin, tmax, rhum, prcp, wspd, pres
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(week_id) DO UPDATE SET
                    temp = excluded.temp,
                    tmin = excluded.tmin,
                    tmax = excluded.tmax,
                    rhum = excluded.rhum,
                    prcp = excluded.prcp,
                    wspd = excluded.wspd,
                    pres = excluded.pres
            """, (week_id, temp, tmin, tmax, rhum, prcp, wspd, pres))

        rowcount = cursor.rowcount

        return model_success(
            "Weather weekly upserted successfully",
            action   = "updated_or_inserted",
            week_id  = week_id,
            rowcount = rowcount,
        )

    # ======================
    # UPSERT MANY (FIXED)
    # ======================
    @staticmethod
    def upsert_many(db, rows):
        params = [
            (
                r["week_id"],
                r.get("temp"),
                r.get("tmin"),
                r.get("tmax"),
                r.get("rhum"),
                r.get("prcp"),
                r.get("wspd"),
                r.get("pres")
            )
            for r in rows
        ]

        with db.transaction():
            cursor = db.execute_many("""
            INSERT INTO weather_weekly (
                week_id, temp, tmin, tmax, rhum, prcp, wspd, pres
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_id) DO UPDATE SET
                temp = excluded.temp,
                tmin = excluded.tmin,
                tmax = excluded.tmax,
                rhum = excluded.rhum,
                prcp = excluded.prcp,
                wspd = excluded.wspd,
                pres = excluded.pres
            """, params)

        return model_success(
            "Weather weekly batch upserted successfully",
            action   = "bulk_upsert",
            rows     = len(rows),
            rowcount = cursor.rowcount,
        )

    # ======================
    # QUERY
    # ======================
    @staticmethod
    def get_all(db):
        return db.fetch_all("""
            SELECT ww.*, w.week, w.start_date, w.end_date
            FROM weather_weekly ww
            JOIN weeks w ON ww.week_id = w.id
            ORDER BY w.start_date
        """)
        
    @staticmethod
    def get_latest(db):
        return db.fetch_one("""
            SELECT *
            FROM weather_weekly ww
            JOIN weeks w ON ww.week_id = w.id
            ORDER BY w.start_date DESC
            LIMIT 1
        """)

    @staticmethod
    def get_by_week_id(db, week_id):
        return db.fetch_one("""
            SELECT ww.*, w.week, w.start_date, w.end_date
            FROM weather_weekly ww
            JOIN weeks w ON ww.week_id = w.id
            WHERE ww.week_id = ?
        """, (week_id,))

    # ======================
    # DELETE (FIXED)
    # ======================
    @staticmethod
    def delete_by_week_id(db, week_id):
        with db.transaction():
            cursor = db.execute(
                "DELETE FROM weather_weekly WHERE week_id = ?",
                (week_id,)
            )

        return model_success(
            "Weather weekly deleted successfully",
            deleted  = True,
            week_id  = week_id,
            rowcount = cursor.rowcount,
        )
