# FloodSaathi — Data Sources & External API Registry

This document lists all upstream data sources, exact API endpoints, caching policies, and fallback strategies. Never invent other URLs.

---

## 1. Open-Meteo Weather Forecast API
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Method**: `GET`
- **Parameters**: `latitude`, `longitude`, `hourly=precipitation`, `daily=precipitation_sum`, `forecast_days=7`, `timezone=Asia/Kolkata`
- **Purpose**: 48-hour cumulative rainfall forecasting (`precip_48h_mm`).
- **Cache TTL**: 1 hour (`CACHE_TTL_WEATHER_H=1`).
- **Fallback**: `data/cache/fixtures/weather/` or `data/cache/weather/`.

---

## 2. Open-Meteo Flood API
- **Endpoint**: `https://flood-api.open-meteo.com/v1/flood`
- **Method**: `GET`
- **Parameters**: `latitude`, `longitude`, `daily=river_discharge,river_discharge_max`, `forecast_days=7`
- **Purpose**: 48-hour river discharge forecasting (`river_discharge_m3s`).
- **Grid Offset Rule**: If discharge is null or 0, probe $\pm 0.1^\circ$ in 4 cardinal directions and take the maximum. Mark as "modelled, not measured".
- **Cache TTL**: 3 hours.
- **Fallback**: `data/cache/fixtures/flood/` or `data/cache/flood/`.

---

## 3. OpenStreetMap Overpass API
- **Endpoint**: `https://overpass-api.de/api/interpreter`
- **Method**: `POST` with `data=<query>`
- **Query**: Bounding box query for `amenity=hospital`, `amenity=clinic`, `amenity=school`, `amenity=community_centre`, `emergency=assembly_point`, output `out center;`.
- **Purpose**: Seed critical rescue facilities (hospitals and emergency shelters).
- **Cache TTL**: 7 days (`CACHE_TTL_FACILITIES_H=168`).
- **Fallback**: `data/cache/fixtures/overpass/` or `data/cache/overpass/`.

---

## 4. Nominatim Geocoding API
- **Endpoint**: `https://nominatim.openstreetmap.org/search`
- **Method**: `GET`
- **Parameters**: `q=<text>`, `format=json`, `limit=1`, `countrycodes=in`
- **Headers**: `User-Agent: FloodSaathi/1.0 (contact@floodsaathi.in)`
- **Throttling**: Strict 1.0 second delay between live requests.
- **Cache TTL**: Permanent (100 years).
- **Fallback**: District centroid from database with `location_confidence='low'`.

---

## 5. OpenTopoData Elevation API
- **Endpoint**: `https://api.opentopodata.org/v1/srtm90m`
- **Method**: `GET`
- **Parameters**: `locations=lat1,lon1|lat2,lon2`
- **Limits**: Max 100 locations per call, 1 request per second.
- **Cache TTL**: Permanent (100 years).
- **Fallback**: `data/cache/fixtures/elevation/`.

---

## 6. NDMA SACHET RSS / CAP Alerts
- **Endpoint**: `https://sachet.ndma.gov.in/` (State RSS XML feeds)
- **Method**: `GET`
- **Headers**: `User-Agent: FloodSaathi/1.0`, conditional HTTP caching via `ETag` and `If-Modified-Since`.
- **Poll Interval**: 5 minutes.
- **Filter**: Severe / Extreme CAP events matching target district keywords.
- **Fallback**: `data/cache/fixtures/sachet/`.

---

## 7. Optional & Placeholder Adapters
- **IMD Warnings API**: `https://api.imd.gov.in/api/v1` (Disabled unless `IMD_ENABLED=true`).
- **ReliefWeb API**: `https://api.reliefweb.int/v1/reports` (Disabled unless `RELIEFWEB_ENABLED=true`).
- **data.gov.in API**: `https://api.data.gov.in/resource/` (Disabled unless `DATAGOV_ENABLED=true`).
