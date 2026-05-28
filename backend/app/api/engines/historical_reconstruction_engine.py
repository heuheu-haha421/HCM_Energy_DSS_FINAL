import pandas as pd

from app.models import PredictionModel, WeatherWeeklyModel, HolidayModel
from app.errors import InvalidInputError, NotFoundError

class HistoricalReconstructionEngine:
    def __init__(self, db, allocation_engine, predictor=None):
        self.db                = db
        self.predictor         = predictor
        self.allocation_engine = allocation_engine

    def _get_latest_prediction_record(self):
        latest = PredictionModel.get_latest_record(self.db)
        
        if not latest:
            raise NotFoundError("No prediction records found")
        
        return latest

    def _get_current_prediction_context(self, latest_prediction: dict):
        latest_prediction = dict(latest_prediction)

        if not self.predictor:
            return latest_prediction

        runtime_prediction = self.predictor.get_latest_prediction()

        if runtime_prediction is None:
            return latest_prediction

        current_week_id = getattr(self.predictor, "global_week_id", None)
        state           = getattr(self.predictor, "state", None)

        if current_week_id is None:
            return latest_prediction

        context            = latest_prediction.copy()
        context["week_id"] = current_week_id

        if state:
            context["week"]       = getattr(state, "week", context.get("week"))
            context["start_date"] = getattr(state, "start_date", context.get("start_date"))
            context["end_date"]   = getattr(state, "end_date", context.get("end_date"))

        return context
            
    def _get_avg_temp(self, week_id: int):
        weather = WeatherWeeklyModel.get_by_week_id(self.db, week_id)
        
        if not weather:
            weather = WeatherWeeklyModel.get_latest(self.db)
            
        if not weather or weather["temp"] is None:
            raise NotFoundError("No weather data available for grid stress priority")
        
        return float(weather["temp"])
    
    def _get_week_context(self, start_date, end_date):
        if not start_date or not end_date:
            return {"is_holiday": False}
        
        start = pd.to_datetime(start_date)
        end   = pd.to_datetime(end_date)
        
        is_holiday = False
        
        for row in HolidayModel.get_all(self.db):
            holiday_start = pd.to_datetime(row["start"])
            holiday_end   = pd.to_datetime(row["end"])
            
            if max(start, holiday_start) <= min(end, holiday_end):
                is_holiday = True
                break
            
        return {"is_holiday": is_holiday}
            
    def _get_previous_allocated_dfs(self, year: int, latest_prediction: dict):
        predictions = PredictionModel.get_all(self.db)

        if not predictions or len(predictions) < 3:
            return None, None

        latest_week_id = latest_prediction["week_id"]
        historical     = []
        seen_week_ids  = {latest_week_id}

        for row in predictions:
            record  = dict(row)
            week_id = record["week_id"]

            if week_id in seen_week_ids:
                continue

            if record.get("actual_load") is None:
                continue

            seen_week_ids.add(week_id)
            historical.append(record)

            if len(historical) == 2:
                break

        if len(historical) < 2:
            return None, None

        try:
            return (
                self._get_allocated_df_for_actual_load(year, historical[0]),
                self._get_allocated_df_for_actual_load(year, historical[1]),
            )
        except (InvalidInputError, NotFoundError):
            return None, None

    def _get_allocated_df_for_actual_load(self, year: int, prediction: dict):
        df             = self.allocation_engine._get_ward_proxy_weights(year)
        base_share     = self.allocation_engine._get_base_share(df)
        avg_temp       = self._get_avg_temp(prediction["week_id"])
        weather_signal = self.allocation_engine._compute_weather_signal(avg_temp)
        _, sector_loads = self.allocation_engine._decompose_dynamic_load(
            total_load     = float(prediction["actual_load"]),
            weather_signal = weather_signal,
            week_context   = self._get_week_context(
                prediction.get("start_date"),
                prediction.get("end_date"),
            ),
            base_share=base_share,
        )
        return self.allocation_engine._calculate_allocated_kwh(df, sector_loads)