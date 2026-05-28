import os
from datetime import datetime
from fastapi import UploadFile

from app.models import ModelRunModel, PredictionModel
from app.errors import InvalidInputError, NotFoundError


class ModelRunService:
    def __init__(self, db, predictor=None):
        self.db        = db
        self.predictor = predictor
        self.model_dir = "model"

    def create_model_run(
        self,
        max_depth       : int,
        min_child_weight: int,
        mae             : float,
        mape            : float,
        rmse            : float,
        r2              : float,
        is_best         : int,
        is_active       : int,
        model_file      : UploadFile
    ):
        self._validate_model_file(model_file)

        file_name, file_path = self._save_model_file(model_file)

        payload = {
            "max_depth"       : max_depth,
            "min_child_weight": min_child_weight,
            "mae"             : mae,
            "mape"            : mape,
            "rmse"            : rmse,
            "r2"              : r2,
            "model_path"      : file_path,
            "is_best"         : is_best,
            "is_active"       : is_active
        }

        model_res = ModelRunModel.create(self.db, payload)

        if self.predictor:
            self.predictor.update_model()

        return {
            "model_id": model_res["data"]["run_id"],
            "file"    : file_name
        }

    def get_all_models(self):
        models = ModelRunModel.get_all(self.db)

        return [dict(model) for model in models]

    def get_active_model(self):
        model = ModelRunModel.get_active(self.db)

        if not model:
            # raise NotFoundError("No active model")
            return None

        return dict(model)

    def get_metrics(self, model_id: int):
        model = self._get_model_or_fail(model_id)

        return {
            "mae" : model["mae"],
            "mape": model["mape"],
            "rmse": model["rmse"],
            "r2"  : model["r2"]
        }

    def get_acceptance_graph(self, model_id: int):
        predictions = PredictionModel.get_by_model(self.db, model_id)

        if not predictions:
            raise NotFoundError("No predictions found or model does not exist")

        graph = []

        for prediction in predictions:
            if prediction["actual_load"] is None:
                continue

            graph.append({
                "week"     : prediction["week"],
                "predicted": prediction["predicted_load"],
                "actual"   : prediction["actual_load"],
                "mae"      : prediction["mae"],
                "mape"     : prediction["mape"]
            })

        return graph

    def set_active_model(self, model_id: int):
        result = ModelRunModel.set_active(self.db, model_id)

        if not result["success"]:
            raise InvalidInputError(result.get("message", "Validation failed"))

        if self.predictor:
            self.predictor.update_model()

        return {
            "active_run_id": result["data"]["active_run_id"]
        }

    def compare_models(self, ids: str):
        model_ids = self._parse_model_ids(ids)

        models = []

        for model_id in model_ids:
            model = self._get_model_or_fail(model_id)

            models.append({
                "id"              : model["id"],
                "max_depth"       : model["max_depth"],
                "min_child_weight": model["min_child_weight"],
                "mae"             : model["mae"],
                "mape"            : model["mape"],
                "rmse"            : model["rmse"],
                "r2"              : model["r2"]
            })

        return models

    def _get_model_or_fail(self, model_id: int):
        model = ModelRunModel.get_by_id(self.db, model_id)

        if not model:
            raise NotFoundError(f"Model with ID {model_id} not found")

        return model

    def _validate_model_file(self, model_file: UploadFile):
        if not model_file.filename:
            raise InvalidInputError("Model file is required")

        if not model_file.filename.endswith(".json"):
            raise InvalidInputError("Model file must be a .json file")

    def _save_model_file(self, model_file: UploadFile):
        os.makedirs(self.model_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{timestamp}_{model_file.filename}"
        file_path = os.path.join(self.model_dir, file_name)

        with open(file_path, "wb") as file:
            file.write(model_file.file.read())

        return file_name, file_path

    def _parse_model_ids(self, ids: str):
        try:
            return [int(item.strip()) for item in ids.split(",") if item.strip()]
        except ValueError:
            raise InvalidInputError("Model ids must be comma-separated integers")
