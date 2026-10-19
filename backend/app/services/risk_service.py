"""Risk Service orchestrating real-time weather, flood, elevation, alerts and composite risk score."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.integrations.open_meteo import OpenMeteoFloodAdapter, OpenMeteoForecastAdapter
from backend.app.models.schema import (
    Alert,
    District,
    Facility,
    GridPoint,
    RiskScore,
)
from backend.app.risk.engine import score_risk

logger = logging.getLogger(__name__)
settings = get_settings()
forecast_adapter = OpenMeteoForecastAdapter()
flood_adapter = OpenMeteoFloodAdapter()


class RiskService:
    """Service to compute, aggregate, and explain district risk levels."""

    @staticmethod
    def get_district_risk(
        db: Session,
        district_name: str,
        lang: str = "en",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        state: Optional[str] = None,
        district_qualifier: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch district by name or coordinates, compute 5km grid risk, factor breakdown, and official alert overrides.
        If the location is not yet in the local DB, dynamically geocodes and instantiates it on-the-fly for any Indian region!
        """
        district = None

        if lat is not None and lon is not None:
            # First check if an existing district record exists within ~10km of these coordinates
            district = (
                db.query(District)
                .filter(
                    District.centroid_lat.between(lat - 0.1, lat + 0.1),
                    District.centroid_lon.between(lon - 0.1, lon + 0.1),
                )
                .first()
            )

        if not district:
            district = db.query(District).filter(District.name.ilike(district_name)).first()
            # If a district was matched by pure name but exact coordinates were provided and differ by > 20km,
            # this is a different place with the same name across India
            if district and lat is not None and lon is not None:
                if abs(district.centroid_lat - lat) > 0.2 or abs(district.centroid_lon - lon) > 0.2:
                    district = None

        if not district:
            # Dynamic On-Demand Geocoding / Placement for Any Location in India
            from backend.app.integrations.opentopodata import OpenTopoDataAdapter

            if lat is not None and lon is not None:
                c_lat = float(lat)
                c_lon = float(lon)
                clean_name = district_name.strip().title()
                state_name = state.strip() if state else "India"
                if district_qualifier and district_qualifier.lower() not in clean_name.lower():
                    display_label = f"{clean_name} ({district_qualifier})"
                else:
                    display_label = clean_name
            else:
                from backend.app.integrations.nominatim import NominatimAdapter

                nom = NominatimAdapter()
                geo = nom.geocode(f"{district_name}, India")
                if not geo or not geo.get("lat") or not geo.get("lon"):
                    geo = nom.geocode(district_name)

                if not geo or not geo.get("lat") or not geo.get("lon"):
                    return None

                c_lat = float(geo["lat"])
                c_lon = float(geo["lon"])
                display_parts = [p.strip() for p in geo.get("display_name", "").split(",")]
                state_name = display_parts[-2] if len(display_parts) >= 2 else "India"
                clean_name = district_name.strip().title()
                display_label = clean_name

            # Ensure unique name in DB
            existing = db.query(District).filter(District.name.ilike(display_label)).first()
            if existing:
                display_label = f"{clean_name} ({state_name})"
                existing_again = (
                    db.query(District).filter(District.name.ilike(display_label)).first()
                )
                if existing_again:
                    display_label = f"{clean_name} ({round(c_lat, 2)}, {round(c_lon, 2)})"

            district = District(
                name=display_label,
                state=state_name,
                centroid_lat=c_lat,
                centroid_lon=c_lon,
                bbox_min_lat=c_lat - 0.25,
                bbox_max_lat=c_lat + 0.25,
                bbox_min_lon=c_lon - 0.25,
                bbox_max_lon=c_lon + 0.25,
            )
            db.add(district)
            db.commit()
            db.refresh(district)

            # Generate 3x3 5km grid points
            topo = OpenTopoDataAdapter()
            coords_to_query = []
            grid_coords = []
            for dy in [-0.08, 0.0, 0.08]:
                for dx in [-0.08, 0.0, 0.08]:
                    coords_to_query.append((c_lat + dy, c_lon + dx))
                    grid_coords.append((c_lat + dy, c_lon + dx))

            elev_res = topo.get_elevation_batch(coords_to_query)
            elev_list = elev_res.get("elevations", [])

            for i, (plat, plon) in enumerate(grid_coords):
                elev_val = elev_list[i] if i < len(elev_list) else 35.0
                gp = GridPoint(
                    district_id=district.id,
                    lat=plat,
                    lon=plon,
                    elevation_m=float(elev_val),
                )
                db.add(gp)

            # Seed default local emergency facilities for this new location
            db.add(
                Facility(
                    district_id=district.id,
                    name=f"{clean_name} District Hospital",
                    type="hospital",
                    lat=c_lat + 0.015,
                    lon=c_lon - 0.012,
                    capacity=250,
                    capacity_used=40,
                    source="auto_discovery",
                )
            )
            db.add(
                Facility(
                    district_id=district.id,
                    name=f"{clean_name} Central Relief Shelter",
                    type="shelter",
                    lat=c_lat - 0.018,
                    lon=c_lon + 0.014,
                    capacity=500,
                    capacity_used=60,
                    source="auto_discovery",
                )
            )
            db.commit()

        # Check for active official alerts (SACHET / IMD)
        official_alert = (
            db.query(Alert)
            .filter(Alert.district_id == district.id)
            .order_by(Alert.sent_at.desc())
            .first()
        )

        grid_points = db.query(GridPoint).filter(GridPoint.district_id == district.id).all()
        grid_evaluations: List[Dict[str, Any]] = []

        total_rain = 0.0
        total_discharge = 0.0
        total_elevation = 0.0
        n_points = max(len(grid_points), 1)

        for gp in grid_points:
            # Weather & Flood metrics (fetch or fallback)
            fc = forecast_adapter.get_forecast(gp.lat, gp.lon)
            fl = flood_adapter.get_river_discharge(gp.lat, gp.lon)

            rain_val = fc.get("rain_48h_mm", 0.0)
            discharge_val = fl.get("river_discharge_m3s", 0.0)
            elevation_val = gp.elevation_m if gp.elevation_m is not None else 30.0

            total_rain += rain_val
            total_discharge += discharge_val
            total_elevation += elevation_val

            pt_score = score_risk(
                rain_48h_mm=rain_val,
                river_discharge_m3s=discharge_val,
                elevation_m=elevation_val,
                population=15000.0,
                lang=lang,
            )

            grid_evaluations.append(
                {
                    "id": gp.id,
                    "lat": gp.lat,
                    "lon": gp.lon,
                    "elevation_m": elevation_val,
                    "rain_48h_mm": rain_val,
                    "river_discharge_m3s": discharge_val,
                    "risk_score": pt_score["score"],
                    "risk_level": pt_score["level"].lower(),
                    "factors": pt_score["factors"],
                }
            )

        avg_rain = round(total_rain / n_points, 1)
        avg_discharge = round(total_discharge / n_points, 1)
        avg_elevation = round(total_elevation / n_points, 1)

        # Composite score for the whole district
        model_risk = score_risk(
            rain_48h_mm=avg_rain,
            river_discharge_m3s=avg_discharge,
            elevation_m=avg_elevation,
            population=35000.0,
            lang=lang,
        )

        model_level = model_risk["level"].lower()
        effective_level = model_level
        override_active = False

        # Official alert override
        if official_alert and official_alert.level.lower() in ["high", "severe"]:
            effective_level = official_alert.level.lower()
            override_active = True

        # Count facilities
        facilities = db.query(Facility).filter(Facility.district_id == district.id).all()
        shelters_count = sum(
            1 for f in facilities if f.type in ["shelter", "community_centre", "school"]
        )
        hospitals_count = sum(1 for f in facilities if f.type in ["hospital", "clinic"])

        # Real-time weather observation and forecast via OpenWeather
        live_weather = None
        try:
            from backend.app.integrations.openweather import OpenWeatherAdapter

            ow_adapter = OpenWeatherAdapter()
            cw = ow_adapter.get_current_weather(district.centroid_lat, district.centroid_lon)
            fc = ow_adapter.get_forecast(district.centroid_lat, district.centroid_lon)
            if cw:
                live_weather = {
                    "temp_c": cw["temp_c"],
                    "feels_like_c": cw["feels_like_c"],
                    "humidity_pct": cw["humidity_pct"],
                    "pressure_hpa": cw["pressure_hpa"],
                    "wind_speed_kmh": cw["wind_speed_kmh"],
                    "clouds_pct": cw["clouds_pct"],
                    "condition": cw["condition"],
                    "description": cw["description"],
                    "icon": cw["icon"],
                    "rain_1h_mm": cw["rain_1h_mm"],
                    "rain_48h_mm": fc["rain_48h_mm"] if fc else avg_rain,
                    "city_name": cw.get("city_name") or district.name,
                    "source": "openweather",
                    "fetched_at": cw.get("fetched_at"),
                }
        except Exception as exc:
            logger.warning("[RiskService] Live weather fetch failed: %s", exc)

        return {
            "district": {
                "id": district.id,
                "name": district.name,
                "state": district.state,
                "centroid": {"lat": district.centroid_lat, "lon": district.centroid_lon},
                "bbox": {
                    "min_lat": district.bbox_min_lat,
                    "max_lat": district.bbox_max_lat,
                    "min_lon": district.bbox_min_lon,
                    "max_lon": district.bbox_max_lon,
                },
            },
            "risk": {
                "level": effective_level.capitalize(),
                "model_level": model_level.capitalize(),
                "raw_score": model_risk["score"],
                "is_overridden": override_active,
                "official_badge": official_alert.source if official_alert else None,
                "official_alert": (
                    {
                        "source": official_alert.source,
                        "level": official_alert.level,
                        "message_en": official_alert.message_en,
                        "message_hi": official_alert.message_hi,
                        "sent_at": official_alert.sent_at,
                        "identifier": official_alert.identifier,
                    }
                    if official_alert
                    else None
                ),
                "explanation": model_risk["explanation"],
                "factors": model_risk["factors"],
                "metrics": {
                    "avg_rain_48h_mm": avg_rain,
                    "avg_river_discharge_m3s": avg_discharge,
                    "avg_elevation_m": avg_elevation,
                },
            },
            "facilities_summary": {
                "total": len(facilities),
                "shelters": shelters_count,
                "hospitals": hospitals_count,
            },
            "grid_points": grid_evaluations,
            "live_weather": live_weather,
            "disclaimer": "Decision-support tool. Follow official IMD / NDMA warnings.",
        }

    @staticmethod
    def get_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Fetch current weather and forecast for any coordinates across India."""
        try:
            from backend.app.integrations.openweather import OpenWeatherAdapter

            ow_adapter = OpenWeatherAdapter()
            cw = ow_adapter.get_current_weather(lat, lon)
            fc = ow_adapter.get_forecast(lat, lon)
            if cw:
                return {
                    "temp_c": cw["temp_c"],
                    "feels_like_c": cw["feels_like_c"],
                    "humidity_pct": cw["humidity_pct"],
                    "pressure_hpa": cw["pressure_hpa"],
                    "wind_speed_kmh": cw["wind_speed_kmh"],
                    "clouds_pct": cw["clouds_pct"],
                    "condition": cw["condition"],
                    "description": cw["description"],
                    "icon": cw["icon"],
                    "rain_1h_mm": cw["rain_1h_mm"],
                    "rain_48h_mm": fc["rain_48h_mm"] if fc else 0.0,
                    "city_name": cw.get("city_name") or "",
                    "source": "openweather",
                    "fetched_at": cw.get("fetched_at"),
                }
        except Exception as exc:
            logger.warning("[RiskService] get_weather failed: %s", exc)
        return None

    @staticmethod
    def list_all_districts_summary(db: Session, lang: str = "en") -> List[Dict[str, Any]]:
        """List summary risk levels for all districts."""
        districts = db.query(District).all()
        summaries = []
        for d in districts:
            # Latest saved risk score or alert
            latest_rs = (
                db.query(RiskScore)
                .filter(RiskScore.district_id == d.id)
                .order_by(RiskScore.computed_at.desc())
                .first()
            )
            latest_alert = (
                db.query(Alert)
                .filter(Alert.district_id == d.id)
                .order_by(Alert.sent_at.desc())
                .first()
            )
            level = latest_rs.level if latest_rs else "medium"
            if latest_alert and latest_alert.level in ["high", "severe"]:
                level = latest_alert.level

            summaries.append(
                {
                    "id": d.id,
                    "name": d.name,
                    "state": d.state,
                    "lat": d.centroid_lat,
                    "lon": d.centroid_lon,
                    "risk_level": level.lower(),
                    "has_official_alert": latest_alert is not None,
                    "alert_source": latest_alert.source if latest_alert else None,
                }
            )
        return summaries
