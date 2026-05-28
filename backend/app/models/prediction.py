from .result import model_success


class PredictionModel:

    # ======================
    # SCHEMA
    # ======================
    @staticmethod
    def create_table(db):
        db.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                model_run_id INTEGER NOT NULL,
                week_id INTEGER NOT NULL,

                predicted_load REAL,
                actual_load REAL,

                mae REAL,
                mape REAL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(model_run_id, week_id),

                FOREIGN KEY (model_run_id) REFERENCES model_runs(id),
                FOREIGN KEY (week_id) REFERENCES weeks(id)
            )
        """)
        
    @staticmethod
    def to_float(value):
        return float(value) if value is not None else None

    # ======================
    # UPSERT ONE
    # ======================
    @staticmethod
    def upsert(db, data: dict):
        model_run_id   = data.get("model_run_id", 0)
        week_id        = data.get("week_id", 0)
        predicted_load = data.get("predicted_load", 0)
        actual_load    = data.get("actual_load", None)
        mae            = data.get("mae", None)
        mape           = data.get("mape", None)

        with db.transaction():
            cursor = db.execute("""
                INSERT INTO predictions (
                    model_run_id, week_id, predicted_load, actual_load, mae, mape
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_run_id, week_id) DO UPDATE SET
                    predicted_load = excluded.predicted_load,
                    actual_load    = excluded.actual_load,
                    mae            = excluded.mae,
                    mape           = excluded.mape,
                    created_at     = CURRENT_TIMESTAMP
            """, (
                model_run_id,
                week_id,
                PredictionModel.to_float(predicted_load),
                PredictionModel.to_float(actual_load),
                PredictionModel.to_float(mae),
                PredictionModel.to_float(mape)
            ))

            return model_success(
                "Prediction upserted successfully",
                model_run_id = model_run_id,
                week_id      = week_id,
                rowcount     = cursor.rowcount,
            )

    # ======================
    # UPSERT MANY
    # ======================
    @staticmethod
    def upsert_many(db, rows):
        params = [
            (
                r["model_run_id"],
                r["week_id"],
                PredictionModel.to_float(r["predicted_load"]),
                PredictionModel.to_float(r["actual_load"]) if r["actual_load"] is not None else None,
                PredictionModel.to_float(r["mae"]) if r["mae"] is not None else None,
                PredictionModel.to_float(r["mape"]) if r["mape"] is not None else None
            )
            for r in rows
        ]

        with db.transaction():
            cursor = db.execute_many("""
                INSERT INTO predictions (
                    model_run_id, week_id, predicted_load, actual_load, mae, mape
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_run_id, week_id) DO UPDATE SET
                    predicted_load = excluded.predicted_load,
                    actual_load    = excluded.actual_load,
                    mae            = excluded.mae,
                    mape           = excluded.mape,
                    created_at     = CURRENT_TIMESTAMP
            """, params)

        return model_success(
            "Predictions upserted successfully",
            processed = len(rows),
            rowcount  = cursor.rowcount,
        )

    # ======================
    # DELETE
    # ======================
    @staticmethod
    def delete_all(db):
        with db.transaction():
            cursor = db.execute("DELETE FROM predictions")
            db.execute("DELETE FROM sqlite_sequence WHERE name = 'predictions'")

        return model_success(
            "Predictions deleted successfully",
            rowcount=cursor.rowcount,
        )

    # ======================
    # QUERY
    # ======================
    @staticmethod
    def get_by_model(db, model_run_id):
        return db.fetch_all("""
            SELECT p.*, w.week, w.start_date, w.end_date
            FROM predictions p
            JOIN weeks w ON p.week_id = w.id
            WHERE p.model_run_id = ?
            ORDER BY p.week_id DESC
            LIMIT 15
        """, (model_run_id,))

    @staticmethod
    def get_all(db):
        return db.fetch_all("""
            SELECT p.*, w.week, w.start_date, w.end_date
            FROM predictions p
            JOIN weeks w ON p.week_id = w.id
            ORDER BY p.week_id DESC
        """)
    
    @staticmethod
    def get_latest_record(db):
        return db.fetch_one("""
            SELECT p.*, w.week, w.start_date, w.end_date
            FROM predictions p
            JOIN weeks w ON p.week_id = w.id
            ORDER BY p.week_id DESC, p.id DESC
            LIMIT 1
        """)

    @staticmethod
    def get_latest_by_week(db, week_id):
        return db.fetch_one("""
            SELECT *
            FROM predictions
            WHERE week_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (week_id,))
