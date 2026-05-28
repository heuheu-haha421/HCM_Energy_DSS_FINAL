from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.api.services import AuthService
from app.schemas.api_response import success_response
from app.schemas.auth import (
    AuthChangePasswordResponse,
    AuthDeleteResponse,
    AuthLoginResponse,
    AuthMeResponse,
    AuthRegisterResponse,
)

optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


class AuthController:
    def __init__(self):
        self.router        = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
        self.oauth2_scheme = OAuth2PasswordBearer(
            tokenUrl="/api/v1/auth"
        )

        self.router.add_api_route("/login", self.login, methods=["POST"], response_model=AuthLoginResponse)
        self.router.add_api_route("/register", self.register, methods=["POST"], response_model=AuthRegisterResponse)
        self.router.add_api_route("/{user_id}/change-password", self.change_password, methods=["PUT"], response_model=AuthChangePasswordResponse)
        self.router.add_api_route("/{user_id}/delete-account", self.delete_account, methods=["DELETE"], response_model=AuthDeleteResponse)
        self.router.add_api_route("/me", self.me, methods=["GET"], response_model=AuthMeResponse)

    def _service(self, request: Request):
        return AuthService(db=request.app.state.db)

    def login(self, request: Request, data: dict):
        response_data = self._service(request).login(data)

        return success_response("Login successful", "AUTH_LOGIN_SUCCESS", response_data)

    def register(
        self,
        request: Request,
        data: dict,
        token: str | None = Depends(optional_oauth2_scheme),
    ):
        response_data = self._service(request).register(data, token)

        return success_response("Account created successfully", "AUTH_REGISTER_SUCCESS", response_data)

    def change_password(
        self,
        user_id: int,
        request : Request,
        data    : dict,
        token   : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        service = self._service(request)
        service.require_self_or_admin(token, user_id)
        response_data = service.change_password(user_id, data)

        return success_response("Password changed successfully", "AUTH_PASSWORD_CHANGED", response_data)

    def delete_account(
        self,
        user_id: int,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        service = self._service(request)
        service.require_admin(token)
        response_data = service.delete_account(user_id)

        return success_response("Account deleted successfully", "AUTH_ACCOUNT_DELETED", response_data)

    def me(
        self,
        request: Request,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        response_data = self._service(request).me(token)

        return success_response("Current user fetched successfully", "AUTH_ME_FETCHED", response_data)
