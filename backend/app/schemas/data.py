from typing import Any

from pydantic import BaseModel

from .api_response import ApiResponse


class BatchUpsertData(BaseModel):
    rows    : int | None = None
    rowcount: int | None = None


class DataStatusData(BaseModel):
    energy_rows: int
    ward_rows  : int
    model_rows : int
    status     : str


class DataUploadResponse(ApiResponse[BatchUpsertData]):
    pass


class DataStatusResponse(ApiResponse[DataStatusData]):
    pass


class GeoJsonResponse(ApiResponse[dict[str, Any]]):
    pass
