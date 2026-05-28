import pandas as pd

from app.models import EnergyWeeklyModel, PredictionModel, WeatherWeeklyModel, WeekModel
from app.utilities import DebugMixin

class EnergyRepository:
    ENERGY_COLUMNS = [
        "week",
        "week_id",
        "start_date",
        "end_date",
        "pmax_mw",
        "pmin_mw",
        "total_load_kwh",
    ]

    RENAME_COLUMNS = {
        "pmax_mw"       : "Pmax (MW)",
        "pmin_mw"       : "Pmin (MW)",
        "total_load_kwh": "total_load (kWh)",
    }

    def __init__(self, db):
        self.db = db

    def get_all(self):
        res = EnergyWeeklyModel.get_all(self.db)
        if not res:
            return None, None, False

        df         = pd.DataFrame([dict(row) for row in res])
        total_load = self._normalize_energy_df(df)
        week_ids   = df["week_id"].tolist()

        return total_load, week_ids, True

    def get_last_n(self, n=3):
        res = EnergyWeeklyModel.get_last_n(self.db, n)
        if not res:
            return None, None, False

        df = pd.DataFrame([dict(row) for row in res])

        total_load = self._normalize_energy_df(df)

        total_load = total_load.sort_values("week_id", ascending=True).reset_index(drop=True)

        current_week_id = int(total_load.iloc[-1]["week_id"])

        return total_load, current_week_id, True

    def _normalize_energy_df(self, df: pd.DataFrame):
        return df[self.ENERGY_COLUMNS].rename(columns=self.RENAME_COLUMNS)


class PredictionRepository(DebugMixin):
    def __init__(self, db):
        self.db = db

    def get_all(self):
        res = PredictionModel.get_all(self.db)

        if not res:
            return None

        return pd.DataFrame([dict(row) for row in res])

    def delete_all(self):
        return PredictionModel.delete_all(self.db)

    def upsert_prediction(self, data: dict):
        return PredictionModel.upsert(self.db, data)

    def upsert_weather(self, data: dict):
        res = WeatherWeeklyModel.upsert(self.db, data)
        self.printDebug(f"Weather weekly upsert result: {res['data']}")

    def upsert_many_weather(self, data: list):
        res = WeatherWeeklyModel.upsert_many(self.db, data)
        self.printDebug(f"Weather weekly upsert many result: {res['data']}")

    def ingest_week(self, week, start_date, end_date):
        return WeekModel.get_or_create(self.db, week, start_date, end_date)


class PredictionStore:
    def __init__(self, db_repo: PredictionRepository, get_model_info, get_date_range):
        self.db_repo        = db_repo
        self.get_model_info = get_model_info
        self.get_date_range = get_date_range
        self.predicted_dict = {}

    def add(self, week, key, value):
        if week not in self.predicted_dict:
            self.predicted_dict[week] = {}

        if isinstance(value, (pd.Series, pd.DataFrame)):
            value = value.item()

        self.predicted_dict[week][key] = float(value)

    def flush_if_complete(self, week):
        data = self.predicted_dict.get(week, {})
        
        # Make sure that there is new week in the week data
        start_date, end_date = self.get_date_range()
        week_id = self.db_repo.ingest_week(week, start_date, end_date)

        if "pred" not in data or "actual" not in data:
            return

        model_info = self.get_model_info()

        pred   = data["pred"]
        actual = data["actual"]

        prediction_data = {
            "model_run_id"  : int(model_info["id"]),
            "week_id"       : week_id,
            "predicted_load": pred,
            "actual_load"   : actual,
            "mae"           : abs(pred - actual),
            "mape"          : (abs(pred - actual) / actual) * 100 if actual != 0 else None,
        }

        self.db_repo.upsert_prediction(prediction_data)
