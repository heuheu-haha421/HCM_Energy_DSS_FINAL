from .result import model_failure, model_success


class EnergyWeeklyModel:

    @staticmethod
    def create_table(db):
        db.execute("""
        CREATE TABLE IF NOT EXISTS energy_weekly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_id INTEGER NOT NULL,
            pmax_mw REAL,
            pmin_mw REAL,
            total_load_kwh REAL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(week_id),
            FOREIGN KEY (week_id) REFERENCES weeks(id)
        )
        """)

    # ======================
    # UPSERT ONE
    # ======================
    @staticmethod
    def upsert(db, week_id, pmax_mw, pmin_mw, total_load_kwh, source):
        with db.transaction():
            cursor = db.execute("""
                INSERT INTO energy_weekly (
                    week_id, pmax_mw, pmin_mw, total_load_kwh, source
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(week_id) DO UPDATE SET
                    pmax_mw        = excluded.pmax_mw,
                    pmin_mw        = excluded.pmin_mw,
                    total_load_kwh = excluded.total_load_kwh,
                    source         = excluded.source
            """, (week_id, pmax_mw, pmin_mw, total_load_kwh, source))
            
        return model_success(
            "Energy weekly upserted successfully",
            week_id=week_id,
            rowcount=cursor.rowcount,
        )

    # ======================
    # UPSERT MANY
    # ======================
    @staticmethod
    def upsert_many(db, rows):
        params = [
            (
                r["week_id"],
                r.get("pmax_mw"),
                r.get("pmin_mw"),
                r.get("total_load_kwh"),
                r["source"]
            )
            for r in rows
        ]

        with db.transaction():
            cursor = db.execute_many("""
                INSERT INTO energy_weekly (
                    week_id, pmax_mw, pmin_mw, total_load_kwh, source
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(week_id) DO UPDATE SET
                    pmax_mw        = excluded.pmax_mw,
                    pmin_mw        = excluded.pmin_mw,
                    total_load_kwh = excluded.total_load_kwh,
                    source         = excluded.source
            """, params)

        return model_success(
            "Energy weekly batch upserted successfully",
            processed=len(rows),
            rowcount=cursor.rowcount,
        )

    # ======================
    # QUERY
    # ======================
    @staticmethod
    def get_all(db):
        return db.fetch_all("""
            SELECT ew.*, w.week, w.start_date, w.end_date
            FROM energy_weekly ew
            JOIN weeks w ON ew.week_id = w.id
            ORDER BY w.start_date
        """)
        
    @staticmethod
    def get_latest(db):
        return db.fetch_one("""
            SELECT ew.*, w.week, w.start_date, w.end_date
            FROM energy_weekly ew
            JOIN weeks w ON ew.week_id = w.id
            ORDER BY w.start_date DESC
            LIMIT 1
        """)
        
    @staticmethod
    def get_last_n(db, n=3):
        return db.fetch_all("""
            SELECT ew.*, w.week, w.start_date, w.end_date
            FROM energy_weekly ew
            JOIN weeks w ON ew.week_id = w.id
            ORDER BY ew.week_id DESC
            LIMIT ?
        """, (n,))

    @staticmethod
    def get_by_week_id(db, week_id):
        return db.fetch_one("""
            SELECT ew.*, w.week, w.start_date, w.end_date
            FROM energy_weekly ew
            JOIN weeks w ON ew.week_id = w.id
            WHERE ew.week_id = ?
        """, (week_id,))
        
    @staticmethod
    def get_data_length(db):
        return db.fetch_one("""
            SELECT COUNT(*) as c
            FROM energy_weekly
        """)["c"]

    # ======================
    # DELETE (FIXED)
    # ======================
    @staticmethod
    def delete_by_week_id(db, week_id):
        with db.transaction():
            result = db.execute(
                "DELETE FROM energy_weekly WHERE week_id = ?",
                (week_id,)
            )

        if result.rowcount == 0:
            return model_failure(
                f"week_id={week_id} not found",
                deleted = False,
                week_id = week_id,
            )

        return model_success(
            "Energy weekly deleted successfully",
            deleted = True,
            week_id = week_id,
        )
