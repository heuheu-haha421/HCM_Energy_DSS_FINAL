import pandas as pd
import numpy as np
import json
import unicodedata

from typing import Callable
from app.api.config.grid_stress_config import CONFIG, GEOJSON_PATH
from app.errors import InvalidInputError

class SpatialEngine:
    def __init__(self, predictor):
        self.predictor    = predictor
        self.config       = CONFIG
        self.geojson_path = GEOJSON_PATH
        
    def _load_geojson_neighbors(self, ward_df: pd.DataFrame):
        if not self.geojson_path.exists():
            return {}
        
        with self.geojson_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        geojson_id_to_ward_code = self._map_geojson_ids_to_ward_codes(
            data,
            ward_df,
        )
        boundary_points = {}

        for feature in data.get("features", []):
            props      = feature.get("properties", {})
            geojson_id = str(props.get("id", ""))
            ward_code  = geojson_id_to_ward_code.get(geojson_id)

            if not ward_code:
                continue

            for point in self._geometry_points(feature.get("geometry", {})):
                boundary_points.setdefault(point, set()).add(ward_code)

        neighbors = {}

        for codes in boundary_points.values():
            if len(codes) < 2:
                continue

            for code in codes:
                neighbors.setdefault(code, set()).update(c for c in codes if c != code)

        return {
            code: sorted(values)
            for code, values in neighbors.items()
        }
    
    def _map_geojson_ids_to_ward_codes(self, geojson_data: dict, ward_df: pd.DataFrame):
        wards_by_name = {
            self._normalize_ward_name(row["ward_name"]): row["ward_code"]
            for row in ward_df[["ward_code", "ward_name"]].to_dict(orient="records")
        }

        mapping = {}

        for feature in geojson_data.get("features", []):
            props        = feature.get("properties", {})
            geojson_id   = str(props.get("id", ""))
            geojson_name = props.get("name")

            if not geojson_id or not geojson_name:
                continue

            ward_code = wards_by_name.get(self._normalize_ward_name(geojson_name))

            if ward_code:
                mapping[geojson_id] = ward_code

        return mapping

    def _geometry_points(self, geometry: dict):
        geometry_type = geometry.get("type")
        coordinates   = geometry.get("coordinates", [])

        if geometry_type == "Polygon":
            polygons = [coordinates]
        elif geometry_type == "MultiPolygon":
            polygons = [ring_set for ring_set in coordinates]
        else:
            polygons = []

        for polygon in polygons:
            for ring in polygon:
                for lng, lat in ring:
                    yield (round(float(lng), 6), round(float(lat), 6))

    def _apply_spatial_smoothing(self, df: pd.DataFrame, minmax: Callable):
        df = df.copy()
        lambda_spatial = self.config["LAMBDA_SPATIAL"]

        if lambda_spatial < 0 or lambda_spatial > 1:
            raise InvalidInputError("LAMBDA_SPATIAL must be between 0 and 1")

        score_dict = df.set_index("ward_code")["priority_pre_spatial"].to_dict()

        def get_neighbor_mean(neighbor_value):
            neighbors    = neighbor_value if isinstance(neighbor_value, list) else []
            valid_scores = [
                score_dict[code]
                for code in neighbors
                if code in score_dict
            ]

            if not valid_scores:
                return 0.0

            return float(np.mean(valid_scores))

        df["spatial_score"]   = df["neighbors"].apply(get_neighbor_mean)
        df["final_score_raw"] = (
            (1 - lambda_spatial) * df["priority_pre_spatial"]
            + lambda_spatial * df["spatial_score"]
        )
        df["final_score_ranked"] = minmax(df["final_score_raw"])

        df["allocated_kwh"]        = df["allocated_kwh"].round(3)
        df["final_score_raw"]      = df["final_score_raw"].round(4)
        df["final_score_ranked"]   = df["final_score_ranked"].round(4)
        df["rank_score"]           = df["rank_score"].round(4)
        df["absolute_score"]       = df["absolute_score"].round(4)
        df["acceleration_score"]   = df["acceleration_score"].round(4)

        return df

    def _normalize_ward_name(self, value: str):
        normalized = value.strip().lower()

        for prefix in (
            "special zone ",
            "commune ",
            "ward ",
            "town ",
            "phường ",
            "xã ",
            "thị trấn ",
            "đặc khu ",
        ):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break

        normalized = normalized.replace("đ", "d")
        normalized = "".join(
            char
            for char in unicodedata.normalize("NFD", normalized)
            if unicodedata.category(char) != "Mn"
        )

        return " ".join(normalized.split())
