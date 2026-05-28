from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from app.api.services import AuthService
from app.config import EnvManager


class DevDeleteController:
    ENABLE_DEV_DELETE_ENV = "ENABLE_DEV_DELETE"

    def __init__(self):
        self.router = APIRouter(
            prefix = "/api/v1/dev/delete",
            tags   = ["Dev Delete"]
        )

        self.router.add_api_route("/users", self.delete_users, methods=["DELETE"])
        self.router.add_api_route("/weeks", self.delete_weeks, methods=["DELETE"])
        self.router.add_api_route("/energy-weekly", self.delete_energy_weekly, methods=["DELETE"])
        self.router.add_api_route("/weather-weekly", self.delete_weather_weekly, methods=["DELETE"])
        self.router.add_api_route("/holidays", self.delete_holidays, methods=["DELETE"])
        self.router.add_api_route("/wards", self.delete_wards, methods=["DELETE"])
        self.router.add_api_route("/ward-infra", self.delete_ward_infra, methods=["DELETE"])
        self.router.add_api_route("/model-runs", self.delete_model_runs, methods=["DELETE"])
        self.router.add_api_route("/predictions", self.delete_predictions, methods=["DELETE"])
        self.router.add_api_route("/scenarios", self.delete_scenarios, methods=["DELETE"])

    def _ensure_enabled(self):
        env = EnvManager()
        env.load({self.ENABLE_DEV_DELETE_ENV})

        if not env.get_bool(self.ENABLE_DEV_DELETE_ENV, False):
            raise HTTPException(
                status_code=403,
                detail="Dev delete APIs are disabled. Set ENABLE_DEV_DELETE=true to enable them.",
            )

    def _auth_service(self, request: Request):
        return AuthService(db=request.app.state.db)

    def _delete_table(self, request: Request, table_name: str, token: str):
        self._ensure_enabled()
        self._auth_service(request).require_dev(token)

        db = request.app.state.db
        db.connect()

        try:
            db.conn.execute("PRAGMA foreign_keys = OFF")
            cursor = db.conn.execute(f'DELETE FROM "{table_name}"')
            db.conn.execute(
                "DELETE FROM sqlite_sequence WHERE name = ?",
                (table_name,),
            )
            db.conn.commit()
            db.conn.execute("PRAGMA foreign_keys = ON")

            return {
                "success"     : True,
                "table"       : table_name,
                "deleted_rows": cursor.rowcount,
                "id_reset"    : True,
            }
        except Exception as exc:
            db.conn.rollback()
            db.conn.execute("PRAGMA foreign_keys = ON")
            raise HTTPException(status_code=500, detail=str(exc))

    def _delete_users_except_protected_accounts(self, request: Request, token: str):
        self._ensure_enabled()
        self._auth_service(request).require_dev(token)

        db = request.app.state.db
        db.connect()

        try:
            db.conn.execute("PRAGMA foreign_keys = OFF")
            cursor = db.conn.execute(
                "DELETE FROM users WHERE username NOT IN (?, ?)",
                ("admin", "dev"),
            )
            db.conn.execute(
                "UPDATE sqlite_sequence SET seq = COALESCE((SELECT MAX(id) FROM users), 0) WHERE name = ?",
                ("users",),
            )
            db.conn.commit()
            db.conn.execute("PRAGMA foreign_keys = ON")

            return {
                "success"     : True,
                "table"       : "users",
                "deleted_rows": cursor.rowcount,
                "protected"   : ["admin", "dev"],
                "id_reset"    : True,
            }
        except Exception as exc:
            db.conn.rollback()
            db.conn.execute("PRAGMA foreign_keys = ON")
            raise HTTPException(status_code=500, detail=str(exc))

    def delete_users(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_users_except_protected_accounts(request, token)

    def delete_weeks(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "weeks", token)

    def delete_energy_weekly(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "energy_weekly", token)

    def delete_weather_weekly(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "weather_weekly", token)

    def delete_holidays(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "holidays", token)

    def delete_wards(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "wards", token)

    def delete_ward_infra(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "ward_infra", token)

    def delete_model_runs(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "model_runs", token)

    def delete_predictions(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "predictions", token)

    def delete_scenarios(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        return self._delete_table(request, "scenarios", token)
