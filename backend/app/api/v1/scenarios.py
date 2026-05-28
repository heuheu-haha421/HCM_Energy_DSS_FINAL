from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.api.services import AuthService, ScenarioService
from app.schemas.api_response import success_response
from app.schemas.scenario import (
    ScenarioApplyResponse,
    ScenarioCreateResponse,
    ScenarioDeleteResponse,
    ScenarioListResponse,
    ScenarioUpdateResponse,
)


class ScenarioController:
    def __init__(self):
        self.router = APIRouter(
            prefix = "/api/v1/scenarios",
            tags   = ["Scenarios"]
        )

        self.router.add_api_route("/", self.get_all, methods=["GET"], response_model=ScenarioListResponse)
        self.router.add_api_route("/", self.create, methods=["POST"], response_model=ScenarioCreateResponse)
        self.router.add_api_route("/{scenario_id}", self.update, methods=["PUT"], response_model=ScenarioUpdateResponse)
        self.router.add_api_route("/{scenario_id}", self.delete, methods=["DELETE"], response_model=ScenarioDeleteResponse)
        self.router.add_api_route("/{scenario_id}/apply", self.apply, methods=["POST"], response_model=ScenarioApplyResponse)

    def _service(self, request: Request):
        return ScenarioService(
            db        = request.app.state.db,
            predictor = request.app.state.predictor,
        )

    def _auth_service(self, request: Request):
        return AuthService(db=request.app.state.db)

    def get_all(self, request: Request):
        data = self._service(request).get_all()

        return success_response("Scenarios fetched successfully", "SCENARIOS_FETCHED", data)

    def create(
        self,
        data   : dict,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        response_data = self._service(request).create(data)

        return success_response("Scenario created successfully", "SCENARIO_CREATED", response_data)

    def update(
        self,
        scenario_id: int,
        data       : dict,
        request    : Request,
        token      : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        response_data = self._service(request).update(scenario_id, data)

        return success_response("Scenario updated successfully", "SCENARIO_UPDATED", response_data)

    def delete(
        self,
        scenario_id: int,
        request    : Request,
        token      : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_dev(token)
        response_data = self._service(request).delete(scenario_id)

        return success_response("Scenario deleted successfully", "SCENARIO_DELETED", response_data)

    def apply(
        self,
        scenario_id: int,
        request    : Request,
        token      : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        response_data = self._service(request).apply(scenario_id)

        return success_response("Scenario applied successfully", "SCENARIO_APPLIED", response_data)

    def get_current_weights(self, request: Request):
        return getattr(request.app.state, "current_weights", None)
