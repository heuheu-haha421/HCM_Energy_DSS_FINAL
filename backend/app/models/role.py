import sqlite3
from .result import model_failure, model_success

class RoleModel:
    # ========
    # Schema
    # ========
    @staticmethod
    def create_table(db):
        db.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
    @staticmethod
    def seed(db):
        roles = ["admin", "user", "dev"]

        existing_roles = db.fetch_all("SELECT name FROM roles")
        existing_set   = {r["name"] for r in existing_roles}

        to_insert = [r for r in roles if r not in existing_set]

        if not to_insert:
            return model_success(
                "All roles already exist",
                created  = False,
                existing = list(existing_set),
            )

        params = [(r,) for r in to_insert]

        db.execute_many("""
            INSERT INTO roles (name)
            VALUES (?)
        """, params)
        
        return model_success(
            "Roles seeded successfully",
            created  = True,
            inserted = to_insert,
            existing = list(existing_set),
        )
            
    # ========
    # CRUD Operations
    # ========
    @staticmethod
    def create_role(db, name):
        existing = db.fetch_one(
            "SELECT id FROM roles WHERE name = ?",
            (name,)
        )
        if existing:
            result = model_failure(
                f"Role '{name}' already exists",
                created = False,
                name    = name,
            )
            return result

        db.execute(
            "INSERT INTO roles (name) VALUES (?)",
            (name,)
        )
        
        return model_success(
            "Role created successfully",
            created = True,
            name    = name,
        )
        
    @staticmethod
    def get_by_id(db, role_id):
        return db.fetch_one(
            "SELECT * FROM roles WHERE id = ?", 
            (role_id,)
        )

    @staticmethod
    def get_by_name(db, name):
        return db.fetch_one(
            "SELECT * FROM roles WHERE name = ?",
            (name,)
        )
    
    @staticmethod
    def get_all(db):
        return db.fetch_all("SELECT * FROM roles")
    
    @staticmethod
    def delete_role(db, role_id):
        db.execute(
            "DELETE FROM roles WHERE id = ?", 
            (role_id,)
        )
        return model_success(
            "Role deleted successfully",
            deleted = True,
            role_id = role_id,
        )
