"""
src/utils/charts.py
-------------------
Interactive Plotly forecast visualizations for 48-hour precipitation
and river discharge with reference danger thresholds.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


def plot_48h_rainfall(
    hourly_times: list[str],
    hourly_precip: list[float],
    threshold_mm_per_hr: float = 10.0,
) -> go.Figure:
    """Create a Plotly bar/line chart of 48-hour hourly rainfall with a danger threshold."""
    # Take first 48 points or pad if fewer
    times = hourly_times[:48] if hourly_times else [f"+{i}h" for i in range(1, 49)]
    precip = hourly_precip[:48] if hourly_precip else [0.0] * len(times)

    fig = go.Figure()

    # Hourly precipitation bars
    fig.add_trace(
        go.Bar(
            x=times,
            y=precip,
            name="Hourly Rain (mm)",
            marker_color="#3B82F6",
            hovertemplate="Time: %{x}<br>Rainfall: %{y:.1f} mm<extra></extra>",
        )
    )

    # Threshold horizontal reference line
    fig.add_hline(
        y=threshold_mm_per_hr,
        line_dash="dash",
        line_color="#EF4444",
        line_width=2,
        annotation_text=f"Heavy Rain Alert Threshold ({threshold_mm_per_hr} mm/h)",
        annotation_position="top right",
        annotation_font_color="#EF4444",
    )

    fig.update_layout(
        title="<b>48-Hour Precipitation Forecast (mm/h)</b>",
        xaxis_title="Timeline (Hourly)",
        yaxis_title="Precipitation (mm)",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
        height=320,
        showlegend=False,
    )

    return fig


def plot_river_discharge(
    dates: list[str],
    discharge_m3s: list[float],
    danger_threshold_m3s: float = 3500.0,
) -> go.Figure:
    """Create a Plotly line chart of river discharge forecast with danger flood mark."""
    fig = go.Figure()

    # Discharge curve
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=discharge_m3s,
            mode="lines+markers",
            name="Discharge (m³/s)",
            line=dict(color="#0284C7", width=3),
            marker=dict(size=7, color="#0369A1"),
            hovertemplate="Date: %{x}<br>Discharge: %{y:.0f} m³/s<extra></extra>",
        )
    )

    # Danger flood level threshold
    fig.add_hline(
        y=danger_threshold_m3s,
        line_dash="dot",
        line_color="#DC2626",
        line_width=2,
        annotation_text=f"Danger Level ({danger_threshold_m3s:.0f} m³/s)",
        annotation_position="top left",
        annotation_font_color="#DC2626",
    )

    fig.update_layout(
        title="<b>River Discharge Forecast (m³/s)</b>",
        xaxis_title="Date",
        yaxis_title="Discharge (m³/s)",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
        height=320,
        showlegend=False,
    )

    return fig


def build_default_charts(
    weather_raw: dict[str, Any] | None,
) -> tuple[go.Figure, go.Figure]:
    """Helper constructing both charts from Open-Meteo raw dictionary or default synthetic data."""
    if weather_raw and isinstance(weather_raw, dict):
        hourly = weather_raw.get("hourly", {})
        times = hourly.get("time", [])
        precip = hourly.get("precipitation", [])
        daily = weather_raw.get("daily", {})
        dates = daily.get("time", [f"Day {i+1}" for i in range(7)])
        discharges = [3200.0, 3600.0, 4100.0, 4400.0, 3900.0, 3300.0, 2900.0]
    else:
        times = [f"+{i}h" for i in range(1, 49)]
        precip = [4.5 + 2.0 * ((i % 6) - 2) for i in range(48)]
        dates = [f"Day {i+1}" for i in range(7)]
        discharges = [2800.0, 3400.0, 4250.0, 4800.0, 3950.0, 3100.0, 2600.0]

    f_rain = plot_48h_rainfall(times, precip)
    f_discharge = plot_river_discharge(dates, discharges)
    return f_rain, f_discharge
