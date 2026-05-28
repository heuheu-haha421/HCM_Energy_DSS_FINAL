import pandas as pd


class PreprocessData:
    CUTOFF_DATE       = pd.Timestamp("2025-07-01")
    TOTAL_LOAD_COLUMN = "total_load (kWh)"

    def __init__(self, total_load: pd.DataFrame, weather: pd.DataFrame, holiday: pd.DataFrame, structual_shift: float = 1.87):
        self.total_load      = total_load.copy()
        self.weather         = weather.copy()
        self.holiday         = holiday.copy()
        self.structual_shift = structual_shift
        self.delta_holiday   = 0.1830
        self.delta_pre       = -0.1289
        self.delta_post      = 0.0944

    # -------------------------
    # TOTAL LOAD
    # -------------------------
    def process_total_load(self):
        df                = self.total_load.copy()
        df["holiday"]     = 0.0
        df["tet_holiday"] = 0.0
        return df.reset_index(drop=True)

    # -------------------------
    # HOLIDAY GRAVITY
    # -------------------------
    def calc_holiday_gravity(self, df):
        df = df.copy()

        df["start_date"]      = pd.to_datetime(df["start_date"])
        df["end_date"]        = pd.to_datetime(df["end_date"])
        self.holiday["start"] = pd.to_datetime(self.holiday["start"])
        self.holiday["end"]   = pd.to_datetime(self.holiday["end"])

        indicases, dates = [], []

        for i, row in df.iterrows():
            week_start = pd.Timestamp(row["start_date"])
            week_end   = pd.Timestamp(row["end_date"]) - pd.Timedelta(days=1)

            total_days = 0

            for h in self.holiday.itertuples():
                holiday_start = pd.Timestamp(h.start)
                holiday_end   = pd.Timestamp(h.end)
                overlap_start = max(week_start, holiday_start)
                overlap_end   = min(week_end, holiday_end)

                if overlap_start <= overlap_end:
                    days = (overlap_end - overlap_start).days + 1
                    total_days += days

                    if h.type == "Tet Holiday":
                        indicases.append(i)
                        dates.append([holiday_start, holiday_end])
                        df.at[i, "tet_holiday"] = 1

            df.at[i, "holiday"] = round(total_days / 6, 1)

        return df, indicases, dates
    
    def calc_sunday_monday_gravity(self, df, indicases, dates):
        df = df.copy()

        tmp_df = pd.DataFrame({
            "idx"  : indicases,
            "start": [d[0] for d in dates],
            "end"  : [d[1] for d in dates]
        })

        tmp_df['prev_date'] = pd.to_datetime(tmp_df['start']) -  pd.Timedelta(days=7)
        tmp_df['post_date'] = pd.to_datetime(tmp_df['end']) +  pd.Timedelta(days=7)

        tmp_df['days_to_sunday']    = round((6 - tmp_df['prev_date'].dt.weekday) / 6, 1)
        tmp_df['days_since_monday'] = round((tmp_df['post_date'].dt.weekday) / 6, 1)

        return tmp_df
        

    # -------------------------
    # TET GRAVITY
    # -------------------------
    def calc_tet_gravity(self, df, indicases, dates):
        df = df.copy()

        tmp_df = self.calc_sunday_monday_gravity(df, indicases, dates)

        df["pre_tet_gravity"]  = 0.0
        df["post_tet_gravity"] = 0.0

        for _, group in tmp_df.groupby(["start", "end"], sort=False):
            first_overlap_idx = int(group["idx"].min())
            last_overlap_idx  = int(group["idx"].max())

            pre_idx  = first_overlap_idx - 1
            post_idx = last_overlap_idx + 1

            row = group.iloc[0]

            if pre_idx in df.index:
                df.at[pre_idx, "pre_tet_gravity"] = row["days_to_sunday"]

            if post_idx in df.index:
                df.at[post_idx, "post_tet_gravity"] = row["days_since_monday"]
        
        return df

    def get_load_shift_factor(self, df):
        factor    = pd.Series(1.0, index=df.index)
        end_dates = pd.to_datetime(df["end_date"])
        mask_old  = end_dates < self.CUTOFF_DATE

        holiday_mask  = mask_old & (df["holiday"] > 0)
        pre_tet_mask  = mask_old & (df["pre_tet_gravity"] > 0)
        post_tet_mask = mask_old & (df["post_tet_gravity"] > 0)

        factor.loc[holiday_mask] *= (
            1 - (self.delta_holiday * df.loc[holiday_mask, "holiday"])
        )
        factor.loc[pre_tet_mask] *= (
            1 - (self.delta_pre * df.loc[pre_tet_mask, "pre_tet_gravity"])
        )
        factor.loc[post_tet_mask] *= (
            1 - (self.delta_post * df.loc[post_tet_mask, "post_tet_gravity"])
        )
        factor.loc[mask_old] *= self.structual_shift

        return factor

    def decode_prediction(self, prediction, start_date, end_date):
        end_date = pd.to_datetime(end_date)

        if end_date >= self.CUTOFF_DATE:
            return int(round(prediction))

        context = self.get_adjustment_context(start_date, end_date)
        factor  = self.get_prediction_shift_factor(
            context["holiday"],
            context["pre_tet_gravity"],
            context["post_tet_gravity"],
        )

        if factor == 0:
            return int(round(prediction))

        return int(round(prediction / factor))

    def get_prediction_shift_factor(self, holiday, pre_tet_gravity, post_tet_gravity):
        factor = 1.0

        if holiday > 0:
            factor *= 1 - (self.delta_holiday * holiday)

        if pre_tet_gravity > 0:
            factor *= 1 - (self.delta_pre * pre_tet_gravity)

        if post_tet_gravity > 0:
            factor *= 1 - (self.delta_post * post_tet_gravity)

        return factor * self.structual_shift

    def get_adjustment_context(self, start_date, end_date):
        start_date = pd.to_datetime(start_date)
        end_date   = pd.to_datetime(end_date)

        self.holiday["start"] = pd.to_datetime(self.holiday["start"])
        self.holiday["end"]   = pd.to_datetime(self.holiday["end"])

        return {
            "holiday"         : self._get_holiday_gravity(start_date, end_date),
            "pre_tet_gravity" : self._get_pre_tet_gravity(start_date, end_date),
            "post_tet_gravity": self._get_post_tet_gravity(start_date, end_date),
        }

    def _get_holiday_gravity(self, start_date, end_date):
        start_date = pd.Timestamp(start_date)
        end_date   = pd.Timestamp(end_date)
        week_end   = end_date - pd.Timedelta(days=1)
        total_days = 0

        for holiday in self.holiday.itertuples():
            holiday_start = pd.Timestamp(holiday.start)
            holiday_end   = pd.Timestamp(holiday.end)
            overlap_start = max(start_date, holiday_start)
            overlap_end   = min(week_end, holiday_end)

            if overlap_start <= overlap_end:
                total_days += (overlap_end - overlap_start).days + 1

        return round(total_days / 6, 1)

    def _get_pre_tet_gravity(self, start_date, end_date):
        next_start = start_date + pd.Timedelta(days=7)
        next_end   = end_date + pd.Timedelta(days=7)
        return int(self._has_tet_overlap(next_start, next_end))

    def _get_post_tet_gravity(self, start_date, end_date):
        previous_start = start_date - pd.Timedelta(days=7)
        previous_end   = end_date - pd.Timedelta(days=7)
        return int(self._has_tet_overlap(previous_start, previous_end))

    def _has_tet_overlap(self, start_date, end_date):
        start_date = pd.Timestamp(start_date)
        end_date   = pd.Timestamp(end_date)
        week_end   = end_date - pd.Timedelta(days=1)

        for holiday in self.holiday.itertuples():
            if holiday.type != "Tet Holiday":
                continue

            holiday_start = pd.Timestamp(holiday.start)
            holiday_end   = pd.Timestamp(holiday.end)
            overlap_start = max(start_date, holiday_start)
            overlap_end   = min(week_end, holiday_end)

            if overlap_start <= overlap_end:
                return True

        return False

    # -------------------------
    # WEEK SPLIT
    # -------------------------
    def split_week(self, df):
        df = df.copy()

        df[["week_num", "year"]] = df["week"].str.split("/", expand=True)

        df["week_num"] = pd.to_numeric(df["week_num"], errors="coerce")
        df["year"]     = pd.to_numeric(df["year"], errors="coerce")

        return df

    # -------------------------
    # CLEAN COLUMNS
    # -------------------------
    def remove_cols(self, df):
        df = df.copy()

        drop_cols = [
            "week", "start_date", "end_date",
            "Pmax (MW)", "Pmin (MW)",
            "tet_holiday", "total_load (kWh)"
        ]

        df = df.drop(columns=drop_cols, errors="ignore")

        ordered = [
            "week_num", "year",
            "temp", "tmin", "tmax", "rhum", "prcp", "wspd", "pres",
            "holiday", "pre_tet_gravity", "post_tet_gravity"
        ]

        cols = ordered + [c for c in df.columns if c not in ordered]

        return df[cols]

    def preprocess_for_prediction(self, target_week, target_start_date, target_end_date):
        df = self.process_total_load()

        target_row                         = df.iloc[-1:].copy()
        target_row["week"]                 = target_week
        target_row["start_date"]           = target_start_date
        target_row["end_date"]             = target_end_date
        target_row["Pmax (MW)"]            = None
        target_row["Pmin (MW)"]            = None
        target_row[self.TOTAL_LOAD_COLUMN] = None

        df = pd.concat([df, target_row], ignore_index=True)

        df, indicases, dates = self.calc_holiday_gravity(df)
        df = self.calc_tet_gravity(df, indicases, dates)

        factor = self.get_load_shift_factor(df)
        load   = pd.to_numeric(df[self.TOTAL_LOAD_COLUMN], errors="coerce") * factor

        df["load_lag_1"] = load.shift(1)
        df["load_lag_2"] = load.shift(2)
        df["load_lag_3"] = load.shift(3)

        df = df.iloc[[-1]].reset_index(drop=True)
        df = pd.concat([df, self.weather.reset_index(drop=True)], axis=1)

        df = self.split_week(df)
        df = self.remove_cols(df)

        return df.reset_index(drop=True).dropna()
