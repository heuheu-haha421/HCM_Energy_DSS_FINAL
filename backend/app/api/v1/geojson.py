from fastapi import APIRouter
from fastapi.responses import FileResponse

class GeoJsonController:
    def __init__(self):
        self.router = APIRouter(
            prefix = "/api/v1/geojson",
            tags   = ["GeoJSON"]
        )

        self.router.add_api_route("/wards", self.get_wards_geojson, methods=["GET"])
        
    def get_wards_geojson(self):
        return FileResponse(
            path       = "app/api/static/hcm_wards.geojson",
            media_type = "application/geo+json",
            filename   = "hcm_wards.geojson"
        )