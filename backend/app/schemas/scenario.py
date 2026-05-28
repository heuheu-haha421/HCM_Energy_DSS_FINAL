from pydantic import BaseModel

from .api_response import ApiResponse


class ScenarioItem(BaseModel):
    id        : int
    weight    : str
    created_by: int
    created_at: str | None = None


class ScenarioWeights(BaseModel):
    residential: float
    industrial : float
    commercial : float
    services   : float


class ScenarioCreateData(BaseModel):
    scenario_id: int


class ScenarioUpdateData(BaseModel):
    updated    : bool
    scenario_id: int


class ScenarioDeleteData(BaseModel):
    deleted    : bool
    scenario_id: int


class ScenarioApplyData(BaseModel):
    applied    : bool
    scenario_id: int
    weights    : ScenarioWeights


class ScenarioListResponse(ApiResponse[list[ScenarioItem]]):
    pass


class ScenarioCreateResponse(ApiResponse[ScenarioCreateData]):
    pass


class ScenarioUpdateResponse(ApiResponse[ScenarioUpdateData]):
    pass


class ScenarioDeleteResponse(ApiResponse[ScenarioDeleteData]):
    pass


class ScenarioApplyResponse(ApiResponse[ScenarioApplyData]):
    pass
