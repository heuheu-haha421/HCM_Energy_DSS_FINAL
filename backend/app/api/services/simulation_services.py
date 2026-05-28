import numpy as np
import pandas as pd

from app.api.engines import (
    AllocationEngine,
    HistoricalReconstructionEngine,
    SpatialEngine,
    StressScoreEngine,
)
from app.api.config.grid_stress_config import GRID_STRESS_METHOD
from app.errors import InvalidInputError, NotFoundError
from app.models import PredictionModel


class SimulationService:
    def __init__(self, db, predictor=None):
        self.db        = db
        self.predictor = predictor
        
        self.allocation_engine                = AllocationEngine(db, predictor=self.predictor)
        self.stress_score_engine              = StressScoreEngine()
        self.historical_reconstruction_engine = HistoricalReconstructionEngine(db, self.allocation_engine, predictor=self.predictor)
        self.spatial_engine                   = SpatialEngine(predictor=self.predictor)

    def get_current_load(self):
        result = PredictionModel.get_latest_record(self.db)

        if not result:
            raise NotFoundError("No prediction data available")

        return dict(result)

    def allocate(self, payload: dict):
        weights = payload.get("weights")
        year    = payload.get("year")

        if not weights:
            raise InvalidInputError("Missing weights")
        if not year:
            raise InvalidInputError("Missing year")

        context    = self._build_grid_stress_context(year)
        total_load = context["total_load"]
        base_share = self._normalize_payload_weights(weights)
        df         = self._calculate_dynamic_allocation(
            context["ward_df"],
            total_load,
            context["weather_signal"],
            context["week_context"],
            base_share,
        )
        df = self._calculate_allocation_pct(df, total_load)
        df = self._assign_allocation_priority_level(df)

        return {
            "total_load": float(total_load),
            "avg_temp"  : context["avg_temp"],
            "week"      : context["current_context"].get("week"),
            "start_date": self._format_response_date(context["current_context"].get("start_date")),
            "end_date"  : self._format_response_date(context["current_context"].get("end_date")),
            "count"     : len(df),
            "results"   : self._allocation_records_for_response(df),
        }

    def grid_stress_priorities(self, payload: dict):
        limit = payload.get("limit", 10)
        year  = payload.get("year")

        if not year:
            raise InvalidInputError("Missing year")

        result      = self.calculate_grid_stress_priorities(year)
        top_results = result["results"][:limit]

        result["count"]   = len(top_results)
        result["results"] = top_results

        return result

    def calculate_grid_stress_priorities(self, year: int):
        context         = self._build_grid_stress_context(year)
        total_load      = context["total_load"]
        current_context = context["current_context"]
        avg_temp        = context["avg_temp"]
        df              = context["ward_df"]

        df["neighbors"] = df["ward_code"].map(self.spatial_engine._load_geojson_neighbors(df))

        previous_df, previous_previous_df = self.historical_reconstruction_engine._get_previous_allocated_dfs(
            year,
            current_context,
        )

        base_share = self.allocation_engine._get_base_share(df)
        current_share, df = self._calculate_dynamic_allocation_with_share(
            df,
            total_load,
            context["weather_signal"],
            context["week_context"],
            base_share,
        )
        df = self._calculate_stress_scores(
            df,
            previous_df,
            previous_previous_df,
            current_share,
            base_share,
        )

        df = df.sort_values(by="final_score_raw", ascending=False)

        return {
            "total_load": float(total_load),
            "avg_temp"  : avg_temp,
            "method"    : GRID_STRESS_METHOD,
            "week"      : current_context.get("week"),
            "start_date": self._format_response_date(current_context.get("start_date")),
            "end_date"  : self._format_response_date(current_context.get("end_date")),
            "count"     : len(df),
            "results"   : self._records_for_response(df),
        }

    def _format_response_date(self, value):
        if value is None:
            return None

        if hasattr(value, "date"):
            return value.date().isoformat()

        return str(value)

    def _build_grid_stress_context(self, year: int):
        latest_prediction = self.historical_reconstruction_engine._get_latest_prediction_record()
        total_load        = self.allocation_engine._get_total_load(latest_prediction)
        current_context   = self.historical_reconstruction_engine._get_current_prediction_context(latest_prediction)
        avg_temp          = self.historical_reconstruction_engine._get_avg_temp(current_context["week_id"])
        weather_signal    = self.allocation_engine._compute_weather_signal(avg_temp)
        week_context      = self.historical_reconstruction_engine._get_week_context(
            current_context.get("start_date"),
            current_context.get("end_date"),
        )

        return {
            "latest_prediction": latest_prediction,
            "total_load"       : total_load,
            "current_context"  : current_context,
            "avg_temp"         : avg_temp,
            "weather_signal"   : weather_signal,
            "week_context"     : week_context,
            "ward_df"          : self.allocation_engine._get_ward_proxy_weights(year),
        }

    def _calculate_dynamic_allocation_with_share(
        self,
        df            : pd.DataFrame,
        total_load    : float,
        weather_signal: float,
        week_context  : dict,
        base_share    : dict,
    ):
        current_share, sector_loads = self.allocation_engine._decompose_dynamic_load(
            total_load     = total_load,
            weather_signal = weather_signal,
            week_context   = week_context,
            base_share     = base_share,
        )
        df = self.allocation_engine._calculate_allocated_kwh(df, sector_loads)

        return current_share, df

    def _calculate_dynamic_allocation(
        self,
        df            : pd.DataFrame,
        total_load    : float,
        weather_signal: float,
        week_context  : dict,
        base_share    : dict,
    ):
        _, df = self._calculate_dynamic_allocation_with_share(
            df,
            total_load,
            weather_signal,
            week_context,
            base_share,
        )
        return df

    def _calculate_stress_scores(
        self,
        df                  : pd.DataFrame,
        previous_df         : pd.DataFrame | None,
        previous_previous_df: pd.DataFrame | None,
        current_share       : dict,
        base_share          : dict,
    ):
        df = self.stress_score_engine._calculate_rank_score(df)
        df = self.stress_score_engine._calculate_absolute_score(df)
        df = self.stress_score_engine._calculate_acceleration_score(
            df,
            previous_df,
            previous_previous_df,
        )
        df = self.stress_score_engine._calculate_sector_shift_score(df, current_share, base_share)
        df = self.stress_score_engine._calculate_priority_score(df)
        df = self.spatial_engine._apply_spatial_smoothing(df, self.stress_score_engine._minmax)
        df = self.stress_score_engine._assign_priority_level(df)
        df = self._add_explainability(df)

        return df

    def _records_for_response(self, df: pd.DataFrame):
        output_cols = [
            "ward_code",
            "ward_name",
            "allocated_kwh",
            "rank_score",
            "absolute_score",
            "acceleration_score",
            "final_score_raw",
            "final_score_ranked",
            "priority_level",
            "stress_factors",
            "primary_reason",
        ]

        df = df[output_cols].replace([np.inf, -np.inf], np.nan)
        df = df.astype(object).where(pd.notna(df), None)

        return df.to_dict(orient="records")

    def _add_explainability(self, df: pd.DataFrame):
        df                   = df.copy()
        df["stress_factors"] = df.apply(self._build_stress_factors, axis=1)
        df["primary_reason"] = df["stress_factors"].apply(self._build_primary_reason)

        return df

    def _build_stress_factors(self, row: pd.Series):
        return {
            "high_load"      : bool(row.get("absolute_score", 0.0) >= 0.80),
            "rapid_growth"   : bool(row.get("acceleration_score", 0.0) >= 0.70),
            "sector_shift"   : bool(row.get("sector_shift_score", 0.0) >= 0.60),
            "spatial_cluster": bool(row.get("spatial_score", 0.0) >= 0.65),
        }

    def _build_primary_reason(self, factors: dict):
        if factors["rapid_growth"] and factors["spatial_cluster"]:
            return "Rapid load acceleration combined with neighboring high-stress wards"
        if factors["high_load"] and factors["rapid_growth"]:
            return "High electricity allocation with abnormal week-over-week acceleration"
        if factors["high_load"] and factors["sector_shift"]:
            return "High electricity allocation and strong sensitivity to sector redistribution"
        if factors["high_load"]:
            return "Consistently high electricity allocation"
        if factors["rapid_growth"]:
            return "Abnormal load acceleration detected"
        if factors["sector_shift"]:
            return "Sensitive to weather or holiday-driven sector redistribution"
        if factors["spatial_cluster"]:
            return "Located near other high-priority wards"

        return "Composite priority score is higher than other wards"

    def _normalize_payload_weights(self, weights: dict):
        raw_weights = {
            "industrial" : weights.get("industrial", weights.get("w_industrial")),
            "residential": weights.get("residential", weights.get("w_residential")),
            "commercial" : weights.get("commercial", weights.get("w_commercial")),
            "services"   : weights.get("services", weights.get("w_services")),
        }

        missing = [
            sector
            for sector, value in raw_weights.items()
            if value is None
        ]

        if missing:
            raise InvalidInputError(f"Missing weights for sectors: {', '.join(missing)}")

        try:
            normalized_input = {
                sector: float(value)
                for sector, value in raw_weights.items()
            }
        except (TypeError, ValueError):
            raise InvalidInputError("Weights must be numeric")

        if any(value < 0 for value in normalized_input.values()):
            raise InvalidInputError("Weights must be non-negative")

        return self.allocation_engine._normalize_dict(normalized_input)

    def _calculate_allocation_pct(self, df: pd.DataFrame, total_load: float):
        df = df.copy()

        if total_load <= 0:
            df["allocation_pct"] = 0.0
        else:
            df["allocation_pct"] = (
                df["allocated_kwh"] / total_load * 100
            ).round(3)
            diff = round(100 - df["allocation_pct"].sum(), 3)

            if not df.empty and diff != 0:
                idx = df["allocation_pct"].idxmax()
                df.loc[idx, "allocation_pct"] = round(
                    df.loc[idx, "allocation_pct"] + diff,
                    3,
                )

        df["allocated_kwh"] = df["allocated_kwh"].round(3)

        return df

    def _assign_allocation_priority_level(self, df: pd.DataFrame):
        df            = df.copy()
        allocated_kwh = df["allocated_kwh"]

        mean_allocated = allocated_kwh.mean()
        std_allocated  = allocated_kwh.std()

        if std_allocated != std_allocated:
            std_allocated = 0.0

        medium_threshold = mean_allocated + (0.5 * std_allocated)
        high_threshold   = mean_allocated + (1.5 * std_allocated)

        df["priority_level"] = "LOW"
        df.loc[
            (allocated_kwh > medium_threshold) & (allocated_kwh <= high_threshold),
            "priority_level"
        ] = "MEDIUM"
        df.loc[allocated_kwh > high_threshold, "priority_level"] = "HIGH"

        return df

    def _allocation_records_for_response(self, df: pd.DataFrame):
        output_cols = [
            "ward_code",
            "ward_name",
            "allocation_pct",
            "allocated_kwh",
            "priority_level",
        ]

        df = df[output_cols].replace([np.inf, -np.inf], np.nan)
        df = df.astype(object).where(pd.notna(df), None)

        return df.to_dict(orient="records")
