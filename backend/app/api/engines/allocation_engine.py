import json
import pandas as pd
from app.errors import InvalidInputError, NotFoundError
from app.api.config.grid_stress_config import CONFIG, SECTOR_COLUMNS
from app.models import WardInfraModel, ScenarioModel

class AllocationEngine:
    def __init__(self, db, predictor=None):
        self.db        = db
        self.predictor = predictor
        
        self.config         = CONFIG
        self.sector_columns = SECTOR_COLUMNS

    def _get_total_load(self, latest_prediction: dict):
        latest_prediction = dict(latest_prediction)

        runtime_prediction = (
            self.predictor.get_latest_prediction()
            if self.predictor
            else None
        )

        if runtime_prediction is not None:
            return float(runtime_prediction)

        predicted_load = latest_prediction.get("predicted_load")

        if predicted_load is None:
            raise InvalidInputError(
                "Latest prediction record does not contain 'predicted_load'"
            )

        return float(predicted_load)
        
    def _get_ward_proxy_weights(self, year: int):
        rows = WardInfraModel.get_by_year(self.db, year)
        
        if not rows:
            raise NotFoundError(f"No ward infrastructure data found for year {year} in DB")
        
        df = pd.DataFrame([dict(row) for row in rows])
        
        output_cols = ["ward_code", "ward_name"]
        
        for sector_config in self.sector_columns.values():
            weight_col = sector_config["weight"]
            source_col = sector_config["source"]
            
            if weight_col in df.columns:
                values =pd.to_numeric(df[weight_col], errors="coerce").fillna(0.0)
                if (values < 0).any():
                    raise InvalidInputError(f"{weight_col} contains negative values")
                
                total = values.sum()
                if total <= 0:
                    raise InvalidInputError(f"{weight_col} total must be positive")
                
                df[weight_col] = values / total
                output_cols.append(weight_col)
                continue
            
            if source_col not in df.columns:
                raise InvalidInputError(f"Missing ward proxy column: {weight_col} or {source_col}")
            
            values = pd.to_numeric(df[source_col], errors="coerce").fillna(0.0)

            if (values < 0).any():
                raise InvalidInputError(f"{source_col} contains negative values")

            total = values.sum()

            if total <= 0:
                raise InvalidInputError(f"{source_col} total must be positive")

            df[weight_col] = values / total
            output_cols.extend([weight_col, source_col])
            
        for sector_config in self.sector_columns.values():
            for share_col in sector_config["share_aliases"]:
                if share_col in df.columns and share_col not in output_cols:
                    output_cols.append(share_col)

        return df[output_cols]
        
    def _get_base_share(self, df: pd.DataFrame):
        scenario_share = self._get_scenario_base_share()

        if scenario_share is not None:
            return scenario_share

        share = {}

        for sector, sector_config in self.sector_columns.items():
            share_col = next(
                (col for col in sector_config["share_aliases"] if col in df.columns),
                None,
            )

            if share_col is not None:
                values = pd.to_numeric(df[share_col], errors="coerce").dropna()

                if not values.empty:
                    share[sector] = float(values.iloc[0])

        if len(share) == len(self.sector_columns):
            return self._normalize_dict(share)

        weight_totals = {}

        for sector, sector_config in self.sector_columns.items():
            weight_col = sector_config["weight"]

            if weight_col not in df.columns:
                continue

            values = pd.to_numeric(df[weight_col], errors="coerce").fillna(0.0)

            if (values < 0).any():
                raise InvalidInputError(f"{weight_col} contains negative values")

            weight_totals[sector] = float(values.sum())

        if len(weight_totals) == len(self.sector_columns):
            return self._normalize_dict(weight_totals)

        source_totals = {}

        for sector, sector_config in self.sector_columns.items():
            source_col = sector_config["source"]

            if source_col not in df.columns:
                continue

            values = pd.to_numeric(df[source_col], errors="coerce").fillna(0.0)

            if (values < 0).any():
                raise InvalidInputError(f"{source_col} contains negative values")

            source_totals[sector] = float(values.sum())

        if len(source_totals) != len(self.sector_columns):
            missing = [
                sector_config["source"]
                for sector_config in self.sector_columns.values()
                if sector_config["source"] not in df.columns
            ]
            raise InvalidInputError(
                f"Missing DB columns for base share: {', '.join(missing)}"
            )

        return self._normalize_dict(source_totals)
    
    def _get_scenario_base_share(self):
        runtime_weights = getattr(self.predictor, "weights", None)

        if runtime_weights:
            return self._normalize_dict(runtime_weights)

        scenarios = ScenarioModel.get_all(self.db)

        if not scenarios:
            return None

        scenario = dict(scenarios[0])
        weights  = json.loads(scenario["weight"])

        return self._normalize_dict({
            "industrial" : weights["w_industrial"],
            "residential": weights["w_residential"],
            "commercial" : weights["w_commercial"],
            "services"   : weights["w_services"],
        })

    def _decompose_dynamic_load(
        self,
        total_load    : float,
        weather_signal: float,
        week_context  : dict,
        base_share    : dict,
    ):
        if total_load < 0:
            raise InvalidInputError("total_load must be non-negative")

        share = base_share.copy()

        for sector, coef in self.config["WEATHER_ADJUSTMENT"].items():
            share[sector] += coef * weather_signal

        if week_context.get("is_holiday", False):
            for sector, delta in self.config["HOLIDAY_ADJUSTMENT"].items():
                share[sector] += delta

        current_share = self._normalize_dict(share)

        sector_loads = {
            sector: total_load * pct
            for sector, pct in current_share.items()
        }

        return current_share, sector_loads
    
    def _compute_weather_signal(self, avg_temp: float):
        base_temp = self.config.get("BASE_TEMP", 26.0)
        max_temp  = self.config.get("MAX_TEMP", 35.0)
        
        if max_temp <= base_temp:
            raise InvalidInputError("MAX_TEMP must be greater than BASE_TEMP")
        
        signal = (avg_temp - base_temp) / (max_temp - base_temp)
        
        return max(0.0, min(signal, 1.0))
        
    def _normalize_dict(self, data: dict):
        total = sum(data.values())

        if total <= 0:
            raise InvalidInputError("Total share must be positive")

        return {key: value / total for key, value in data.items()}
    
    def _calculate_allocated_kwh(self, df: pd.DataFrame, sector_loads: dict):
        df = df.copy()

        df["allocated_kwh"] = (
            df["weight_ind"] * sector_loads["industrial"]
            + df["weight_res"] * sector_loads["residential"]
            + df["weight_com"] * sector_loads["commercial"]
            + df["weight_ser"] * sector_loads["services"]
        )

        return df
