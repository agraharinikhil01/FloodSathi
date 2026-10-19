# FloodSaathi — Internal Service Layer (API.md)

> **Hackathon Edition** · Version 1.0 · References: ARCHITECTURE.md, DATABASE.md
>
> The functions below are Python callables in `src/`. If a FastAPI server is added,
> each maps 1-to-1 to an HTTP endpoint. Streamlit pages call them directly.

---

## Pydantic Models

```python
# src/triage/validator.py

from pydantic import BaseModel, Field
from typing import Literal, Optional

class TriageResult(BaseModel):
    location_raw:       str
    lat:                Optional[float] = None
    lon:                Optional[float] = None
    urgency:            int   = Field(..., ge=1, le=5)
    need:               Literal["rescue","medical","food","shelter","other"]
    people_count:       Optional[int]   = None
    vulnerable_groups:  list[str]       = []   # "elderly"|"children"|"pregnant"|"disabled"
    summary_en:         str
    summary_hi:         str
    language:           Literal["en","hi","hinglish"]
    triage_method:      Literal["llm","fallback"]

class ForecastPoint(BaseModel):
    time:               str            # ISO 8601
    precip_mm:          float
    discharge_m3s:      Optional[float] = None

class FacilityOut(BaseModel):
    id:                 int
    name:               str
    type:               Literal["hospital","shelter","school"]
    lat:                float
    lon:                float
    capacity:           int
    capacity_used:      int
    distance_km:        Optional[float] = None

class VolunteerOut(BaseModel):
    id:                 int
    name:               str
    skills:             str
    lat:                float
    lon:                float
    available:          bool
    distance_km:        Optional[float] = None

class AssignmentOut(BaseModel):
    request_id:         int
    resource_type:      Literal["hospital","shelter","volunteer"]
    resource_id:        int
    resource_name:      str
    distance_km:        float
    eta_min:            int

class RiskOut(BaseModel):
    district:           str
    level:              Literal["low","medium","high","severe"]
    explanation:        str
    score_raw:          float
    computed_at:        str

class AlertOut(BaseModel):
    id:                 int
    district:           str
    level:              str
    message_en:         str
    message_hi:         str
    channel:            str
    sent_at:            str

class RequestOut(BaseModel):
    id:                 int
    district:           Optional[str]
    raw_text:           str
    urgency:            int
    need:               str
    people_count:       Optional[int]
    vulnerable_groups:  list[str]
    summary_en:         Optional[str]
    summary_hi:         Optional[str]
    status:             str
    created_at:         str

class ErrorResponse(BaseModel):
    error:              str
    detail:             Optional[str] = None
    code:               int
```

---

## Endpoints

---

### `GET /risk`

**Function:** `src/risk/engine.get_risk(district: str, hours: int = 48) -> RiskOut`

**Purpose:** Return the latest risk score for a district, optionally forecasting `hours` ahead.

**Request parameters:**

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `district` | string | Yes | — |
| `hours` | int | No | 48 |

**Example request:**
```
GET /risk?district=Morigaon&hours=48
```

**200 Response:**
```json
{
  "district": "Morigaon",
  "level": "severe",
  "explanation": "River discharge 3× normal + 48h cumulative rain > 150 mm.",
  "score_raw": 0.91,
  "computed_at": "2026-10-19T04:30:00Z"
}
```

**404 Response:**
```json
{ "error": "District not found", "detail": "No district named 'XYZ' in DB", "code": 404 }
```

**503 Response (API + cache failure):**
```json
{ "error": "Data unavailable", "detail": "Weather API timed out, no cache available", "code": 503 }
```

---

### `GET /forecast`

**Function:** `src/data/weather.get_combined_forecast(lat: float, lon: float) -> list[ForecastPoint]`

**Purpose:** Return 48 hourly forecast entries combining precipitation and river discharge.

**Request parameters:**

| Param | Type | Required |
|-------|------|----------|
| `lat` | float | Yes |
| `lon` | float | Yes |

**Example request:**
```
GET /forecast?lat=26.25&lon=92.34
```

**200 Response:**
```json
[
  { "time": "2026-10-19T05:00:00Z", "precip_mm": 12.3, "discharge_m3s": 1450.0 },
  { "time": "2026-10-19T06:00:00Z", "precip_mm": 18.7, "discharge_m3s": 1520.5 },
  ...
]
```

**206 Response (stale cache):**
```json
{
  "data": [...],
  "warning": "Cached data from 2026-10-19T04:00:00Z (API unavailable)"
}
```

---

### `GET /facilities`

**Function:** `src/data/facilities.get_facilities(type: str, bbox: str) -> list[FacilityOut]`

**Purpose:** Return facilities within a bounding box, filtered by type.

**Request parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | string | Yes | `hospital` \| `shelter` \| `school` |
| `bbox` | string | Yes | `"min_lat,min_lon,max_lat,max_lon"` |

**Example request:**
```
GET /facilities?type=hospital&bbox=26.0,92.1,26.5,92.6
```

**200 Response:**
```json
[
  {
    "id": 3,
    "name": "Morigaon District Hospital",
    "type": "hospital",
    "lat": 26.27,
    "lon": 92.35,
    "capacity": 200,
    "capacity_used": 45,
    "distance_km": null
  }
]
```

---

### `POST /requests`

**Function:** `src/triage/llm.triage_and_save(raw_text: str) -> RequestOut`

**Purpose:** Triage a raw text message and save the result to DB.

**Request body:**
```json
{
  "raw_text": "bhaiya paani ghar mein ghus gaya, 5 log hain, ek budhiya hai"
}
```

**201 Response:**
```json
{
  "id": 42,
  "district": "Morigaon",
  "raw_text": "bhaiya paani ghar mein ghus gaya, 5 log hain, ek budhiya hai",
  "urgency": 5,
  "need": "rescue",
  "people_count": 5,
  "vulnerable_groups": ["elderly"],
  "summary_en": "Family of 5 trapped including an elderly person, needs rescue.",
  "summary_hi": "5 लोगों का परिवार फंसा है जिसमें एक बुजुर्ग हैं, बचाव जरूरी।",
  "status": "new",
  "created_at": "2026-10-19T10:05:00Z"
}
```

**422 Response (validation failure):**
```json
{ "error": "Triage validation failed", "detail": "urgency field missing from LLM response", "code": 422 }
```

**503 Response (both LLM and fallback fail):**
```json
{ "error": "Triage unavailable", "detail": "Claude API error and fallback extraction failed", "code": 503 }
```

---

### `GET /requests`

**Function:** `src/db/queries.list_requests(status: str | None, urgency: int | None) -> list[RequestOut]`

**Purpose:** Retrieve help requests, optionally filtered.

**Request parameters:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `status` | string | No | `new` \| `assigned` \| `resolved` |
| `urgency` | int | No | 1–5, returns ≥ this value |

**Example request:**
```
GET /requests?status=new&urgency=4
```

**200 Response:** Array of `RequestOut` objects, sorted by `urgency DESC, created_at DESC`.

---

### `POST /match`

**Function:** `src/matching/matcher.run_matching(request_ids: list[int] | None = None) -> list[AssignmentOut]`

**Purpose:** Run resource matching for all new requests (or a specified subset). Updates `help_requests.status` to `assigned`.

**Request body:**
```json
{ "request_ids": [42, 43, 44] }
```
_(empty body = match all `status=new` requests)_

**200 Response:**
```json
[
  {
    "request_id": 42,
    "resource_type": "shelter",
    "resource_id": 7,
    "resource_name": "Govt School Ward 4",
    "distance_km": 0.8,
    "eta_min": 10
  },
  {
    "request_id": 42,
    "resource_type": "volunteer",
    "resource_id": 3,
    "resource_name": "Arjun Singh",
    "distance_km": 0.3,
    "eta_min": 4
  }
]
```

**409 Response (no available resources):**
```json
{ "error": "No resources available", "detail": "All volunteers assigned in district Morigaon", "code": 409 }
```

---

### `GET /alerts`

**Function:** `src/db/queries.list_alerts(district: str) -> list[AlertOut]`

**Purpose:** Retrieve alert history for a district, newest first.

**Example request:**
```
GET /alerts?district=Morigaon
```

**200 Response:** Array of `AlertOut` objects.

---

### `POST /alerts/generate`

**Function:** `src/alerts/generator.generate_alert(district: str, level: str, channel: str) -> AlertOut`

**Purpose:** Generate and store a bilingual alert (does not send real SMS).

**Request body:**
```json
{
  "district": "Morigaon",
  "level": "severe",
  "channel": "public"
}
```

**201 Response:**
```json
{
  "id": 15,
  "district": "Morigaon",
  "level": "severe",
  "message_en": "⚠ SEVERE FLOOD ALERT — Morigaon. Evacuate low-lying areas immediately. Report to: Govt School, Ward 4. Helpline: 1070.",
  "message_hi": "⚠ गंभीर बाढ़ चेतावनी — मोरीगांव। निचले इलाकों से तुरंत निकलें। यहाँ जाएं: सरकारी स्कूल, वार्ड 4। हेल्पलाइन: 1070।",
  "channel": "public",
  "sent_at": "2026-10-19T10:05:00Z"
}
```

---

### `POST /auth/login`

**Function:** `src/db/queries.authenticate(username: str, password: str) -> dict`

**Purpose:** Verify credentials and return a session token (UUID stored in `st.session_state`).

**Request body:**
```json
{ "username": "coordinator", "password": "demo1234" }
```

**200 Response:**
```json
{ "token": "a3f8c2d1-...", "role": "coordinator", "username": "coordinator" }
```

**401 Response:**
```json
{ "error": "Unauthorized", "detail": "Invalid username or password", "code": 401 }
```

---

## External APIs Consumed

### Open-Meteo Forecast API

| Property | Value |
|----------|-------|
| Base URL | `https://api.open-meteo.com/v1/forecast` |
| Auth | None (free) |
| Rate limit | 10 000 req/day (free tier) |
| Timeout | 5 s |
| Retry | 1 × after 2 s |
| Key params | `latitude`, `longitude`, `hourly=precipitation,wind_speed_10m`, `forecast_days=2` |
| Fallback | `data/cache/weather_cache.json` |

### Open-Meteo Flood API

| Property | Value |
|----------|-------|
| Base URL | `https://flood-api.open-meteo.com/v1/flood` |
| Auth | None (free) |
| Rate limit | Same as above |
| Timeout | 5 s |
| Retry | 1 × after 2 s |
| Key params | `latitude`, `longitude`, `daily=river_discharge`, `forecast_days=2` |
| Fallback | `data/cache/flood_cache.json` |

### OSM Overpass API

| Property | Value |
|----------|-------|
| Base URL | `https://overpass-api.de/api/interpreter` |
| Auth | None |
| Rate limit | Polite use; 1 req / 2 s max |
| Timeout | 10 s |
| Retry | 0 (cache hit expected) |
| Cache TTL | 24 hours |
| Fallback | Seed data in `data/seed/` |
| Sample query | `[out:json]; node["amenity"="hospital"](bbox); out body;` |

### Nominatim Geocoding

| Property | Value |
|----------|-------|
| Base URL | `https://nominatim.openstreetmap.org/search` |
| Auth | None |
| Rate limit | **1 req/s** (enforced by `time.sleep(1)` in fetcher) |
| Timeout | 5 s |
| Retry | 1 × after 1 s |
| Cache TTL | 7 days |
| Fallback | Return district centroid from DB |
| Headers | `User-Agent: FloodSaathi-Hackathon/1.0` (required by Nominatim ToS) |

### OpenTopoData Elevation

| Property | Value |
|----------|-------|
| Base URL | `https://api.opentopodata.org/v1/srtm30m` |
| Auth | None (free public instance) |
| Rate limit | 1 req/s |
| Timeout | 5 s |
| Retry | 0 |
| Fallback | Return `None`; risk engine skips elevation factor |

### Anthropic Claude API

| Property | Value |
|----------|-------|
| Model | `claude-3-5-haiku-20241022` (fast, cheap) |
| Auth | `ANTHROPIC_API_KEY` from `.env` |
| Rate limit | Tier-dependent; ~50 RPM on free tier |
| Timeout | 15 s (LLM can be slow) |
| Retry | 1 × after 2 s exponential backoff |
| Max tokens | 512 (triage output is compact JSON) |
| Fallback | `src/triage/fallback.py` keyword extractor |
| Prompt template | See `src/triage/llm.py` |
