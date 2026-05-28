import numpy as np
import pandas as pd

from app.api.config.grid_stress_config import CONFIG


class StressScoreEngine:
    def __init__(self):
        self.config = CONFIG
    
    def _calculate_rank_score(self, df: pd.DataFrame):
        df                  = df.copy()
        df["allocated_log"] = np.log1p(df["allocated_kwh"])
        df["rank_score"]    = df["allocated_log"].rank(pct=True, method="average")
        return df

    def _calculate_absolute_score(self, df: pd.DataFrame):
        df            = df.copy()
        max_allocated = df["allocated_log"].max()

        if pd.isna(max_allocated) or max_allocated <= 0:
            df["absolute_score"] = 0.0
        else:
            df["absolute_score"] = df["allocated_log"] / max_allocated

        return df

    def _calculate_acceleration_score(
        self,
        df                  : pd.DataFrame,
        previous_df         : pd.DataFrame | None,
        previous_previous_df: pd.DataFrame | None,
    ):
        df = df.copy()

        if previous_df is None or previous_previous_df is None:
            df["growth_t"]           = 0.0
            df["growth_t_minus_1"]   = 0.0
            df["acceleration_raw"]   = 0.0
            df["acceleration_score"] = 0.0
            return df

        prev1 = previous_df[["ward_code", "allocated_kwh"]].rename(
            columns={"allocated_kwh": "allocated_t_minus_1"}
        )
        prev2 = previous_previous_df[["ward_code", "allocated_kwh"]].rename(
            columns={"allocated_kwh": "allocated_t_minus_2"}
        )

        df = df.merge(prev1, on="ward_code", how="left")
        df = df.merge(prev2, on="ward_code", how="left")

        df["growth_t"] = (
            (df["allocated_kwh"] - df["allocated_t_minus_1"])
            / df["allocated_t_minus_1"]
        )
        df["growth_t_minus_1"] = (
            (df["allocated_t_minus_1"] - df["allocated_t_minus_2"])
            / df["allocated_t_minus_2"]
        )
        df["acceleration_raw"] = df["growth_t"] - df["growth_t_minus_1"]
        df["acceleration_raw"] = (
            df["acceleration_raw"]
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
            .clip(-0.1, 0.1)
        )
        df["acceleration_score"] = self._minmax(df["acceleration_raw"])

        return df

    def _calculate_sector_shift_score(
        self,
        df           : pd.DataFrame,
        current_share: dict,
        base_share   : dict,
    ):
        df = df.copy()

        df["sector_shift_raw"] = (
            abs(current_share["residential"] - base_share["residential"]) * df["weight_res"]
            + abs(current_share["commercial"] - base_share["commercial"]) * df["weight_com"]
            + abs(current_share["industrial"] - base_share["industrial"]) * df["weight_ind"]
        )
        df["sector_shift_score"] = self._minmax(df["sector_shift_raw"])

        return df

    def _calculate_priority_score(self, df: pd.DataFrame):
        df      = df.copy()
        weights = self.config["PRIORITY_WEIGHTS"]
        df["priority_pre_spatial"] = (
            weights["rank"] * df["rank_score"]
            + weights["absolute"] * df["absolute_score"]
            + weights["acceleration"] * df["acceleration_score"]
            + weights["sector_shift"] * df["sector_shift_score"]
        )
        return df

    def _assign_priority_level(self, df: pd.DataFrame):
        df = df.copy()
        df["priority_level"] = "LOW"
        df.loc[
            df["final_score_raw"] >= self.config["LEVEL_MEDIUM"],
            "priority_level",
        ] = "MEDIUM"
        df.loc[
            df["final_score_raw"] >= self.config["LEVEL_HIGH"],
            "priority_level",
        ] = "HIGH"
        return df

    def _minmax(self, series: pd.Series):
        min_value = series.min()
        max_value = series.max()

        if pd.isna(min_value) or pd.isna(max_value) or max_value == min_value:
            return pd.Series(0.0, index=series.index)

        return (series - min_value) / (max_value - min_value)
