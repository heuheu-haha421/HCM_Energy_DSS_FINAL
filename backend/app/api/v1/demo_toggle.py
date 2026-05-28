from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.api.services import AuthService
from app.errors import InvalidInputError


class DemoTogglePayload(BaseModel):
    is_demo         : bool
    interval_seconds: int


class DemoToggleController:
    def __init__(self):
        self.router = APIRouter(
            prefix = "/api/v1/demo",
            tags   = ["Demo"]
        )

        self.router.add_api_route("/toggle", self.toggle, methods=["POST"])

    def _auth_service(self, request: Request):
        return AuthService(db=request.app.state.db)

    def toggle(
        self,
        payload: DemoTogglePayload,
        request: Request,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)

        if payload.interval_seconds <= 0:
            raise InvalidInputError("interval_seconds must be greater than 0")

        predictor = request.app.state.predictor
        settings  = predictor.update_demo_settings(
            payload.is_demo,
            payload.interval_seconds,
        )

        mode = "demo" if payload.is_demo else "normal"

        return {
            "status"       : "ok",
            "mode"         : mode,
            "interval"     : settings["sleep_seconds"],
            "is_demo_mode" : settings["is_demo_mode"],
            "sleep_seconds": settings["sleep_seconds"],
        }
