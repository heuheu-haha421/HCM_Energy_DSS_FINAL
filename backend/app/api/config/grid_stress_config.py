from pathlib import Path

GRID_STRESS_METHOD = "proxy_based_weekly_grid_stress_priority"

GEOJSON_PATH       = Path(__file__).resolve().parents[2] / "api" / "static" / "hcm_wards.geojson"

CONFIG             = {
    "BASE_TEMP": 26.0,
    "MAX_TEMP" : 35.0,
    "WEATHER_ADJUSTMENT": {
        "industrial" : -0.11,
        "residential": 0.08,
        "commercial" : 0.03,
        "services"   : 0.00,
    },
    "HOLIDAY_ADJUSTMENT": {
        "industrial" : -0.15,
        "residential": 0.20,
        "commercial" : -0.05,
        "services"   : 0.00,
    },
    "PRIORITY_WEIGHTS": {
        "rank"        : 0.20,
        "absolute"    : 0.15,
        "acceleration": 0.40,
        "sector_shift": 0.15,
    },
    "LAMBDA_SPATIAL": 0.15,
    "LEVEL_MEDIUM"  : 0.65,
    "LEVEL_HIGH"    : 0.85,
}

SECTOR_COLUMNS = {
    "industrial": {
        "weight"       : "weight_ind",
        "source"       : "enterprises",
        "share_aliases": ("share_industrial", "base_share_industrial", "industrial_share"),
    },
    "residential": {
        "weight"       : "weight_res",
        "source"       : "population",
        "share_aliases": ("share_residential", "base_share_residential", "residential_share"),
    },
    "commercial": {
        "weight"       : "weight_com",
        "source"       : "school_classes",
        "share_aliases": ("share_commercial", "base_share_commercial", "commercial_share"),
    },
    "services": {
        "weight"       : "weight_ser",
        "source"       : "hospital_beds",
        "share_aliases": ("share_services", "base_share_services", "services_share"),
    },
}
