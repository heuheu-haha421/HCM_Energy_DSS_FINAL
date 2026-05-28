from pydantic import BaseModel

from .api_response import ApiResponse


class ModelRunItem(BaseModel):
    id              : int
    max_depth       : int | None = None
    min_child_weight: float | None = None
    mae             : float | None = None
    mape            : float | None = None
    rmse            : float | None = None
    r2              : float | None = None
    model_path      : str
    is_best         : int
    is_active       : int
    created_at      : str | None = None


class ModelRunCreateData(BaseModel):
    model_id: int
    file    : str


class ModelRunMetricsData(BaseModel):
    mae : float | None = None
    mape: float | None = None
    rmse: float | None = None
    r2  : float | None = None


class ModelAcceptancePoint(BaseModel):
    week     : str
    predicted: float | None = None
    actual   : float | None = None
    mae      : float | None = None
    mape     : float | None = None


class ModelRunSetActiveData(BaseModel):
    active_run_id: int


class ModelRunCompareItem(BaseModel):
    id              : int
    max_depth       : int | None = None
    min_child_weight: float | None = None
    mae             : float | None = None
    mape            : float | None = None
    rmse            : float | None = None
    r2              : float | None = None


class ModelRunCreateResponse(ApiResponse[ModelRunCreateData]):
    pass


class ModelRunListResponse(ApiResponse[list[ModelRunItem]]):
    pass


class ModelRunDetailResponse(ApiResponse[ModelRunItem]):
    pass


class ModelRunMetricsResponse(ApiResponse[ModelRunMetricsData]):
    pass


class ModelRunAcceptanceGraphResponse(ApiResponse[list[ModelAcceptancePoint]]):
    pass


class ModelRunSetActiveResponse(ApiResponse[ModelRunSetActiveData]):
    pass


class ModelRunCompareResponse(ApiResponse[list[ModelRunCompareItem]]):
    pass
