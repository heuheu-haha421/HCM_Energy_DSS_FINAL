import asyncio
from datetime import datetime

import pandas as pd

from ..preprocess_data import PreprocessData
from .config import PredictionConfig, PredictionState
from .helpers import SafeValue, WeatherExtractor, WeekHelper
from .repositories import EnergyRepository, PredictionRepository, PredictionStore
from ...utilities import DebugMixin

class ClientBroadcaster(DebugMixin):
    def __init__(self, manager, loop, timezone):
        self.manager  = manager
        self.loop     = loop
        self.timezone = timezone

    def send(self, week, prediction, preprocessed_data):
        temp_value = self._extract_temp(preprocessed_data)

        data_send = {
            "week"          : week,
            "timestamp"     : datetime.now(self.timezone).isoformat(),
            "predicted_load": SafeValue.to_float(prediction),
            "simulated_temp": temp_value,
        }

        self.printDebug(f"Broadcasting websocket data: {data_send}")

        asyncio.run_coroutine_threadsafe(
            self.manager.broadcast(data_send),
            self.loop,
        )

    def _extract_temp(self, preprocessed_data):
        if (
            preprocessed_data is not None
            and not preprocessed_data.empty
            and "temp" in preprocessed_data.columns
        ):
            return SafeValue.to_float(preprocessed_data["temp"].iloc[-1])

        return None


class PreprocessBuilder:
    def __init__(self, weather_extractor: WeatherExtractor, holiday_reader):
        self.weather_extractor = weather_extractor
        self.holiday_reader    = holiday_reader

    def build(self, total_load, start_date, end_date):
        weather_data = self.weather_extractor.extract(start_date, end_date)

        if weather_data is None:
            raise RuntimeError("Weather data missing")

        target_week = WeekHelper.get_next_week(total_load["week"].iloc[-1])

        return self.build_prediction_from_weather(
            total_load,
            weather_data,
            target_week,
            start_date,
            end_date,
        )

    def build_prediction_from_weather(
        self,
        total_load,
        weather_data,
        target_week,
        target_start_date,
        target_end_date,
    ):
        holiday_data = self.holiday_reader.read()

        return PreprocessData(
            total_load.reset_index(drop=True),
            weather_data.reset_index(drop=True),
            holiday_data,
        ).preprocess_for_prediction(
            target_week,
            target_start_date,
            target_end_date,
        )

    def decode_prediction(self, prediction, start_date, end_date):
        holiday_data = self.holiday_reader.read()

        return PreprocessData(
            pd.DataFrame(),
            pd.DataFrame(),
            holiday_data,
        ).decode_prediction(prediction, start_date, end_date)


class DataUpdateHandler(DebugMixin):
    def __init__(
        self,
        energy_repo     : EnergyRepository,
        prediction_store: PredictionStore,
        state           : PredictionState,
        week_ids        : dict,
    ):
        self.energy_repo      = energy_repo
        self.prediction_store = prediction_store
        self.state            = state
        self.week_ids         = week_ids

    def get_last_n_energy_data(self, n=3):
        total_load, current_week_id, ok = self.energy_repo.get_last_n(n)

        if not ok:
            return None, None, False

        last_row     = total_load.iloc[-1]
        current_week = last_row["week"]

        self.prediction_store.add(
            current_week,
            "actual",
            last_row["total_load (kWh)"],
        )
        self.prediction_store.flush_if_complete(current_week)

        self.state.week = WeekHelper.get_next_week(current_week)
        self.state.start_date, self.state.end_date = WeekHelper.get_next_date_range(
            last_row["end_date"]
        )
        next_week_id = self.prediction_store.db_repo.ingest_week(
            self.state.week,
            self.state.start_date,
            self.state.end_date,
        )

        start_date  = pd.to_datetime(last_row["start_date"])
        is_new_week = self._is_new_week(start_date)

        self.state.last_start_date  = start_date
        self.week_ids[current_week] = current_week_id

        return total_load, next_week_id, is_new_week

    def _is_new_week(self, start_date):
        if self.state.last_start_date is None:
            return True

        return self.state.last_start_date != start_date


class FirstRunProcessor(DebugMixin):
    def __init__(
        self,
        config            : PredictionConfig,
        energy_repo       : EnergyRepository,
        prediction_repo   : PredictionRepository,
        prediction_store  : PredictionStore,
        preprocess_builder: PreprocessBuilder,
        weather_extractor : WeatherExtractor,
        state             : PredictionState,
        week_ids          : dict,
        add_weekly_prediction,
    ):
        self.config                = config
        self.energy_repo           = energy_repo
        self.prediction_repo       = prediction_repo
        self.prediction_store      = prediction_store
        self.preprocess_builder    = preprocess_builder
        self.weather_extractor     = weather_extractor
        self.state                 = state
        self.week_ids              = week_ids
        self.add_weekly_prediction = add_weekly_prediction

    def run(self, model):
        self.printDebug("FIRST RUN -> batch per week")

        prediction_data = self.prediction_repo.get_all()
        tmp_total_load, _, ok = self.energy_repo.get_all()

        if not ok or tmp_total_load is None or len(tmp_total_load) < self.config.min_energy_rows:
            self.printDebug("No energy data found in DB")
            return None, None, False

        total_load = self._get_missing_prediction_energy_rows(
            tmp_total_load,
            prediction_data,
        )

        if len(total_load) < self.config.min_energy_rows:
            total_load = tmp_total_load.iloc[-3:].copy()

        total_load_without_id = total_load.copy()
        weather_rows          = []
        preprocessed_data     = None
        prediction            = None
        global_week_id        = None
        is_loop               = False

        for i in range(2, len(total_load_without_id)):
            week_data = total_load_without_id.iloc[i - 2 : i + 1].copy()

            current_week    = week_data["week"].iloc[-1]
            current_week_id = int(week_data["week_id"].iloc[-1])
            
            week_data = week_data.drop(columns=["week_id"])

            self._save_actual(current_week, week_data, current_week_id)

            preprocessed_data, weather_row, loop_start, loop_end, global_week_id = (
                self._prepare_next_week(week_data)
            )
            weather_rows.append(weather_row)

            prediction = self._predict_and_store(
                model,
                preprocessed_data,
                loop_start,
                loop_end,
            )

            self.printDebug(f"Week_id: {global_week_id}, week: {self.state.week}, current_week: {current_week}, start_date: {self.state.start_date}, end_date: {self.state.end_date}, prediction: {prediction}")
            
            is_loop = True
        
        if not is_loop:
            self.printDebug("Not enough data for loop -> using last 3 rows for prediction")
            total_load_without_id = tmp_total_load.copy().drop(columns=["week_id"])
            last_three_data       = total_load_without_id.iloc[-3:].copy()

            preprocessed_data, weather_row, _, _, global_week_id = self._prepare_next_week(
                last_three_data
            )
            weather_rows.append(weather_row)
            
        self.prediction_repo.upsert_many_weather(weather_rows)

        return preprocessed_data, prediction, global_week_id

    def _prepare_next_week(self, week_data):
        current_week = week_data["week"].iloc[-1]
        next_week    = WeekHelper.get_next_week(current_week)
        start_date, end_date = WeekHelper.get_next_date_range(
            week_data["end_date"].iloc[-1]
        )
        next_week_id = self.prediction_repo.ingest_week(
            next_week,
            start_date,
            end_date,
        )

        weather_data      = self.weather_extractor.extract(start_date, end_date)
        weather_row       = self.weather_extractor.to_weekly_row(next_week_id, weather_data)
        preprocessed_data = self.preprocess_builder.build_prediction_from_weather(
            week_data,
            weather_data,
            next_week,
            start_date,
            end_date,
        )

        self._set_state(next_week, start_date, end_date)

        return preprocessed_data, weather_row, start_date, end_date, next_week_id

    def _set_state(self, week, start_date, end_date):
        self.state.week       = week
        self.state.start_date = start_date
        self.state.end_date   = end_date

    def _predict_and_store(self, model, preprocessed_data, start_date, end_date):
        prediction = self.preprocess_builder.decode_prediction(
            float(model.predict(preprocessed_data)[0]),
            start_date,
            end_date,
        )

        self.add_weekly_prediction(prediction)
        self.prediction_store.add(self.state.week, "pred", prediction)
        self.prediction_store.flush_if_complete(self.state.week)

        return prediction

    def _get_missing_prediction_energy_rows(self, tmp_total_load, prediction_data):
        df = tmp_total_load.reset_index(drop=True).copy()

        if len(df) <= 3:
            self.printDebug("Not enough energy rows ---> using all energy data")
            return df

        if prediction_data is None or len(prediction_data) == 0:
            self.printDebug("No prediction data found ---> using all energy data")
            return df

        if "week_id" not in prediction_data.columns:
            self.printDebug("prediction_data missing week_id ---> fallback full data")
            return df

        if "week_id" not in df.columns:
            self.printDebug("tmp_total_load missing week_id ---> fallback full data")
            return df

        predicted_week_ids = set(
            prediction_data["week_id"]
            .dropna()
            .tolist()
        )

        # Just check missing from 4th row onward
        # because the first 3 rows are context, by default no prediction exists for them.
        predictable_df = df.iloc[3:].copy()

        missing_mask = ~predictable_df["week_id"].isin(predicted_week_ids)
        missing_positions = predictable_df.index[missing_mask].tolist()

        if not missing_positions:
            self.printDebug("No missing predictable rows ---> using last 3 rows as context")
            return df.iloc[-3:].copy()

        first_missing_pos = missing_positions[0]

        # Get 3 rows before the first missing predictable row as input context
        start_pos = max(0, first_missing_pos - 3)

        result = df.iloc[start_pos:].copy()

        self.printDebug(
            f"Missing predictable rows found ---> "
            f"first_missing_pos={first_missing_pos}, "
            f"context_start_pos={start_pos}, "
            f"returned_rows={len(result)}"
        )

        return result

    def _save_actual(self, week, week_data, week_id):
        self.prediction_store.add(
            week,
            "actual",
            week_data["total_load (kWh)"].iloc[-1],
        )
        self.prediction_store.flush_if_complete(week)
        self.week_ids[week] = week_id


class WeatherRefreshHandler(DebugMixin):
    def __init__(
        self,
        weather_extractor: WeatherExtractor,
        prediction_repo  : PredictionRepository,
    ):
        self.weather_extractor = weather_extractor
        self.prediction_repo   = prediction_repo

    def refresh_in_place(self, preprocessed_data, start_date, end_date, week_id):
        self.printDebug(f"Refreshing weather data in-place for week_id={week_id}, date_range=({start_date}, {end_date})")
        new_weather = self.weather_extractor.extract(start_date, end_date)

        weather_row = self.weather_extractor.to_weekly_row(week_id, new_weather)

        if new_weather is not None and preprocessed_data is not None:
            new_weather             = new_weather.astype(float)
            cols                    = new_weather.columns
            preprocessed_data[cols] = new_weather.values

            self.prediction_repo.upsert_weather(weather_row)
            self.printDebug("Weather updated in-place")

        return preprocessed_data
