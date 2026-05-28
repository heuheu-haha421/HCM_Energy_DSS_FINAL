from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
DB_PATH = BACKEND_DIR / "energy_dss.db"

TARGET_YEAR = 2026
TARGET_WEEK = "12/2026"
TARGET_WARD_CODE = "HCM078_AK"
TARGET_WARD_NAME = "Ward An Khanh"

REFERENCE_API_ALLOCATED_KWH = 17_785_314.752
REFERENCE_API_SCORES = {
    "rank_score": 0.994,
    "absolute_score": 0.9939,
    "acceleration_score": 0.8738,
    "final_score_raw": 0.8214,
    "final_score_ranked": 0.9655,
    "priority_level": "MEDIUM",
}

sys.path.insert(0, str(BACKEND_DIR))

from app.api.services.simulation_services import SimulationService  # noqa: E402
from app.models.database import Database  # noqa: E402


def as_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def format_value(value: Any, digits: int = 6) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return "N/A"
        if abs(float(value)) >= 1000:
            return f"{float(value):,.3f}"
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def get_prediction_for_week(db: Database, week: str) -> dict[str, Any]:
    row = db.fetch_one(
        """
        SELECT p.*, w.week, w.start_date, w.end_date
        FROM predictions p
        JOIN weeks w ON w.id = p.week_id
        WHERE w.week = ?
        ORDER BY p.created_at DESC, p.id DESC
        LIMIT 1
        """,
        (week,),
    )
    if not row:
        raise RuntimeError(f"No prediction record found for week {week}")
    return as_dict(row)


def get_city_totals(db: Database, year: int) -> dict[str, float]:
    row = db.fetch_one(
        """
        SELECT
            SUM(population) AS total_population,
            SUM(enterprises) AS total_enterprises,
            SUM(school_classes) AS total_school_classes,
            SUM(hospital_beds) AS total_hospital_beds
        FROM ward_infra
        WHERE data_year = ?
        """,
        (year,),
    )
    return as_dict(row)


def calculate_for_prediction(
    service: SimulationService,
    year: int,
    prediction: dict[str, Any],
) -> dict[str, Any]:
    allocation_engine = service.allocation_engine
    historical_engine = service.historical_reconstruction_engine

    total_load = allocation_engine._get_total_load(prediction)
    avg_temp = historical_engine._get_avg_temp(prediction["week_id"])
    weather_signal = allocation_engine._compute_weather_signal(avg_temp)
    week_context = historical_engine._get_week_context(
        prediction.get("start_date"),
        prediction.get("end_date"),
    )

    ward_df = allocation_engine._get_ward_proxy_weights(year)
    base_share = allocation_engine._get_base_share(ward_df)
    adjusted_share, sector_loads = allocation_engine._decompose_dynamic_load(
        total_load=total_load,
        weather_signal=weather_signal,
        week_context=week_context,
        base_share=base_share,
    )
    allocated_df = allocation_engine._calculate_allocated_kwh(ward_df, sector_loads)
    allocated_df["neighbors"] = allocated_df["ward_code"].map(
        service.spatial_engine._load_geojson_neighbors(allocated_df)
    )

    previous_df, previous_previous_df = historical_engine._get_previous_allocated_dfs(
        year,
        prediction,
    )
    stress_df = service._calculate_stress_scores(
        allocated_df,
        previous_df,
        previous_previous_df,
        adjusted_share,
        base_share,
    )
    stress_df = stress_df.sort_values(by="final_score_raw", ascending=False)

    return {
        "total_load": total_load,
        "avg_temp": avg_temp,
        "weather_signal": weather_signal,
        "week_context": week_context,
        "ward_df": ward_df,
        "base_share": base_share,
        "adjusted_share": adjusted_share,
        "sector_loads": sector_loads,
        "allocated_df": allocated_df,
        "stress_df": stress_df,
    }


def row_for_ward(df: pd.DataFrame, ward_code: str) -> dict[str, Any]:
    matched = df[df["ward_code"] == ward_code]
    if matched.empty:
        raise RuntimeError(f"Ward {ward_code} not found in calculation dataframe")
    return matched.iloc[0].to_dict()


def main() -> None:
    db = Database(DB_PATH)
    db.connect()
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA query_only = ON")

    try:
        service = SimulationService(db)

        prediction = get_prediction_for_week(db, TARGET_WEEK)
        target = calculate_for_prediction(service, TARGET_YEAR, prediction)
        ward_proxy = row_for_ward(target["ward_df"], TARGET_WARD_CODE)
        ward_allocated = row_for_ward(target["allocated_df"], TARGET_WARD_CODE)
        ward_stress = row_for_ward(target["stress_df"], TARGET_WARD_CODE)
        city_totals = get_city_totals(db, TARGET_YEAR)

        current_endpoint_result = service.calculate_grid_stress_priorities(TARGET_YEAR)
        current_endpoint_rows = current_endpoint_result["results"]
        current_endpoint_ward = next(
            (row for row in current_endpoint_rows if row.get("ward_code") == TARGET_WARD_CODE),
            None,
        )

        target_api_like_rows = service._records_for_response(target["stress_df"])
        target_api_like_ward = next(
            (row for row in target_api_like_rows if row.get("ward_code") == TARGET_WARD_CODE),
            None,
        )

        contributions = {
            "industrial_contribution": ward_proxy["weight_ind"] * target["sector_loads"]["industrial"],
            "residential_contribution": ward_proxy["weight_res"] * target["sector_loads"]["residential"],
            "commercial_contribution": ward_proxy["weight_com"] * target["sector_loads"]["commercial"],
            "services_contribution": ward_proxy["weight_ser"] * target["sector_loads"]["services"],
        }
        calculated_allocated_kwh = sum(contributions.values())
        target_api_allocated_kwh = (
            target_api_like_ward.get("allocated_kwh")
            if target_api_like_ward
            else None
        )
        current_api_allocated_kwh = (
            current_endpoint_ward.get("allocated_kwh")
            if current_endpoint_ward
            else None
        )

        print("# Dynamic Ward Allocation Debug")
        print()
        print(
            "Read-only script. It uses backend AllocationEngine/SimulationService methods and "
            "does not read from the removed ward_allocation table."
        )
        print()

        print("## 1. Week Context")
        print(markdown_table(
            ["Field", "Value"],
            [
                ["target_year", TARGET_YEAR],
                ["target_week", prediction.get("week")],
                ["start_date", prediction.get("start_date")],
                ["end_date", prediction.get("end_date")],
                ["total_load", format_value(target["total_load"], 3)],
                ["avg_temp", format_value(target["avg_temp"], 3)],
                ["weather_signal", format_value(target["weather_signal"], 6)],
                ["is_holiday", format_value(target["week_context"].get("is_holiday"))],
            ],
        ))
        print()

        print("## 2. Dynamic Sector Decomposition")
        sector_rows = []
        for sector in ("industrial", "residential", "commercial", "services"):
            sector_rows.append([
                sector,
                format_value(target["base_share"].get(sector), 6),
                format_value(target["adjusted_share"].get(sector), 6),
            ])
        print(markdown_table(
            ["Sector", "Base Share", "Adjusted Share"],
            sector_rows,
        ))
        print()

        print("## 3. Sector Loads")
        print(markdown_table(
            ["Sector", "Load (kWh)"],
            [
                [sector, format_value(value, 3)]
                for sector, value in target["sector_loads"].items()
            ],
        ))
        print()

        print("## 4. Ward An Khanh Infrastructure Values")
        print(markdown_table(
            ["Field", "Value"],
            [
                ["ward_code", ward_proxy.get("ward_code")],
                ["ward_name", ward_proxy.get("ward_name", TARGET_WARD_NAME)],
                ["population", format_value(ward_proxy.get("population"), 3)],
                ["enterprises", format_value(ward_proxy.get("enterprises"), 3)],
                ["school_classes", format_value(ward_proxy.get("school_classes"), 3)],
                ["hospital_beds", format_value(ward_proxy.get("hospital_beds"), 3)],
            ],
        ))
        print()

        print("## 5. City Totals For Normalization")
        print(markdown_table(
            ["Field", "Value"],
            [
                ["total_population", format_value(city_totals.get("total_population"), 3)],
                ["total_enterprises", format_value(city_totals.get("total_enterprises"), 3)],
                ["total_school_classes", format_value(city_totals.get("total_school_classes"), 3)],
                ["total_hospital_beds", format_value(city_totals.get("total_hospital_beds"), 3)],
            ],
        ))
        print()

        print("## 6. Ward An Khanh Proxy Weights")
        print(markdown_table(
            ["Weight", "Formula", "Value"],
            [
                ["weight_ind", "enterprises_AK / total_enterprises", format_value(ward_proxy.get("weight_ind"), 9)],
                ["weight_res", "population_AK / total_population", format_value(ward_proxy.get("weight_res"), 9)],
                ["weight_com", "school_classes_AK / total_school_classes", format_value(ward_proxy.get("weight_com"), 9)],
                ["weight_ser", "hospital_beds_AK / total_hospital_beds", format_value(ward_proxy.get("weight_ser"), 9)],
            ],
        ))
        print()

        print("## 7. Sector Contribution Breakdown")
        print(markdown_table(
            ["Contribution", "Formula", "Value (kWh)"],
            [
                ["industrial_contribution", "weight_ind * industrial_load", format_value(contributions["industrial_contribution"], 3)],
                ["residential_contribution", "weight_res * residential_load", format_value(contributions["residential_contribution"], 3)],
                ["commercial_contribution", "weight_com * commercial_load", format_value(contributions["commercial_contribution"], 3)],
                ["services_contribution", "weight_ser * services_load", format_value(contributions["services_contribution"], 3)],
                ["allocated_kwh", "sum of four contributions", format_value(calculated_allocated_kwh, 3)],
            ],
        ))
        print()

        print("## 8. Compare With API-Compatible Output")
        comparison_rows = [
            [
                "User-provided API reference",
                format_value(REFERENCE_API_ALLOCATED_KWH, 3),
                format_value(calculated_allocated_kwh, 3),
                format_value(REFERENCE_API_ALLOCATED_KWH - calculated_allocated_kwh, 6),
            ],
            [
                f"Target week {TARGET_WEEK}, service response formatter",
                format_value(target_api_allocated_kwh, 3),
                format_value(calculated_allocated_kwh, 3),
                format_value(
                    None if target_api_allocated_kwh is None else target_api_allocated_kwh - calculated_allocated_kwh,
                    6,
                ),
            ],
            [
                f"Current endpoint context week {current_endpoint_result.get('week')}",
                format_value(current_api_allocated_kwh, 3),
                format_value(calculated_allocated_kwh, 3),
                format_value(
                    None if current_api_allocated_kwh is None else current_api_allocated_kwh - calculated_allocated_kwh,
                    6,
                ),
            ],
        ]
        print(markdown_table(
            ["Source", "API allocated_kwh", "Calculated allocated_kwh", "Difference"],
            comparison_rows,
        ))
        print()
        if current_endpoint_result.get("week") != TARGET_WEEK:
            print(
                f"> Note: the live endpoint has no week query parameter. In this database its current "
                f"context is week {current_endpoint_result.get('week')}, while this script targets "
                f"{TARGET_WEEK}. A difference is expected when latest prediction week, temperature, "
                "holiday context, or active scenario differ."
            )
            print()
        if abs(REFERENCE_API_ALLOCATED_KWH - calculated_allocated_kwh) > 1:
            print(
                "> Reference mismatch note: the user-provided reference does not exactly match the "
                "current local database/service calculation for Week 12/2026. This usually means one "
                "of these inputs changed after the reference was captured: latest prediction record, "
                "weather_weekly.temp, active scenario weights, holiday rows, or ward_infra values."
            )
            print()

        print("## 9. Stress Score Outputs")
        stress_fields = [
            "rank_score",
            "absolute_score",
            "acceleration_score",
            "sector_shift_score",
            "spatial_score",
            "priority_pre_spatial",
            "final_score_raw",
            "final_score_ranked",
            "priority_level",
            "stress_factors",
            "primary_reason",
        ]
        print(markdown_table(
            ["Field", "Value"],
            [
                [field, format_value(ward_stress.get(field), 6)]
                for field in stress_fields
            ],
        ))
        print()

        print("## 10. User-Provided Reference Stress Scores")
        print(markdown_table(
            ["Field", "Reference", "Calculated"],
            [
                [field, format_value(reference, 6), format_value(ward_stress.get(field), 6)]
                for field, reference in REFERENCE_API_SCORES.items()
            ],
        ))
        print()

        print("## 11. Source Trace")
        print(markdown_table(
            ["Item", "Value"],
            [
                ["database", DB_PATH],
                ["target ward", f"{TARGET_WARD_CODE} / {TARGET_WARD_NAME}"],
                ["calculation service", "backend/app/api/services/simulation_services.py"],
                ["allocation engine", "backend/app/api/engines/allocation_engine.py"],
                ["stress engine", "backend/app/api/engines/stress_score_engine.py"],
                ["spatial engine", "backend/app/api/engines/spatial_engine.py"],
                ["ward_allocation table used", "No"],
            ],
        ))
    finally:
        db.close()


if __name__ == "__main__":
    main()
