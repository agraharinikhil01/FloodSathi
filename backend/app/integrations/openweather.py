"""
backend/app/integrations/openweather.py
---------------------------------------
Bridge module re-exporting OpenWeatherAdapter from src.integrations.openweather.
"""

from src.integrations.openweather import (
    OW_RATE_LIMITER,
    OpenWeatherAdapter,
    mask_secret,
)

__all__ = ["OpenWeatherAdapter", "OW_RATE_LIMITER", "mask_secret"]
