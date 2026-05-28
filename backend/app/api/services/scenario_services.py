import json

from app.errors import InvalidInputError, NotFoundError
from app.models import ScenarioModel


class ScenarioService:
    def __init__(self, db, predictor=None):
        self.db        = db
        self.predictor = predictor

    def get_all(self):
        scenarios = ScenarioModel.get_all(self.db)

        return [dict(scenario) for scenario in scenarios]

    def create(self, data: dict):
        required = {"weight", "created_by"}

        if not required.issubset(data):
            raise InvalidInputError(f"Columns required: {required}")

        scenario_res = ScenarioModel.create(
            self.db,
            data["weight"],
            data["created_by"]
        )

        return {
            "scenario_id": scenario_res["data"]["scenario_id"]
        }

    def update(self, scenario_id: int, data: dict):
        result = ScenarioModel.update(
            self.db,
            scenario_id,
            data["weight"]
        )

        if not result["success"]:
            raise InvalidInputError(result.get("message", "Update failed"))

        return {
            "updated"    : True,
            "scenario_id": scenario_id
        }

    def delete(self, scenario_id: int):
        result = ScenarioModel.delete(self.db, scenario_id)

        if not result["success"]:
            raise InvalidInputError(result.get("message", "Delete failed"))

        return {
            "deleted"    : True,
            "scenario_id": scenario_id
        }

    def apply(self, scenario_id: int):
        scenario = ScenarioModel.get_by_id(self.db, scenario_id)

        if not scenario:
            raise NotFoundError(f"Scenario with ID {scenario_id} not found")

        weights_raw = json.loads(scenario["weight"])

        weights = {
            "residential": weights_raw["w_residential"],
            "industrial" : weights_raw["w_industrial"],
            "commercial" : weights_raw["w_commercial"],
            "services"   : weights_raw["w_services"]
        }

        if self.predictor:
            self.predictor.update_weight(weights)

        return {
            "applied"    : True,
            "scenario_id": scenario_id,
            "weights"    : weights
        }
