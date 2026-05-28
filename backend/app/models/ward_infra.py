from .result import model_success


class WardInfraModel:

    @staticmethod
    def create_table(db):
        db.execute("""
            CREATE TABLE IF NOT EXISTS ward_infra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ward_code TEXT NOT NULL,
                data_year INTEGER NOT NULL,

                population REAL,
                enterprises REAL,
                hospital_beds REAL,
                school_classes REAL,

                UNIQUE(ward_code, data_year),
                FOREIGN KEY (ward_code) REFERENCES wards(ward_code)
            )
        """)

    @staticmethod
    def upsert_many(db, rows):
        params = [
            (
                r["ward_code"],
                r["data_year"],
                r.get("population"),
                r.get("enterprises"),
                r.get("hospital_beds"),
                r.get("school_classes")
            )
            for r in rows
        ]
        
        with db.transaction():

            cursor = db.execute_many("""
                INSERT INTO ward_infra (
                    ward_code, data_year,
                    population, enterprises, hospital_beds, school_classes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ward_code, data_year) DO UPDATE SET
                    population     = excluded.population,
                    enterprises    = excluded.enterprises,
                    hospital_beds  = excluded.hospital_beds,
                    school_classes = excluded.school_classes
            """, params)

        return model_success(
            "Ward infrastructure upserted successfully",
            processed = len(rows),
            rowcount  = cursor.rowcount,
        )
        
    @staticmethod
    def get_all(db):
        return db.fetch_all("""
            SELECT *
            FROM ward_infra
            ORDER BY ward_code, data_year
        """)
        
    @staticmethod
    def get_by_year(db, data_year):
        return db.fetch_all("""
            SELECT
                wi.*,
                w.ward_name
            FROM ward_infra wi
            JOIN  wards w ON wi.ward_code = w.ward_code
            WHERE wi.data_year            = ?
            ORDER BY wi.ward_code
        """, (data_year,))
    
    @staticmethod
    def get_by_ward(db, ward_code):
        return db.fetch_all("""
            SELECT *
            FROM ward_infra
            WHERE ward_code = ?
            ORDER BY data_year DESC
        """, (ward_code,))

    @staticmethod
    def get_data_length(db):
        return db.fetch_one("""
            SELECT COUNT(*) as c
            FROM ward_infra
        """)["c"]
