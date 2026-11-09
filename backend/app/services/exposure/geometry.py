import json
from typing import Dict, Any, Tuple
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, Point
from shapely.validation import make_valid
from shapely.ops import unary_union

class GeometryService:
    @staticmethod
    def validate_and_normalize(geojson_dict: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """
        Validates GeoJSON dictionary.
        Returns (shapely_geom, normalized_geojson)
        """
        if "type" not in geojson_dict or geojson_dict["type"] not in ["Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]:
            raise ValueError(f"Unsupported geometry type: {geojson_dict.get('type')}")
        
        geom = shape(geojson_dict)
        if not geom.is_valid:
            geom = make_valid(geom)
            
        valid_types = ["Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]
        if geom.geom_type not in valid_types:
            raise ValueError(f"Geometry became {geom.geom_type} after validation")
            
        return geom, mapping(geom)

    @staticmethod
    def get_bbox(geom) -> Tuple[float, float, float, float]:
        """Returns (min_lon, min_lat, max_lon, max_lat)"""
        return geom.bounds

    @staticmethod
    def calculate_area_km2(geom) -> float:
        """
        Rough area calculation for WGS84 bounding box / polygon in km^2.
        For exact, we'd project. But for max area limiting, a rough calculation is fine.
        Let's use a very simple approximation based on centroid latitude.
        1 degree lat = ~111 km. 1 degree lon = ~111 * cos(lat) km.
        """
        import math
        centroid = geom.centroid
        cos_lat = math.cos(math.radians(centroid.y))
        
        # Area in sq degrees * (111 km/deg)^2 * cos(lat)
        area_sq_deg = geom.area
        return area_sq_deg * 111.0 * 111.0 * cos_lat

    @staticmethod
    def intersects(geom, pt_lon: float, pt_lat: float) -> bool:
        """Check if point intersects geometry"""
        pt = Point(pt_lon, pt_lat)
        return geom.intersects(pt)

    @staticmethod
    def create_buffer(geom, buffer_km: float) -> Any:
        """
        Create a buffer in degrees (approximate).
        """
        import math
        centroid = geom.centroid
        deg_per_km = 1.0 / 111.0
        
        # Expand buffer based on latitude
        lon_scale = 1.0 / math.cos(math.radians(centroid.y))
        
        # Simple buffer in degrees (not perfectly round, but works for bounding analysis)
        buffer_deg = buffer_km * deg_per_km
        # We can just buffer in degrees. 
        # For a truly accurate buffer, we should use pyproj, but Shapely buffer in WGS84 is acceptable here
        # for a rough analysis if we use an average degree scale.
        return geom.buffer(buffer_deg)
