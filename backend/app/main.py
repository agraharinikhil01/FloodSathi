"""FastAPI main application entry point for FloodSaathi."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import get_settings
from backend.app.routers import alerts, geocode, health, matching, risk, triage

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Flood early-warning and rescue-coordination web platform for India.",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
def startup_checks():
    import logging

    from backend.app.db import ensure_db_initialized

    ensure_db_initialized()

    log = logging.getLogger("uvicorn.info")
    geo_key = settings.GEOAPIFY_API_KEY
    geo_status = (
        f"Enabled (Daily Cap: {settings.GEOCODE_DAILY_CAP})"
        if geo_key
        else "Not configured (missing GEOAPIFY_API_KEY)"
    )
    ow_key = settings.OPENWEATHER_API_KEY
    ow_status = "Enabled" if ow_key else "Not configured (missing OPENWEATHER_API_KEY)"
    log.info(
        "[Startup] Integrations: OpenWeather=%s, Geoapify=%s, Photon=Enabled, Nominatim=Enabled, OfflineDemo=%s",
        ow_status,
        geo_status,
        settings.OFFLINE_DEMO,
    )


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development & local access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standard Exception Handlers conforming to {error: {code, message, details}}
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all unhandled exception handler returning uniform envelope."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "details": None,
            }
        },
    )


# Include Routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(risk.router, prefix=settings.API_V1_STR)
app.include_router(triage.router, prefix=settings.API_V1_STR)
app.include_router(matching.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(geocode.router, prefix=settings.API_V1_STR)


@app.get("/api")
def api_root():
    """API metadata endpoint."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
        "disclaimer": "Decision-support tool. Follow official IMD / NDMA warnings.",
    }


frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
else:

    @app.get("/")
    def root():
        """Root entry point with service metadata."""
        return api_root()
