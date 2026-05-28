import bcrypt

from app.core import TokenService
from app.errors import ForbiddenError, InvalidInputError, NotFoundError
from app.models import RoleModel, UserModel


class AuthService:
    def __init__(self, db):
        self.db            = db
        self.token_service = TokenService()

    def register(self, data: dict, token: str | None = None):
        username  = data.get("username")
        password  = data.get("password")
        role_name = data.get("role", "user")

        if not username or not password:
            raise InvalidInputError("Missing username or password")

        if len(password) < 6:
            raise InvalidInputError("Password must be at least 6 characters")

        if role_name in {"admin", "dev"}:
            if not token:
                raise InvalidInputError(
                    "Public registration can only create user accounts. Admin or dev account creation requires admin/dev authorization"
                )
            self.require_admin(token)
        elif role_name != "user":
            raise InvalidInputError("Invalid role")

        role = RoleModel.get_by_name(self.db, role_name)

        if not role:
            raise InvalidInputError("Invalid role")

        hashed_password = bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt()
        ).decode()

        result = UserModel.create_user(
            self.db,
            username,
            hashed_password,
            role["id"],
        )

        if not result["success"]:
            raise InvalidInputError(result["message"])

        user = UserModel.get_by_username(self.db, username)

        return {
            "id"      : user["id"],
            "username": user["username"],
            "role"    : role["name"],
        }

    def delete_account(self, user_id: int):
        user = UserModel.get_auth_by_id(self.db, user_id)

        if not user:
            raise NotFoundError("User not found")

        if user["username"] in {"admin", "dev"}:
            raise InvalidInputError("Cannot delete protected account")

        result = UserModel.delete_user(self.db, user_id)

        return {
            "deleted": result["data"]["deleted"],
            "user_id": result["data"]["user_id"],
        }

    def change_password(self, user_id: int, data: dict):
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not old_password or not new_password:
            raise InvalidInputError("Missing old_password or new_password")

        if len(new_password) < 6:
            raise InvalidInputError("Password must be at least 6 characters")

        user = UserModel.get_auth_by_id(self.db, user_id)

        if not user:
            raise NotFoundError("User not found")

        auth_user = UserModel.get_by_username(self.db, user["username"])

        if not bcrypt.checkpw(
            old_password.encode(),
            auth_user["hashed_password"].encode()
        ):
            raise InvalidInputError("Invalid old password")

        hashed_password = bcrypt.hashpw(
            new_password.encode(),
            bcrypt.gensalt()
        ).decode()

        result = UserModel.update_password(self.db, user_id, hashed_password)

        return {
            "user_id": result["data"]["user_id"],
            "updated": result["data"]["updated"],
        }

    def require_admin(self, token: str):
        user = self.token_service.verify_token(token)

        if not user:
            raise InvalidInputError("Invalid or expired token")

        if user.get("role") not in {"admin", "dev"}:
            raise ForbiddenError("Admin or dev role required")

        return user

    def require_dev(self, token: str):
        user = self.token_service.verify_token(token)

        if not user:
            raise InvalidInputError("Invalid or expired token")

        if user.get("role") != "dev":
            raise ForbiddenError("Dev role required")

        return user

    def require_self_or_admin(self, token: str, user_id: int):
        user = self.token_service.verify_token(token)

        if not user:
            raise InvalidInputError("Invalid or expired token")

        if user.get("role") in {"admin", "dev"}:
            return user

        if user.get("user_id") != user_id:
            raise ForbiddenError("You can only change your own password")

        return user

    def start_prediction(self, token: str, predictor):
        self.require_admin(token)
        started = predictor.start()

        return {
            "running": predictor.bRun,
            "started": started,
        }

    def stop_prediction(self, token: str, predictor):
        self.require_admin(token)
        stopped = predictor.stop()

        return {
            "running": predictor.bRun,
            "stopped": stopped,
        }

    def restart_prediction(self, token: str, predictor):
        self.require_admin(token)
        stopped = predictor.stop()
        started = predictor.start()

        return {
            "running"  : predictor.bRun,
            "stopped"  : stopped,
            "started"  : started,
            "restarted": started,
        }

    def login(self, data: dict):
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise InvalidInputError("Missing credentials")

        user = UserModel.get_by_username(self.db, username)

        if not user:
            raise InvalidInputError("Invalid credentials")

        if not bcrypt.checkpw(
            password.encode(),
            user["hashed_password"].encode()
        ):
            raise InvalidInputError("Invalid credentials")

        role = RoleModel.get_by_id(self.db, user["role_id"])

        token = self.token_service.create_token({
            "user_id" : user["id"],
            "username": user["username"],
            "role"    : role["name"]
        })

        return {
            "access_token": token,
            "token_type"  : "bearer",
            "user_id"     : user["id"],
            "role"        : role["name"]
        }

    def me(self, token: str):
        user = self.token_service.decode_token(token)

        return {
            "username": user["username"],
            "role"    : user["role"]
        }
