import sqlite3
import bcrypt
from .result import model_failure, model_success


class UserModel:

    @staticmethod
    def create_table(db):
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
        """)

    # ======================
    # CREATE USER
    # ======================
    @staticmethod
    def create_user(db, username, hashed_password, role_id):
        existing_user = db.fetch_one(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )
        if existing_user:
            return model_failure(
                f"Username '{username}' already exists",
                created  = False,
                username = username,
            )

        existing_role = db.fetch_one(
            "SELECT id FROM roles WHERE id = ?",
            (role_id,)
        )
        if not existing_role:
            return model_failure(
                f"Invalid role_id: {role_id}",
                created = False,
                role_id = role_id,
            )

        with db.transaction():
            db.execute(
                "INSERT INTO users (username, hashed_password, role_id) VALUES (?, ?, ?)",
                (username, hashed_password, role_id)
            )

        return model_success(
            "User created successfully",
            created  = True,
            username = username,
            role_id  = role_id,
        )

    # ======================
    # GETTERS
    # ======================
    @staticmethod
    def get_by_username(db, username):
        return db.fetch_one(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )

    @staticmethod
    def get_auth_by_id(db, user_id):
        return db.fetch_one("""
            SELECT
                u.id,
                u.username,
                u.role_id,
                u.is_active,
                r.name AS role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?
        """, (user_id,))

    @staticmethod
    def get_all(db):
        return db.fetch_all("SELECT * FROM users")

    # ======================
    # UPDATE
    # ======================
    @staticmethod
    def update_password(db, user_id, hashed_password):
        with db.transaction():
            db.execute("""
                UPDATE users
                SET hashed_password = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (hashed_password, user_id))

        return model_success(
            "Password updated successfully",
            updated = True,
            user_id = user_id,
        )

    # ======================
    # DELETE
    # ======================
    @staticmethod
    def delete_user(db, user_id):
        with db.transaction():
            db.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )

        return model_success(
            "User deleted successfully",
            deleted = True,
            user_id = user_id,
        )

    # ======================
    # ADMIN SEED (FIXED BCRYPT)
    # ======================
    @staticmethod
    def seed_admin(db, role_id):
        return UserModel._seed_account(
            db               = db,
            username         = "admin",
            password         = "admin123",
            role_id          = role_id,
            existing_message = "Admin already exists",
            created_message  = "Admin created successfully",
        )

    @staticmethod
    def seed_dev(db, role_id):
        return UserModel._seed_account(
            db               = db,
            username         = "dev",
            password         = "dev123",
            role_id          = role_id,
            existing_message = "Dev account already exists",
            created_message  = "Dev account created successfully",
        )

    @staticmethod
    def _seed_account(db, username, password, role_id, existing_message, created_message):
        existing = db.fetch_one(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )

        if existing:
            return model_success(
                existing_message,
                created  = False,
                username = username,
            )

        hashed_password = bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt()
        ).decode()

        db.execute("""
        INSERT INTO users (username, hashed_password, role_id)
        VALUES (?, ?, ?)
        """, (username, hashed_password, role_id))

        return model_success(
            created_message,
            created  = True,
            username = username,
        )
