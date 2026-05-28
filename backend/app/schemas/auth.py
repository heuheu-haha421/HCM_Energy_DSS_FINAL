from pydantic import BaseModel

from .api_response import ApiResponse


class AuthLoginData(BaseModel):
    access_token: str
    token_type  : str
    user_id     : int
    role        : str


class AuthMeData(BaseModel):
    username: str
    role    : str


class AuthRegisterData(BaseModel):
    id      : int
    username: str
    role    : str


class AuthDeleteData(BaseModel):
    deleted: bool
    user_id: int


class AuthChangePasswordData(BaseModel):
    user_id: int
    updated: bool


class AuthStartPredictionData(BaseModel):
    running: bool
    started: bool


class AuthStopPredictionData(BaseModel):
    running: bool
    stopped: bool


class AuthRestartPredictionData(BaseModel):
    running  : bool
    stopped  : bool
    started  : bool
    restarted: bool


class AuthLoginResponse(ApiResponse[AuthLoginData]):
    pass


class AuthMeResponse(ApiResponse[AuthMeData]):
    pass


class AuthRegisterResponse(ApiResponse[AuthRegisterData]):
    pass


class AuthDeleteResponse(ApiResponse[AuthDeleteData]):
    pass


class AuthChangePasswordResponse(ApiResponse[AuthChangePasswordData]):
    pass


class AuthStartPredictionResponse(ApiResponse[AuthStartPredictionData]):
    pass


class AuthStopPredictionResponse(ApiResponse[AuthStopPredictionData]):
    pass


class AuthRestartPredictionResponse(ApiResponse[AuthRestartPredictionData]):
    pass
