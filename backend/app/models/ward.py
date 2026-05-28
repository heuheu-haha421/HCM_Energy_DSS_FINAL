from .result import model_failure, model_success


class WardModel:

    @staticmethod
    def create_table(db):
        db.execute("""
            CREATE TABLE IF NOT EXISTS wards (
                ward_code TEXT PRIMARY KEY,
                ward_name TEXT NOT NULL
            )
        """)

    # ======================
    # GET ALL WARDS
    # ======================
    @staticmethod
    def get_all(db):
        rows = db.fetch_all("""
            SELECT ward_code, ward_name
            FROM wards
            ORDER BY ward_code
        """)
        return rows

    # ======================
    # INSERT MANY (WITH VALIDATION)
    # ======================
    @staticmethod
    def insert_many(db, rows):
        existing = WardModel.get_all(db)

        db_map = {
            r["ward_code"]: r["ward_name"]
            for r in existing
        }

        params  = []
        invalid = []

        for r in rows:
            code = r["ward_code"].strip()
            name = r["ward_name"].strip()

            if code in db_map:
                if db_map[code] != name:
                    invalid.append({
                        "ward_code" : code,
                        "db_name"   : db_map[code],
                        "input_name": name
                    })
            else:
                params.append((code, name))

        if invalid:
            return model_failure(
                "Ward name does not match existing data",
                created       = 0,
                error         = "WARD_NAME_MISMATCH",
                invalid_wards = invalid,
            )
            
        with db.transaction():
            db.execute_many("""
                INSERT INTO wards (ward_code, ward_name)
                VALUES (?, ?)
            """, params)

        return model_success(
            "Wards inserted successfully",
            inserted=len(params),
        )
