-- FloodSaathi SQLite Schema
-- Run via: python src/db/init_db.py
-- Privacy: no real personal data is stored here.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─── Districts ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS districts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    state           TEXT    NOT NULL,
    centroid_lat    REAL    NOT NULL,
    centroid_lon    REAL    NOT NULL,
    bbox_min_lat    REAL,
    bbox_max_lat    REAL,
    bbox_min_lon    REAL,
    bbox_max_lon    REAL
);

-- ─── Grid Points ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grid_points (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id     INTEGER NOT NULL REFERENCES districts(id) ON DELETE CASCADE,
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    elevation_m     REAL
);
CREATE INDEX IF NOT EXISTS idx_grid_district ON grid_points(district_id);

-- ─── Weather Snapshots ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weather_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_point_id       INTEGER NOT NULL REFERENCES grid_points(id) ON DELETE CASCADE,
    fetched_at          TEXT    NOT NULL,   -- ISO 8601
    valid_from          TEXT    NOT NULL,
    valid_to            TEXT    NOT NULL,
    precip_1h_mm        REAL,
    precip_24h_mm       REAL,
    precip_48h_mm       REAL,
    river_discharge_m3s REAL,
    wind_speed_kmh      REAL
);
CREATE INDEX IF NOT EXISTS idx_weather_grid ON weather_snapshots(grid_point_id, fetched_at DESC);

-- ─── Risk Scores ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id     INTEGER NOT NULL REFERENCES districts(id) ON DELETE CASCADE,
    level           TEXT    NOT NULL CHECK(level IN ('low','medium','high','severe')),
    explanation     TEXT,
    score_raw       REAL,               -- 0.0 – 1.0 composite
    computed_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_risk_district_time ON risk_scores(district_id, computed_at DESC);

-- ─── Facilities ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id     INTEGER REFERENCES districts(id) ON DELETE SET NULL,
    name            TEXT    NOT NULL,
    type            TEXT    NOT NULL CHECK(type IN ('hospital','shelter','school','clinic','community_centre','assembly_point')),
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    capacity        INTEGER DEFAULT 0,
    capacity_used   INTEGER DEFAULT 0,
    source          TEXT    DEFAULT 'seed',   -- 'overpass' | 'seed'
    osm_id          TEXT
);
CREATE INDEX IF NOT EXISTS idx_facilities_latlon ON facilities(lat, lon);
CREATE INDEX IF NOT EXISTS idx_facilities_type   ON facilities(type);
CREATE INDEX IF NOT EXISTS idx_facilities_osmid  ON facilities(osm_id);

-- ─── Volunteers ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS volunteers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id     INTEGER REFERENCES districts(id) ON DELETE SET NULL,
    name            TEXT    NOT NULL,       -- synthetic only
    skills          TEXT,                   -- comma-separated: rescue,first-aid
    capacity        INTEGER DEFAULT 1,
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    available       INTEGER DEFAULT 1 CHECK(available IN (0,1)),
    created_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vol_available ON volunteers(available, lat, lon);

-- ─── Help Requests ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS help_requests (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id         INTEGER REFERENCES districts(id) ON DELETE SET NULL,
    raw_text            TEXT    NOT NULL,
    language            TEXT    CHECK(language IN ('en','hi','hinglish')),
    location_raw        TEXT,
    lat                 REAL,
    lon                 REAL,
    urgency             INTEGER CHECK(urgency BETWEEN 1 AND 5),
    need                TEXT    CHECK(need IN ('rescue','medical','food','shelter','other')),
    people_count        INTEGER,
    vulnerable_groups   TEXT,   -- JSON array string: '["elderly","children"]'
    location_source     TEXT,
    location_confidence TEXT,
    summary_en          TEXT,
    summary_hi          TEXT,
    triage_method       TEXT    CHECK(triage_method IN ('llm','fallback')),
    status              TEXT    NOT NULL DEFAULT 'new'
                                CHECK(status IN ('new','assigned','resolved')),
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_req_status   ON help_requests(status);
CREATE INDEX IF NOT EXISTS idx_req_urgency  ON help_requests(urgency DESC);
CREATE INDEX IF NOT EXISTS idx_req_created  ON help_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_req_latlon   ON help_requests(lat, lon);

-- ─── Assignments ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS assignments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL REFERENCES help_requests(id) ON DELETE CASCADE,
    resource_type   TEXT    NOT NULL CHECK(resource_type IN ('hospital','shelter','volunteer')),
    resource_id     INTEGER NOT NULL,   -- FK to facilities.id or volunteers.id
    distance_km     REAL,
    eta_min         INTEGER,
    assigned_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assign_request ON assignments(request_id);

-- ─── Alerts ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id     INTEGER REFERENCES districts(id) ON DELETE SET NULL,
    level           TEXT    NOT NULL CHECK(level IN ('low','medium','high','severe')),
    message_hi      TEXT    NOT NULL,
    message_en      TEXT    NOT NULL,
    channel         TEXT    NOT NULL CHECK(channel IN ('public','volunteer','all')),
    sent_at         TEXT    NOT NULL,
    source          TEXT    DEFAULT 'internal',
    identifier      TEXT
);
CREATE INDEX IF NOT EXISTS idx_alert_district ON alerts(district_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_identifier ON alerts(identifier);

-- ─── Users ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    role            TEXT    NOT NULL CHECK(role IN ('coordinator','volunteer','admin')),
    password_hash   TEXT    NOT NULL,
    created_at      TEXT    NOT NULL
);

-- ─── API Usage Counter (Budget Guard) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_usage (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service         TEXT    NOT NULL,
    date_str        TEXT    NOT NULL,
    count           INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_usage_service_date ON api_usage(service, date_str);
