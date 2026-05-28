import time
import threading
from datetime import datetime

import pandas as pd
import pytz

import traceback

from app.config import EnvManager

from .prediction import (
    ClientBroadcaster,
    DataUpdateHandler,
    EnergyRepository,
    FirstRunProcessor,
    HolidayReader,
    ModelLoader,
    PredictionConfig,
    PredictionRepository,
    PredictionState,
    PredictionStore,
    PreprocessBuilder,
    RuntimeSnapshot,
    WeatherExtractor,
    WeatherRefreshHandler,
    WeeklyPredictionCache,
)
from ..utilities import DebugMixin


class Prediction(DebugMixin):
    DEMO_MODE_ENV     = "IS_DEMO_MODE"
    SLEEP_SECONDS_ENV = "SLEEP_SECONDS"

    def __init__(self, db, manager, loop):
        self.db      = db
        self.manager = manager
        self.loop    = loop

        self.env_manager = EnvManager()
        self.env_manager.load({self.DEMO_MODE_ENV, self.SLEEP_SECONDS_ENV})

        self.config  = PredictionConfig()
        self.is_demo = self.env_manager.get_bool(self.DEMO_MODE_ENV, False)
        self.config.sleep_seconds = self.env_manager.get_int(
            self.SLEEP_SECONDS_ENV,
            self.config.sleep_seconds,
        )
        self._sync_runtime_env()

        self.state       = PredictionState()
        self.thread_lock = threading.Lock()
        self.bRun        = False

        self.VN_TZ = pytz.timezone(self.config.vn_timezone)

        self.weights = None

        self.week_ids = {}

        self.model_loader       = ModelLoader(self.db)
        self.energy_repo        = EnergyRepository(self.db)
        self.prediction_repo    = PredictionRepository(self.db)
        self.weather_extractor  = WeatherExtractor(self.config.location)
        self.holiday_reader     = HolidayReader(self.db)
        self.preprocess_builder = PreprocessBuilder(
            self.weather_extractor,
            self.holiday_reader,
        )

        self.weekly_predictions = WeeklyPredictionCache(
            self.config.max_weekly_predictions
        )
        self.preprocessed_data = None
        self.global_week_id    = None

        self.prediction_store = PredictionStore(
            self.prediction_repo,
            self._get_model_info,
            self._get_current_date_range,
        )

        self.data_update_handler = DataUpdateHandler(
            self.energy_repo,
            self.prediction_store,
            self.state,
            self.week_ids,
        )

        self.first_run_processor = FirstRunProcessor(
            self.config,
            self.energy_repo,
            self.prediction_repo,
            self.prediction_store,
            self.preprocess_builder,
            self.weather_extractor,
            self.state,
            self.week_ids,
            self.add_weekly_prediction,
        )

        self.weather_refresh_handler = WeatherRefreshHandler(
            self.weather_extractor,
            self.prediction_repo,
        )

        self.client_broadcaster = ClientBroadcaster(
            self.manager,
            self.loop,
            self.VN_TZ,
        )

        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        with self.thread_lock:
            if self.bRun and self.thread.is_alive():
                return False

            if self.thread.is_alive():
                return False

            self.bRun                  = True
            self.state.first_run       = True
            self.state.is_data_updated = True
            self.preprocessed_data     = None
            self.global_week_id        = None
            self.thread                = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

        return True

    def stop(self):
        if not self.bRun and not self.thread.is_alive():
            return False

        self.bRun = False
        if self.thread.is_alive():
            self.thread.join()

        return True

    def get_time(self):
        now = datetime.now(self.VN_TZ)
        return now.weekday() == 0 and now.hour == 0 and now.minute == 0

    def update_demo_settings(self, is_demo: bool, sleep_seconds: int):
        if sleep_seconds <= 0:
            raise ValueError("sleep_seconds must be greater than 0")

        with self.thread_lock:
            self.is_demo              = is_demo
            self.config.sleep_seconds = sleep_seconds
            self._sync_runtime_env()

        return {
            "is_demo_mode" : self.is_demo,
            "sleep_seconds": self.config.sleep_seconds,
        }

    def _sync_runtime_env(self):
        self.env_manager.set_many({
            self.DEMO_MODE_ENV    : str(self.is_demo).lower(),
            self.SLEEP_SECONDS_ENV: str(self.config.sleep_seconds),
        })

    @property
    def model(self):
        return self.model_loader.model

    @property
    def model_info(self):
        return self.model_loader.model_info

    def get_model(self):
        self.model_loader.load_active_model()

    def predict(self, df: pd.DataFrame):
        if self.model is None:
            raise RuntimeError("Model not loaded")

        return float(self.model.predict(df)[0])

    def create_input_data(self, total_load):
        return self.preprocess_builder.build(
            total_load,
            self.state.start_date,
            self.state.end_date,
        )

    def get_last_n_energy_data(self, n=3):
        return self.data_update_handler.get_last_n_energy_data(n)

    def run(self):
        preprocessed_data = self.preprocessed_data
        global_week_id    = self.global_week_id

        while self.bRun:
            try:
                model_ready = self._ensure_model_ready()
                if not model_ready:
                    self._sleep(self.config.sleep_seconds)
                    continue

                snapshot = self._get_runtime_snapshot()
                self._mark_updated_if_scheduled_time(snapshot)

                result = self._process_current_state(
                    snapshot,
                    preprocessed_data,
                    global_week_id,
                )

                preprocessed_data = result["preprocessed_data"]
                global_week_id    = result["global_week_id"]
                prediction        = result["prediction"]

                with self.thread_lock:
                    self.preprocessed_data = preprocessed_data
                    self.global_week_id    = global_week_id

                if preprocessed_data is None:
                    self.printDebug("Preprocessed data not ready")
                    self._sleep(self.config.duplicate_week_sleep_seconds)
                    continue

                if not snapshot.is_first:
                    prediction = self._predict_and_save(preprocessed_data)

                if len(self.manager.connections) > 0:
                    self.send_to_client(prediction, preprocessed_data)

            except RuntimeError as re:
                self.printDebug(f'Runtime error: {re}')
            except Exception as e:
                err = traceback.format_exc()
                self.printDebug(err, with_traceback=True)

            self._sleep(self.config.sleep_seconds)

    def _ensure_model_ready(self):
        if self.model is not None:
            return True

        self.get_model()
        return self.model is not None

    def _get_runtime_snapshot(self):
        with self.thread_lock:
            return RuntimeSnapshot(
                is_first   = self.state.first_run,
                is_updated = self.state.is_data_updated,
                week       = self.state.week,
                start_date = self.state.start_date,
                end_date   = self.state.end_date,
            )

    def _mark_updated_if_scheduled_time(self, snapshot: RuntimeSnapshot):
        if not self.get_time():
            return

        with self.thread_lock:
            self.state.is_data_updated = True
            snapshot.is_updated        = True

    def _process_current_state(
        self,
        snapshot: RuntimeSnapshot,
        preprocessed_data,
        global_week_id,
    ):
        prediction = None

        if snapshot.is_first:
            preprocessed_data, prediction, global_week_id = self._handle_first_run()
            self.printDebug(f"First run completed. Global week id: {global_week_id}")
        elif snapshot.is_updated:
            preprocessed_data, global_week_id = self._handle_data_updated()
            self.printDebug(f"Data updated. Global week id: {global_week_id}")
        else:
            preprocessed_data = self._handle_weather_refresh(
                preprocessed_data,
                snapshot,
                global_week_id,
            )
            self.printDebug(f"Weather data refreshed for week {self.state.week}. Global week id: {global_week_id}")

        return {
            "preprocessed_data": preprocessed_data,
            "prediction"       : prediction,
            "global_week_id"   : global_week_id,
        }

    def _handle_first_run(self):
        preprocessed_data, prediction, global_week_id = self.first_run_processor.run(
            self.model
        )

        if preprocessed_data is None:
            return None, None, global_week_id

        with self.thread_lock:
            self.state.first_run       = False
            self.state.is_data_updated = False

        return preprocessed_data, prediction, global_week_id

    def _handle_data_updated(self):
        total_load, global_week_id, is_new_week = self.get_last_n_energy_data(
            self.config.min_energy_rows
        )

        if not is_new_week:
            self.printDebug(f"Week {self.state.week} already processed")
            self._sleep(self.config.duplicate_week_sleep_seconds)
            return None, global_week_id

        preprocessed_data = self.create_input_data(total_load)
        
        if "week_id" in preprocessed_data.columns:
            preprocessed_data = preprocessed_data.drop(columns=["week_id"])

        with self.thread_lock:
            self.state.is_data_updated = False

        return preprocessed_data, global_week_id

    def _handle_weather_refresh(
        self,
        preprocessed_data,
        snapshot: RuntimeSnapshot,
        global_week_id,
    ):
        return self.weather_refresh_handler.refresh_in_place(
            preprocessed_data,
            snapshot.start_date,
            snapshot.end_date,
            global_week_id,
        )

    def _predict_and_save(self, preprocessed_data):
        prediction = self.preprocess_builder.decode_prediction(
            self.predict(preprocessed_data),
            self.state.start_date,
            self.state.end_date,
        )

        with self.thread_lock:
            self.add_weekly_prediction(prediction)
            self.add_to_predicted_dict(self.state.week, "pred", prediction)
            self.flush_prediction_to_db(self.state.week)

        return prediction

    def _sleep(self, seconds):
        time.sleep(seconds)

    def send_to_client(self, prediction, preprocessed_data):
        self.client_broadcaster.send(
            self.state.week,
            prediction,
            preprocessed_data,
        )

    def add_weekly_prediction(self, prediction):
        self.weekly_predictions.add(prediction)

    def get_latest_prediction(self):
        with self.thread_lock:
            return self.weekly_predictions.latest()

    def add_to_predicted_dict(self, week, key, value):
        self.prediction_store.add(week, key, value)

    def flush_prediction_to_db(self, week):
        self.prediction_store.flush_if_complete(week)

    def update_model(self):
        with self.thread_lock:
            self.printDebug("Model updated, reloading...")
            self.model_loader.mark_reload_required()

    def update_data(self):
        with self.thread_lock:
            self.printDebug("Data updated, refreshing...")
            self.state.is_data_updated = True
            
    def update_weight(self, new_weights):
        with self.thread_lock:
            self.printDebug(f"Weights updated: {new_weights}")
            self.weights = new_weights

    def _get_model_info(self):
        return self.model_info

    def _get_current_date_range(self):
        return self.state.start_date, self.state.end_date


if __name__ == "__main__":
    # prediction = Prediction()
    # prediction.start()

    while True:
        time.sleep(1)
