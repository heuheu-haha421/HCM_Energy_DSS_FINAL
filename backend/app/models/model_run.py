from .result import model_failure, model_success


class ModelRunModel:

    # ======================
    # SCHEMA
    # ======================
    @staticmethod
    def create_table(db):
        db.execute("""
        CREATE TABLE IF NOT EXISTS model_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            max_depth INTEGER,
            min_child_weight INTEGER,

            mae REAL,
            mape REAL,
            rmse REAL,
            r2 REAL,

            model_path TEXT NOT NULL,

            is_best INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    # ======================
    # CREATE
    # ======================
    @staticmethod
    def create(db, data: dict):
        max_depth        = data.get("max_depth")
        min_child_weight = data.get("min_child_weight")

        mae  = data.get("mae")
        mape = data.get("mape")
        rmse = data.get("rmse")
        r2   = data.get("r2")

        model_path = data.get("model_path")

        is_best   = data.get("is_best", 0)
        is_active = data.get("is_active", 0)

        with db.transaction():

            if is_best == 1:
                db.execute("""
                    UPDATE model_runs
                    SET   is_best = 0
                    WHERE is_best = 1
                """)

            if is_active == 1:
                db.execute("""
                    UPDATE model_runs
                    SET   is_active = 0
                    WHERE is_active = 1
                """)

            cursor = db.execute("""
                INSERT INTO model_runs (
                    max_depth,
                    min_child_weight,
                    mae,
                    mape,
                    rmse,
                    r2,
                    model_path,
                    is_best,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                max_depth,
                min_child_weight,
                mae,
                mape,
                rmse,
                r2,
                model_path,
                is_best,
                is_active
            ))

        return model_success(
            "Model run created successfully",
            created = True,
            run_id  = cursor.lastrowid,
        )

    # ======================
    # SET ACTIVE
    # ======================
    @staticmethod
    def set_active(db, run_id):
        with db.transaction():

            row = db.fetch_one(
                "SELECT id FROM model_runs WHERE id = ?",
                (run_id,)
            )

            if not row:
                return model_failure(
                    f"Model with ID {run_id} not found",
                    set_active = False,
                    error      = "INVALID_ID",
                    invalid_id = run_id,
                )

            db.execute("UPDATE model_runs SET is_active = 0")

            db.execute(
                "UPDATE model_runs SET is_active = 1 WHERE id = ?",
                (run_id,)
            )

            return model_success(
                "Active model run updated successfully",
                active_run_id=run_id,
            )

    # ======================
    # UPDATE BEST MODEL
    # ======================
    @staticmethod
    def update_best(db):
        with db.transaction():

            best = db.fetch_one("""
                SELECT id
                FROM model_runs
                ORDER BY r2 DESC, created_at DESC
                LIMIT 1
            """)

            if not best:
                return model_failure(
                    "No model runs available to set as best",
                    updated=False,
                    error="NO_RUNS",
                )

            db.execute("UPDATE model_runs SET is_best = 0")

            db.execute("""
                UPDATE model_runs
                SET   is_best = 1
                WHERE id      = ?
            """, (best["id"],))

            return model_success(
                "Best model run updated successfully",
                best_run_id=best["id"],
            )

    # ======================
    # QUERY
    # ======================
    @staticmethod
    def get_active(db):
        return db.fetch_one("""
            SELECT *
            FROM model_runs
            WHERE is_active = 1
        """)

    @staticmethod
    def get_best(db):
        return db.fetch_one("""
            SELECT *
            FROM model_runs
            WHERE is_best = 1
        """)

    @staticmethod
    def get_all(db):
        return db.fetch_all("""
            SELECT *
            FROM model_runs
            ORDER BY created_at DESC
        """)

    @staticmethod
    def get_by_id(db, run_id):
        return db.fetch_one(
            "SELECT * FROM model_runs WHERE id = ?",
            (run_id,)
        )
        
    @staticmethod
    def get_data_length(db):
        return db.fetch_one("""
            SELECT COUNT(*) as c
            FROM model_runs
        """)["c"]

    # ======================
    # DELETE
    # ======================
    @staticmethod
    def delete(db, run_id):
        with db.transaction():
            result = db.execute(
                "DELETE FROM model_runs WHERE id = ?",
                (run_id,)
            )

            if result.rowcount == 0:
                return model_failure(
                    f"Model with ID {run_id} not found",
                    deleted    = False,
                    error      = "INVALID_ID",
                    invalid_id = run_id,
                )

            return model_success(
                "Model run deleted successfully",
                deleted = True,
                run_id  = run_id,
            )
