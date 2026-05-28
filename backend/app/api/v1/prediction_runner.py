from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.api.services import AuthService
from app.schemas.api_response import success_response
from app.schemas.auth import (
    AuthRestartPredictionResponse,
    AuthStartPredictionResponse,
    AuthStopPredictionResponse,
)


class PredictionRunnerController:
    def __init__(self):
        self.router = APIRouter(
            prefix = "/api/v1/prediction",
            tags   = ["Prediction Runner"]
        )

        self.router.add_api_route("/start", self.start_prediction, methods=["POST"], response_model=AuthStartPredictionResponse)
        self.router.add_api_route("/stop", self.stop_prediction, methods=["POST"], response_model=AuthStopPredictionResponse)
        self.router.add_api_route("/restart", self.restart_prediction, methods=["POST"], response_model=AuthRestartPredictionResponse)

    def _service(self, request: Request):
        return AuthService(db=request.app.state.db)

    def start_prediction(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        response_data = self._service(request).start_prediction(
            token,
            request.app.state.predictor,
        )
        started = response_data["started"]

        return success_response(
            "Prediction process started" if started else "Prediction process is already running",
            "PREDICTION_STARTED" if started else "PREDICTION_ALREADY_RUNNING",
            response_data,
        )

    def stop_prediction(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        response_data = self._service(request).stop_prediction(
            token,
            request.app.state.predictor,
        )
        stopped = response_data["stopped"]

        return success_response(
            "Prediction process stopped" if stopped else "Prediction process is not running",
            "PREDICTION_STOPPED" if stopped else "PREDICTION_NOT_RUNNING",
            response_data,
        )

    def restart_prediction(
        self,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        response_data = self._service(request).restart_prediction(
            token,
            request.app.state.predictor,
        )
        restarted = response_data["restarted"]

        return success_response(
            "Prediction process restarted" if restarted else "Prediction process could not be restarted",
            "PREDICTION_RESTARTED" if restarted else "PREDICTION_RESTART_FAILED",
            response_data,
        )
