import json
from app.errors import InvalidInputError
from .result import model_failure, model_success

class ScenarioModel:

    @staticmethod
    def create_table(db):
        db.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            weight TEXT NOT NULL,

            created_by INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """)

    @staticmethod
    def _validate_weights(weight):
        if isinstance(weight, dict):
            weights = weight
        else:
            weights = json.loads(weight)

        total = (
            weights.get("w_residential", 0) +
            weights.get("w_industrial", 0) +
            weights.get("w_commercial", 0) +
            weights.get("w_services", 0)
        )

        if abs(total - 1.0) > 1e-6:
            raise InvalidInputError(f"Total weights must = 1.0, got {total}")

        return weights

    # ======================
    # CREATE (IMPROVED)
    # ======================
    @staticmethod
    def create(db, weight, created_by):

        ScenarioModel._validate_weights(weight)
        
        with db.transaction():
            cursor = db.execute("""
            INSERT INTO scenarios (
                weight,
                created_by
            )
            VALUES (?, ?)
            """, (
                json.dumps(weight) if isinstance(weight, dict) else weight,
                created_by
            ))

        scenario_id = cursor.lastrowid
        
        return model_success(
            "Scenario created successfully",
            created     = True,
            scenario_id = scenario_id,
        )

    # ======================
    # UPDATE
    # ======================
    @staticmethod
    def update(db, scenario_id, weight):
        ScenarioModel._validate_weights(weight)
        
        existing = db.fetch_one(
            "SELECT id FROM scenarios WHERE id = ?",
            (scenario_id,)
        )

        if not existing:
            return model_failure(
                f"Scenario with ID {scenario_id} not found",
                updated    = False,
                error      = "INVALID_ID",
                invalid_id = scenario_id,
            )

        with db.transaction():
            db.execute("""
                UPDATE scenarios
                SET   weight = ?
                WHERE id     = ?
            """, (json.dumps(weight) if isinstance(weight, dict) else weight, scenario_id))

        return model_success(
            "Scenario updated successfully",
            updated     = True,
            scenario_id = scenario_id,
        )

    # ======================
    # QUERY
    # ======================
    @staticmethod
    def get_by_user(db, user_id):
        return db.fetch_all("""
            SELECT *
            FROM scenarios
            WHERE created_by = ?
            ORDER BY created_at DESC
        """, (user_id,))

    @staticmethod
    def get_by_id(db, scenario_id):
        return db.fetch_one(
            "SELECT * FROM scenarios WHERE id = ?",
            (scenario_id,)
        )
    
    @staticmethod
    def get_all(db):
        return db.fetch_all("""
            SELECT *
            FROM scenarios
            ORDER BY created_at DESC
        """)

    # ======================
    # DELETE
    # ======================
    @staticmethod
    def delete(db, scenario_id):
        existing = db.fetch_one(
            "SELECT id FROM scenarios WHERE id = ?",
            (scenario_id,)
        )

        if not existing:
            return model_failure(
                f"Scenario with ID {scenario_id} not found",
                deleted    = False,
                error      = "INVALID_ID",
                invalid_id = scenario_id,
            )

        with db.transaction():
            db.execute(
                "DELETE FROM scenarios WHERE id = ?",
                (scenario_id,)
            )

        return model_success(
            "Scenario deleted successfully",
            deleted     = True,
            scenario_id = scenario_id,
        )
