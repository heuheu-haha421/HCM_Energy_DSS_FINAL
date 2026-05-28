from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer

from app.api.services import AuthService, ModelRunService
from app.schemas.api_response import success_response
from app.schemas.model_run import (
    ModelRunAcceptanceGraphResponse,
    ModelRunCompareResponse,
    ModelRunCreateResponse,
    ModelRunDetailResponse,
    ModelRunListResponse,
    ModelRunMetricsResponse,
    ModelRunSetActiveResponse,
)


class AIMonitorController:
    def __init__(self):
        self.router = APIRouter(
            prefix = "/api/v1/models",
            tags   = ["AI Monitor"]
        )

        self.router.add_api_route("/", self.add_model_run, methods=["POST"], response_model=ModelRunCreateResponse)
        self.router.add_api_route("/", self.get_all_models, methods=["GET"], response_model=ModelRunListResponse)
        self.router.add_api_route("/active", self.get_active_model, methods=["GET"], response_model=ModelRunDetailResponse)
        self.router.add_api_route("/{model_id}/metrics", self.get_metrics, methods=["GET"], response_model=ModelRunMetricsResponse)
        self.router.add_api_route("/{model_id}/acceptance-graph", self.get_acceptance_graph, methods=["GET"], response_model=ModelRunAcceptanceGraphResponse)
        self.router.add_api_route("/{model_id}/set-active", self.set_active, methods=["POST"], response_model=ModelRunSetActiveResponse)
        self.router.add_api_route("/compare", self.compare_models, methods=["GET"], response_model=ModelRunCompareResponse)

    def _service(self, request: Request):
        db        = request.app.state.db
        predictor = request.app.state.predictor
        return ModelRunService(db=db, predictor=predictor)

    def _auth_service(self, request: Request):
        return AuthService(db=request.app.state.db)

    def add_model_run(
        self,
        request         : Request,
        max_depth       : int = Form(...),
        min_child_weight: int = Form(...),
        mae             : float = Form(...),
        mape            : float = Form(...),
        rmse            : float = Form(...),
        r2              : float = Form(...),
        is_best         : int = Form(0),
        is_active       : int = Form(0),
        model_file      : UploadFile = File(...),
        token           : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        service = self._service(request)

        data = service.create_model_run(
            max_depth        = max_depth,
            min_child_weight = min_child_weight,
            mae              = mae,
            mape             = mape,
            rmse             = rmse,
            r2               = r2,
            is_best          = is_best,
            is_active        = is_active,
            model_file       = model_file
        )

        return success_response("Model run created successfully", "MODEL_RUN_CREATED", data)

    def get_all_models(self, request: Request):
        data = self._service(request).get_all_models()
        
        return success_response("Model runs fetched successfully", "MODEL_RUNS_FETCHED", data)

    def get_active_model(self, request: Request):
        data = self._service(request).get_active_model()

        return success_response("Active model fetched successfully", "ACTIVE_MODEL_FETCHED", data)

    def get_metrics(self, model_id: int, request: Request):
        data = self._service(request).get_metrics(model_id)

        return success_response("Model metrics fetched successfully", "MODEL_METRICS_FETCHED", data)

    def get_acceptance_graph(self, model_id: int, request: Request):
        data = self._service(request).get_acceptance_graph(model_id)

        return success_response("Acceptance graph fetched successfully", "MODEL_ACCEPTANCE_GRAPH_FETCHED", data)

    def set_active(
        self,
        model_id: int,
        request : Request,
        token   : str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    ):
        self._auth_service(request).require_admin(token)
        data = self._service(request).set_active_model(model_id)

        return success_response("Active model updated successfully", "ACTIVE_MODEL_UPDATED", data)

    def compare_models(self, ids: str, request: Request):
        data = self._service(request).compare_models(ids)

        return success_response("Models compared successfully", "MODEL_COMPARISON_FETCHED", data)

