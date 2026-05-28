from .v1.auth import AuthController
from .v1.models_api import AIMonitorController
from .v1.scenarios import ScenarioController
from .v1.data_mgmt import DataManagementController
from .v1.demo_toggle import DemoToggleController
from .v1.dev_delete import DevDeleteController
from .v1.simulation import SimulationController
from .v1.websocket import LivePredictController, ConnectionManager
from .v1.geojson import GeoJsonController
from .v1.prediction_runner import PredictionRunnerController


def register_routers(app):
    manager = ConnectionManager()

    app.include_router(LivePredictController(manager).router)
    app.include_router(AuthController().router)
    app.include_router(SimulationController().router)
    app.include_router(ScenarioController().router)
    app.include_router(AIMonitorController().router)
    app.include_router(DataManagementController().router)
    app.include_router(DemoToggleController().router)
    app.include_router(GeoJsonController().router)
    app.include_router(PredictionRunnerController().router)
    app.include_router(DevDeleteController().router)
    
    return manager
