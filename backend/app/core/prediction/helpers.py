from typing import Optional

import pandas as pd
import xgboost as xgb
import os

from app.models import HolidayModel, ModelRunModel
from app.utilities import DebugMixin

from ..weather import Weather


class SafeValue:
    @staticmethod
    def to_float(value):
        if value is None:
            return None

        if pd.isna(value):
            return None

        try:
            return float(value)
        except Exception:
            return None


class WeekHelper:
    @staticmethod
    def get_next_week(week_value: str) -> str:
        week, year = map(int, week_value.split("/"))

        if week == 52:
            week = 1
            year += 1
        else:
            week += 1

        return f"{week:02d}/{year}"

    @staticmethod
    def get_next_date_range(end_date):
        end_date      = pd.to_datetime(end_date)
        start_date    = end_date + pd.Timedelta(days=1)
        next_end_date = end_date + pd.Timedelta(days=7)
        return start_date, next_end_date


class WeatherExtractor:
    WEATHER_FIELDS = ["temp", "tmin", "tmax", "rhum", "prcp", "wspd", "pres"]

    def __init__(self, location: str):
        self.location = location

    def extract(self, start_date, end_date):
        if start_date is None or end_date is None:
            return None

        weather = Weather(self.location, start_date, end_date)
        return weather.get_weather_data()

    def to_weekly_row(self, week_id, weather_df: Optional[pd.DataFrame]):
        row = {"week_id": week_id}

        for col in self.WEATHER_FIELDS:
            row[col] = self._get_last_value(weather_df, col)

        return row

    def _get_last_value(self, df: Optional[pd.DataFrame], col: str):
        if df is None or df.empty or col not in df.columns:
            return None

        return df[col].iloc[-1]


class HolidayReader:
    def __init__(self, db):
        self.db = db

    def read(self):
        rows = HolidayModel.get_all(self.db)

        if not rows:
            raise RuntimeError("Holiday data not found in DB")

        return pd.DataFrame([dict(row) for row in rows])


class ModelLoader(DebugMixin):
    def __init__(self, db):
        self.db         = db
        self.model      = None
        self.model_info = None

    def load_active_model(self):
        res = ModelRunModel.get_active(self.db)

        if not res:
            self.model      = None
            self.model_info = None
            raise RuntimeError("Initial model not found in DB")

        self.model_info = pd.DataFrame([dict(res)]).iloc[-1]
        model_path      = self.model_info["model_path"]

        self.printDebug(f"Loading model from: {model_path}")
        self.model = self._load_model_from_path(model_path)

    def mark_reload_required(self):
        self.model = None

    def _load_model_from_path(self, model_path):
        if not os.path.exists(model_path):
            raise RuntimeError(f"Model not found: {model_path}")

        model = xgb.XGBRegressor()
        model.load_model(model_path)
        return model


class WeeklyPredictionCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.items    = []

    def add(self, prediction):
        self.items.append(float(prediction))

        if len(self.items) > self.max_size:
            self.items.pop(0)

    def latest(self):
        if not self.items:
            return None

        return self.items[-1]
