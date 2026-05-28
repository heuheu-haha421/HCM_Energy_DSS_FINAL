from fastapi import APIRouter, Depends, Request, Query
from fastapi.security import OAuth2PasswordBearer

from app.api.services import AuthService, SimulationService
from app.schemas.api_response import success_response
from app.schemas.simulation import (
    AllocationResponse,
    CurrentLoadResponse,
    GridStressPrioritiesResponse,
)


class SimulationController:
    def __init__(self):
        self.router = APIRouter(
            prefix = "/api/v1/simulation",
            tags   = ["Simulation"]
        )

        self.router.add_api_route(
            "/current-load", 
            self.get_current_load, 
            methods        = ["GET"],
            response_model = CurrentLoadResponse
        )
        self.router.add_api_route(
            "/allocate", 
            self.allocate, 
            methods        = ["POST"],
            response_model = AllocationResponse
        )
        self.router.add_api_route(
            "/grid-stress-priorities",
            self.grid_stress_priorities,
            methods        = ["GET"],
            response_model = GridStressPrioritiesResponse,
        )

    def _service(self, request: Request):
        return SimulationService(
            db        = request.app.state.db,
            predictor = request.app.state.predictor,
        )

    def _auth_service(self, request: Request):
        return AuthService(db=request.app.state.db)

    def get_current_load(self, request: Request):
        data = self._service(request).get_current_load()

        return success_response("Current load fetched successfully", "SIMULATION_CURRENT_LOAD_FETCHED", data)

    def allocate(
        self,
        payload: dict,
        request: Request,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        data = self._service(request).allocate(payload)

        return success_response("Allocation calculated successfully", "SIMULATION_ALLOCATION_FETCHED", data)

    def grid_stress_priorities(self, request: Request, year: int = Query(...), limit: int = Query(10)):
        payload = {
            "year" : year,
            "limit": limit,
        }
        data = self._service(request).grid_stress_priorities(payload)

        return success_response(
            "Grid stress priorities calculated successfully",
            "GRID_STRESS_PRIORITIES_CALCULATED",
            data,
        )
