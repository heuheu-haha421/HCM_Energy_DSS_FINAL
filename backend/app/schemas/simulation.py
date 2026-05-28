from pydantic import BaseModel

from .api_response import ApiResponse


class PredictionRecord(BaseModel):
    id            : int
    model_run_id  : int
    week_id       : int
    predicted_load: float | None = None
    actual_load   : float | None = None
    mae           : float | None = None
    mape          : float | None = None
    created_at    : str | None = None
    week          : str
    start_date    : str | None = None
    end_date      : str | None = None


class AllocationItem(BaseModel):
    ward_code     : str | None   = None
    ward_name     : str | None   = None
    allocation_pct: float | None = None
    allocated_kwh : float | None = None
    priority_level: str | None   = None
    
class GridStressPriorityItem(BaseModel):
    ward_code         : str | None         = None
    ward_name         : str | None         = None
    allocated_kwh     : float | None       = None
    rank_score        : float | None       = None
    absolute_score    : float | None       = None
    acceleration_score: float | None       = None
    final_score_raw   : float | None       = None
    final_score_ranked: float | None       = None
    priority_level    : str | None         = None
    stress_factors    : dict[str, bool] | None = None
    primary_reason    : str | None         = None


class AllocationResultData(BaseModel):
    total_load: float
    avg_temp  : float
    week      : str | None = None
    start_date: str | None = None
    end_date  : str | None = None
    count     : int
    results   : list[AllocationItem]
    
class GridStressPriorityResultData(BaseModel):
    total_load    : float
    avg_temp      : float
    method        : str | None = None
    week          : str | None = None
    start_date    : str | None = None
    end_date      : str | None = None
    count         : int
    results       : list[GridStressPriorityItem]

class CurrentLoadResponse(ApiResponse[PredictionRecord]):
    pass


class AllocationResponse(ApiResponse[AllocationResultData]):
    pass


class GridStressPrioritiesResponse(ApiResponse[GridStressPriorityResultData]):
    pass
