from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.security import OAuth2PasswordBearer

from app.api.services import AuthService, DataManagementService
from app.errors import InvalidInputError
from app.schemas.api_response import success_response
from app.schemas.data import (
    DataStatusResponse,
    DataUploadResponse,
    GeoJsonResponse,
)


class DataManagementController:
    def __init__(self):
        self.router = APIRouter(
            prefix="/api/v1/data",
            tags=["Data Management"]
        )

        self.router.add_api_route("/upload-energy", self.upload_energy, methods=["POST"], response_model=DataUploadResponse)
        self.router.add_api_route("/upload-ward-stats", self.upload_ward_stats, methods=["POST"], response_model=DataUploadResponse)
        self.router.add_api_route("/upload-holiday", self.upload_holiday, methods=["POST"], response_model=DataUploadResponse)
        self.router.add_api_route("/status", self.get_status, methods=["GET"], response_model=DataStatusResponse)
        
        # Use for demo, not for production
        self.router.add_api_route("/energy-data", self.add_energy, methods=["POST"], response_model=DataUploadResponse)

    def _service(self, request: Request):
        return DataManagementService(db=request.app.state.db)

    def _auth_service(self, request: Request):
        return AuthService(db=request.app.state.db)

    async def upload_energy(
        self,
        request: Request,
        file   : UploadFile = File(...),
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        predictor = request.app.state.predictor

        if predictor.bRun:
            raise InvalidInputError(
                "Prediction process is running. Please stop the prediction process before uploading energy data"
            )

        data = await self._service(request).upload_energy(file)
        
        return success_response("Energy data uploaded successfully", "DATA_ENERGY_UPLOADED", data)

    async def upload_ward_stats(
        self,
        request: Request,
        file   : UploadFile = File(...),
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        data = await self._service(request).upload_ward_stats(file)

        return success_response("Ward stats uploaded successfully", "DATA_WARD_STATS_UPLOADED", data)

    async def upload_holiday(
        self,
        request: Request,
        file   : UploadFile = File(...),
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        data = await self._service(request).upload_holidays(file)

        return success_response("Holiday data uploaded successfully", "DATA_HOLIDAY_UPLOADED", data)

    def get_status(self, request: Request):
        data = self._service(request).get_status()

        return success_response("Data status fetched successfully", "DATA_STATUS_FETCHED", data)

    def add_energy(
        self,
        request: Request,
        payload: dict,
        token  : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        data = self._service(request).add_energy(payload)

        predictor = request.app.state.predictor
        predictor.update_data()

        return success_response("Energy data added successfully", "DATA_ENERGY_ADDED", data)
