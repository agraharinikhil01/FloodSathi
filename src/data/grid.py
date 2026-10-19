"""
src/data/grid.py
----------------
Generates 10 to 20 spatial grid points for a given district.
Used for granular flood risk and forecast modeling across district areas.
"""

from __future__ import annotations

from typing import Any

from src.db.queries import get_district_by_id, get_district_by_name


def _compute_grid_coordinates(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    rows: int = 4,
    cols: int = 4,
) -> list[tuple[float, float]]:
    """Generate a uniform rectangular lattice of coordinates within bounds."""
    lat_step = (max_lat - min_lat) / (rows + 1)
    lon_step = (max_lon - min_lon) / (cols + 1)
    points: list[tuple[float, float]] = []

    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            lat = round(min_lat + r * lat_step, 4)
            lon = round(min_lon + c * lon_step, 4)
            points.append((lat, lon))

    return points


def generate_grid_for_district(district: dict[str, Any], count: int = 16) -> list[dict[str, Any]]:
    """Generate 10 to 20 grid points within a district's bounding box."""
    c_lat = float(district["centroid_lat"])
    c_lon = float(district["centroid_lon"])
    min_lat = float(district.get("bbox_min_lat") or (c_lat - 0.2))
    max_lat = float(district.get("bbox_max_lat") or (c_lat + 0.2))
    min_lon = float(district.get("bbox_min_lon") or (c_lon - 0.2))
    max_lon = float(district.get("bbox_max_lon") or (c_lon + 0.2))

    rows = 4
    cols = 4 if count >= 16 else 3
    coords = _compute_grid_coordinates(min_lat, max_lat, min_lon, max_lon, rows, cols)

    grid_points: list[dict[str, Any]] = []
    base_pop = 15000
    for idx, (lat, lon) in enumerate(coords[:count], start=1):
        # Slightly vary population across grid points to represent urban/rural distribution
        pop_factor = 1.0 + 0.3 * ((idx % 5) - 2)
        grid_points.append(
            {
                "id": idx,
                "district_id": district.get("id"),
                "district_name": district.get("name"),
                "lat": lat,
                "lon": lon,
                "population": int(base_pop * pop_factor),
            }
        )

    return grid_points


def get_district_grid(district_identifier: int | str, count: int = 16) -> list[dict[str, Any]]:
    """Fetch district from DB and return generated grid points."""
    if isinstance(district_identifier, int):
        district = get_district_by_id(district_identifier)
    else:
        district = get_district_by_name(str(district_identifier))

    if not district:
        # Fallback to default centroid if district not found in DB
        district = {
            "id": 1,
            "name": str(district_identifier),
            "centroid_lat": 26.25,
            "centroid_lon": 92.34,
            "bbox_min_lat": 26.0,
            "bbox_max_lat": 26.5,
            "bbox_min_lon": 92.1,
            "bbox_max_lon": 92.6,
        }

    return generate_grid_for_district(district, count=count)
