from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd


@dataclass
class PredictionConfig:
    vn_timezone                 : str = "Asia/Ho_Chi_Minh"
    location                    : str = "48900"
    sleep_seconds               : int = 10
    duplicate_week_sleep_seconds: int = 5
    min_energy_rows             : int = 3
    max_weekly_predictions      : int = 10


@dataclass
class PredictionState:
    first_run      : bool = True
    is_data_updated: bool = True

    week           : Optional[str] = None
    start_date     : Optional[Any] = None
    end_date       : Optional[Any] = None
    last_start_date: Optional[Any] = None

    model_info: Optional[pd.Series] = None


@dataclass
class RuntimeSnapshot:
    is_first  : bool
    is_updated: bool
    week      : Optional[str]
    start_date: Optional[Any]
    end_date  : Optional[Any]
