import io
from datetime import timedelta

import pandas as pd

from app.errors import InvalidInputError
from app.models import (
    EnergyWeeklyModel,
    HolidayModel,
    WardInfraModel,
    WardModel,
    WeatherWeeklyModel,
    WeekModel,
    ModelRunModel,
)
from app.utilities import DebugMixin


class DataManagementService(DebugMixin):
    def __init__(self, db):
        self.db = db

    async def upload_energy(self, file):
        required_cols = {
            "week", 
            "start_date", 
            "end_date", 
            "Pmax (MW)", 
            "Pmin (MW)", 
            "total_load (kWh)"
        }
        df = await self._read_csv_upload(file, required_cols)

        energy_map = []

        for record in df.to_dict(orient="records"):
            week_id = self._ingest_week(
                record["week"],
                record["start_date"],
                record["end_date"]
            )
            energy_map.append({
                "week_id"       : week_id,
                "pmax_mw"       : record.get("Pmax (MW)", None),
                "pmin_mw"       : record.get("Pmin (MW)", None),
                "total_load_kwh": record.get("total_load (kWh)", None),
                "source"        : record.get("source", None)
            })

        result = EnergyWeeklyModel.upsert_many(self.db, energy_map)
        return result["data"]

    async def upload_ward_stats(self, file):
        required_cols = {
            "Ward Code", 
            "Ward Name", 
            "Year", 
            "Average population", 
            "Average enterprises", 
            "Number of hospital beds", 
            "Total classes"
        }
        df = await self._read_csv_upload(file, required_cols)

        ward_map       = []
        ward_infra_map = []

        for record in df.to_dict(orient="records"):
            ward_map.append({
                "ward_code": record.get("Ward Code", None),
                "ward_name": record.get("Ward Name", None),
            })
            ward_infra_map.append({
                "ward_code"     : record.get("Ward Code", None),
                "data_year"     : record.get("Year", None),
                "population"    : record.get("Average population", None),
                "enterprises"   : record.get("Average enterprises", None),
                "hospital_beds" : record.get("Number of hospital beds", None),
                "school_classes": record.get("Total classes", None)
            })

        ward_result = WardModel.insert_many(self.db, ward_map)

        if not ward_result["success"]:
            raise InvalidInputError(ward_result.get("message", "Validation failed"))

        result = WardInfraModel.upsert_many(self.db, ward_infra_map)
        return result["data"]

    def get_status(self):
        energy_count = EnergyWeeklyModel.get_data_length(self.db)
        ward_count   = WardInfraModel.get_data_length(self.db)
        model_count  = ModelRunModel.get_data_length(self.db)

        return {
            "energy_rows": energy_count,
            "ward_rows"  : ward_count,
            "model_rows" : model_count,
            "status"     : "ok"
        }

    async def upload_holidays(self, file):
        required_cols = {"start", "end", "type"}
        df            = await self._read_csv_upload(file, required_cols)

        rows = [
            {
                "start": record.get("start"),
                "end"  : record.get("end"),
                "type" : record.get("type"),
            }
            for record in df.to_dict(orient="records")
        ]

        result = HolidayModel.upsert_many(self.db, rows)
        return result["data"]

    async def _read_csv_upload(self, file, required_cols: set[str]):
        content = await file.read()

        if not content:
            raise InvalidInputError("Empty file")

        df = pd.read_csv(io.StringIO(content.decode("utf-8")))

        if not required_cols.issubset(df.columns):
            raise InvalidInputError(f"Columns required: {required_cols}")

        return df

    def add_energy(self, payload: dict):
        data = payload.get("data", [])

        week       = data[0].get("week", None) if data else None
        start_date = data[0].get("start_date", None) if data else None
        end_date   = data[0].get("end_date", None) if data else None
        total_load = data[0].get("total_load_kwh", None) if data else None
        pmax       = data[0].get("pmax_mw", None) if data else None
        pmin       = data[0].get("pmin_mw", None) if data else None
        source     = data[0].get("source", None) if data else None

        if not week:
            raise InvalidInputError("Missing week")

        if not start_date or not end_date:
            raise InvalidInputError("Missing start_date or end_date")

        latest_energy = EnergyWeeklyModel.get_latest(self.db)

        if not latest_energy:
            raise InvalidInputError("No energy data available")

        request_start  = WeekModel._normalize_date(start_date)
        expected_start = WeekModel._normalize_date(latest_energy["end_date"]) + timedelta(days=1)

        if request_start != expected_start:
            raise InvalidInputError(
                f"Energy data can only be added for the next week after {latest_energy['week']}"
            )

        week_id         = self._ingest_week(week, start_date, end_date)
        existing_energy = EnergyWeeklyModel.get_by_week_id(self.db, week_id)

        if existing_energy:
            raise InvalidInputError(
                f"Energy data for week already exists: {week}"
            )
        
        res = EnergyWeeklyModel.upsert(
            self.db,
            week_id,
            pmax,
            pmin,
            total_load,
            source
        )
        
        return res["data"]

    def _ingest_week(self, week, start_date, end_date):
        return WeekModel.get_or_create(self.db, week, start_date, end_date)
