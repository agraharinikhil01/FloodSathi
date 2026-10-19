"""
tests/test_openweather.py
-------------------------
Unit tests for OpenWeatherMap integration:
- Mocked current weather and 5-day forecast responses (no network)
- Accurate 48h rainfall summation
- Missing API key behavior
- HTTP failure and error tolerance
- Zero key leakage in masked URLs and logs
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.integrations.openweather import OpenWeatherAdapter, mask_secret


@pytest.fixture
def ow_adapter(tmp_path, monkeypatch):
    """OpenWeatherAdapter with isolated temporary cache directory."""
    cache_dir = tmp_path / "openweather_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.integrations.openweather.config.CACHE_DIR", tmp_path)
    adapter = OpenWeatherAdapter()
    adapter.cache_dir = cache_dir
    return adapter


# ─────────────────────────────────────────────────────────────────────────────
# 1. Current Weather Success
# ─────────────────────────────────────────────────────────────────────────────
def test_openweather_current_weather_success(ow_adapter):
    """Test parsing and normalization of OpenWeather current weather response."""
    mock_payload = {
        "cod": 200,
        "name": "Patna",
        "main": {
            "temp": 24.61,
            "feels_like": 25.10,
            "temp_min": 23.5,
            "temp_max": 25.5,
            "humidity": 68,
            "pressure": 1013,
        },
        "weather": [
            {
                "id": 500,
                "main": "Rain",
                "description": "light rain",
                "icon": "10d",
            }
        ],
        "wind": {"speed": 3.5},
        "clouds": {"all": 75},
        "rain": {"1h": 2.4},
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with (
        patch.object(ow_adapter.session, "request", return_value=mock_resp),
        patch.object(ow_adapter, "_get_api_key", return_value="dummy_ow_key_12345"),
    ):

        result = ow_adapter.get_current_weather(lat=25.6, lon=85.1)

    assert result is not None
    assert result["temp_c"] == 24.6
    assert result["feels_like_c"] == 25.1
    assert result["humidity_pct"] == 68
    assert result["condition"] == "Rain"
    assert result["description"] == "Light Rain"
    assert result["rain_1h_mm"] == 2.4
    assert result["wind_speed_kmh"] == round(3.5 * 3.6, 1)
    assert result["source"] == "openweather"


# ─────────────────────────────────────────────────────────────────────────────
# 2. 48-Hour Forecast Aggregation
# ─────────────────────────────────────────────────────────────────────────────
def test_openweather_forecast_48h_aggregation(ow_adapter):
    """Verify that 48-hour rainfall accurately sums the first 16 periods (16 x 3h)."""
    # 20 periods total (60 hours), only first 16 should count towards 48h
    mock_list = []
    for i in range(20):
        # 1.5mm rain per 3-hour period for the first 16 periods -> 16 * 1.5 = 24.0mm
        rain_val = 1.5 if i < 16 else 5.0
        mock_list.append(
            {
                "dt_txt": f"2026-10-20 {i:02d}:00:00",
                "main": {"temp": 22.0 + (i % 3), "humidity": 60},
                "weather": [{"main": "Rain", "description": "moderate rain", "icon": "10d"}],
                "rain": {"3h": rain_val},
                "pop": 0.8,
            }
        )

    mock_payload = {
        "cod": "200",
        "city": {"name": "Patna"},
        "list": mock_list,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with (
        patch.object(ow_adapter.session, "request", return_value=mock_resp),
        patch.object(ow_adapter, "_get_api_key", return_value="dummy_ow_key_12345"),
    ):

        forecast = ow_adapter.get_forecast(lat=25.6, lon=85.1)

    assert forecast is not None
    assert forecast["rain_48h_mm"] == 24.0  # 16 periods * 1.5
    assert forecast["rain_24h_mm"] == 12.0  # 8 periods * 1.5
    assert len(forecast["forecast_periods"]) == 16
    assert forecast["source"] == "openweather"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Missing Key Behavior
# ─────────────────────────────────────────────────────────────────────────────
def test_openweather_missing_key_behavior(ow_adapter):
    """When API key is empty or missing, adapter returns None without error."""
    with patch.object(ow_adapter, "_get_api_key", return_value=""):
        cw = ow_adapter.get_current_weather(lat=25.6, lon=85.1)
        fc = ow_adapter.get_forecast(lat=25.6, lon=85.1)

    assert cw is None
    assert fc is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. HTTP Failure & Error Tolerance
# ─────────────────────────────────────────────────────────────────────────────
def test_openweather_http_failure_handling(ow_adapter):
    """When OpenWeather returns 401 or network error, returns None without crashing."""
    mock_err_resp = MagicMock()
    mock_err_resp.status_code = 401
    mock_err_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")

    with (
        patch.object(ow_adapter.session, "request", return_value=mock_err_resp),
        patch.object(ow_adapter, "_get_api_key", return_value="invalid_key"),
    ):

        cw = ow_adapter.get_current_weather(lat=25.6, lon=85.1)

    assert cw is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Secret Key Masking
# ─────────────────────────────────────────────────────────────────────────────
def test_openweather_secret_masking():
    """Verify that mask_secret scrubs appid from URLs and strings."""
    secret = "3d7fc2151c39ebb482fcf9249a7a05fd"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat=25.6&lon=85.1&appid={secret}&units=metric"

    masked = mask_secret(url)
    assert secret not in masked
    assert "appid=***" in masked
