"""
backend/app/integrations/geocode.py
-----------------------------------
Backend integration adapter for GeocodeService.
Imports and delegates to src.integrations.geocode.GeocodeService.
"""

from src.integrations.geocode import (
    GeocodeService,
    check_and_increment_daily_cap,
    mask_key,
)

__all__ = ["GeocodeService", "check_and_increment_daily_cap", "mask_key"]
