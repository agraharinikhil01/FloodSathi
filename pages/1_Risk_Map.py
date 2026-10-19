"""
pages/1_Risk_Map.py
-------------------
Risk Map page for FloodSaathi.
Displays district-level grid points on an interactive Folium map with risk-colored
markers, weather metrics, river discharge, elevation, and plain-language explanations.
"""

from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium

import config
from src.data.elevation import fetch_elevation_batch
from src.data.grid import get_district_grid
from src.data.weather import fetch_weather_and_discharge
from src.db.queries import (
    get_district_by_name,
    list_districts,
    list_facilities,
    list_volunteers,
    save_risk_score,
)
from src.risk.engine import compute_risk_for_points

# ── Colors per DESIGN.md ────────────────────────────────────────────────────
RISK_COLORS = {
    "Low": "#22C55E",  # Green
    "Medium": "#EAB308",  # Yellow
    "High": "#F97316",  # Orange
    "Severe": "#EF4444",  # Red
}

RISK_HINDI = {
    "Low": "कम",
    "Medium": "मध्यम",
    "High": "अधिक",
    "Severe": "गंभीर",
}


def _get_district_options() -> list[str]:
    """Retrieve list of district names from the database."""
    districts = list_districts()
    if not districts:
        return [config.DEFAULT_DISTRICT]
    return [d["name"] for d in districts]


def _build_popup_html(pt: dict, lang: str = "en") -> str:
    """Construct an HTML popup string with risk metrics and explanation."""
    level = pt.get("level", "Low")
    color = RISK_COLORS.get(level, "#3B82F6")
    level_label = f"{level} / {RISK_HINDI.get(level, level)}" if lang == "hi" else level

    return f"""
    <div style="font-family:sans-serif; min-width:210px; font-size:13px; line-height:1.4;">
        <div style="font-weight:bold; font-size:14px; margin-bottom:4px;">
            Grid Point #{pt.get('id', '')} ({pt.get('lat', 0):.3f}, {pt.get('lon', 0):.3f})
        </div>
        <div style="background-color:{color}; color:white; font-weight:bold; padding:3px 8px; border-radius:4px; display:inline-block; margin-bottom:6px;">
            {level_label} (Score: {pt.get('score', 0):.2f})
        </div>
        <div style="margin-bottom:6px; color:#333;">
            <b>Explanation:</b> {pt.get('explanation', '')}
        </div>
        <hr style="margin:4px 0; border:none; border-top:1px solid #ddd;"/>
        <div><b>48h Rain:</b> {pt.get('precip_48h_mm', 0):.1f} mm</div>
        <div><b>River Discharge:</b> {pt.get('river_discharge_m3s', 0):.0f} m³/s</div>
        <div><b>Elevation:</b> {pt.get('elevation_m', 0):.1f} m ASL</div>
        <div><b>Est. Population:</b> {pt.get('population', 0):,}</div>
    </div>
    """


def render_risk_map(
    district_info: dict,
    grid_points: list[dict],
    facilities: list[dict],
    volunteers: list[dict],
    show_facilities: bool,
    show_volunteers: bool,
    lang: str = "en",
) -> folium.Map:
    """Build and return a Folium map instance configured with markers and layers."""
    c_lat = float(district_info["centroid_lat"])
    c_lon = float(district_info["centroid_lon"])

    m = folium.Map(location=[c_lat, c_lon], zoom_start=11, tiles="CartoDB positron")

    # Add Grid Point Circle Markers
    for pt in grid_points:
        level = pt.get("level", "Low")
        color = RISK_COLORS.get(level, "#22C55E")
        popup_html = _build_popup_html(pt, lang=lang)

        folium.CircleMarker(
            location=[pt["lat"], pt["lon"]],
            radius=12,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=2,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{pt.get('district_name', '')} #{pt.get('id', '')}: {level} ({pt.get('score', 0):.2f})",
        ).add_to(m)

    # Optional Layer: Facilities
    if show_facilities:
        for f in facilities:
            f_type = f.get("type", "shelter")
            icon_name = "plus" if f_type == "hospital" else "home"
            icon_color = "red" if f_type == "hospital" else "blue"
            folium.Marker(
                location=[f["lat"], f["lon"]],
                popup=f"<b>{f.get('name', 'Facility')}</b><br/>Type: {f_type.title()}<br/>Capacity: {f.get('capacity', 0)}",
                icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
            ).add_to(m)

    # Optional Layer: Volunteers
    if show_volunteers:
        for v in volunteers:
            folium.Marker(
                location=[v["lat"], v["lon"]],
                popup=f"<b>Volunteer: {v.get('name', '')}</b><br/>Skills: {v.get('skills', '')}",
                icon=folium.Icon(color="green", icon="user", prefix="fa"),
            ).add_to(m)

    return m


def main() -> None:
    st.set_page_config(page_title="Flood Risk Map | FloodSaathi", page_icon="🗺️", layout="wide")

    lang = st.session_state.get("lang", "en")
    is_hi = lang == "hi"

    title_text = "🗺️ जिला बाढ़ जोखिम मानचित्र (Risk Map)" if is_hi else "🗺️ District Flood Risk Map"
    st.title(title_text)

    # ── Sidebar Controls ───────────────────────────────────────────────────
    st.sidebar.header("Map Controls / नियंत्रण" if is_hi else "Map Controls")
    district_options = _get_district_options()
    selected_name = st.sidebar.selectbox(
        "Select District / जिला चुनें" if is_hi else "Select District",
        options=district_options,
        index=(
            0
            if config.DEFAULT_DISTRICT not in district_options
            else district_options.index(config.DEFAULT_DISTRICT)
        ),
    )

    show_facilities = st.sidebar.checkbox(
        "Hospitals & Shelters" if not is_hi else "अस्पताल और आश्रय", value=True
    )
    show_volunteers = st.sidebar.checkbox(
        "Volunteers" if not is_hi else "स्वयंसेवक (Volunteers)", value=True
    )

    district_info = get_district_by_name(selected_name)
    if not district_info:
        st.error(f"District '{selected_name}' not found.")
        return

    # ── Compute Data with Spinner ──────────────────────────────────────────
    with st.spinner("Computing grid risk scores & fetching forecasts..."):
        grid_pts = get_district_grid(district_info, count=16)

        # 1. Weather & river discharge
        df_weather = fetch_weather_and_discharge(grid_pts, district_name=selected_name)

        # 2. Elevations
        coords = [(pt["lat"], pt["lon"]) for pt in grid_pts]
        elevations = fetch_elevation_batch(coords, district_name=selected_name)

        # 3. Combine into evaluated points
        combined: list[dict] = []
        for i, pt in enumerate(grid_pts):
            w_row = df_weather.iloc[i] if i < len(df_weather) else {}
            c_dict = dict(pt)
            c_dict["precip_48h_mm"] = float(w_row.get("precip_48h_mm", 0.0))
            c_dict["river_discharge_m3s"] = float(w_row.get("river_discharge_m3s", 0.0))
            c_dict["elevation_m"] = float(elevations[i])
            c_dict["source"] = w_row.get("source", "live")
            combined.append(c_dict)

        evaluated_points = compute_risk_for_points(combined, lang=lang)

    # ── Official SACHET & IMD Alerts Integration ───────────────────────────
    from src.db.queries import get_active_official_alert
    from src.integrations.imd import IMDAdapter
    from src.integrations.sachet import SachetAdapter

    sachet = SachetAdapter()
    sachet.sync_alerts()
    official_alert = get_active_official_alert(district_info["id"])

    imd = IMDAdapter()
    imd_badge = imd.get_district_badge(selected_name)

    # If official alert exists, display badge and override model's risk level & color
    override_active = False
    official_level = None
    if official_alert:
        override_active = True
        official_level = official_alert["level"].capitalize()
        st.error(
            f"🏛️ **Official SACHET Alert ({official_level}) Active**: {official_alert['message_en']}\n\n"
            f"*(Note: Official alert status overrides model computed risk color)*"
        )

    if imd_badge:
        st.warning(f"⚡ **IMD Warning Badge**: **{imd_badge['label']}** — {imd_badge['text']}")

    # ── Cache / Source Banner ──────────────────────────────────────────────
    sources = {pt.get("source") for pt in evaluated_points}
    if "fallback" in sources:
        st.warning(
            "⚠️ Live weather API unreachable. Showing fallback baseline data."
            if not is_hi
            else "⚠️ लाइव वेदर एपीआई उपलब्ध नहीं है। फॉलबैक बेसलाइन डेटा दिखाया जा रहा है।"
        )
    elif "stale_cache" in sources:
        st.info("ℹ️ Displaying cached forecast from last 1 hour.")

    # Apply official alert override to points if present
    if override_active and official_level:
        for pt in evaluated_points:
            pt["level"] = official_level
            pt["explanation"] = (
                f"[Official SACHET Advisory: {official_alert['message_en']}] " + pt["explanation"]
            )

    # ── Save aggregate score to DB ─────────────────────────────────────────
    avg_score = sum(p["score"] for p in evaluated_points) / max(len(evaluated_points), 1)
    max_pt = max(evaluated_points, key=lambda x: x["score"])
    save_risk_score(
        district_id=district_info["id"],
        level=official_level if override_active and official_level else max_pt["level"],
        explanation=official_alert["message_en"] if override_active else max_pt["explanation"],
        score_raw=round(avg_score, 4),
    )

    # ── KPI Summary Cards ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    active_level = official_level if override_active and official_level else max_pt["level"]
    severe_count = sum(1 for p in evaluated_points if p["level"] == "Severe")
    high_count = sum(1 for p in evaluated_points if p["level"] == "High")
    max_rain = max(p["precip_48h_mm"] for p in evaluated_points)
    max_discharge = max(p["river_discharge_m3s"] for p in evaluated_points)

    delta_label = "OFFICIAL OVERRIDE" if override_active else f"Score: {max_pt['score']:.2f}"
    c1.metric("Highest Severity", active_level, delta=delta_label)
    c2.metric("Critical Points", f"{severe_count + high_count} / {len(evaluated_points)}")
    c3.metric("Max 48h Rain", f"{max_rain:.1f} mm")
    c4.metric("Max River Discharge", f"{max_discharge:.0f} m³/s")

    # ── Folium Map ─────────────────────────────────────────────────────────
    facilities = list_facilities(district_id=district_info["id"])
    volunteers = list_volunteers(district_id=district_info["id"])

    risk_map = render_risk_map(
        district_info=district_info,
        grid_points=evaluated_points,
        facilities=facilities,
        volunteers=volunteers,
        show_facilities=show_facilities,
        show_volunteers=show_volunteers,
        lang=lang,
    )

    st_folium(risk_map, width="100%", height=520)

    # ── Legend ─────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="display:flex; gap:16px; align-items:center; margin-top:8px; font-size:14px;">
            <span><b>Legend:</b></span>
            <span><span style="color:#22C55E; font-size:18px;">●</span> Low (&lt;0.25)</span>
            <span><span style="color:#EAB308; font-size:18px;">●</span> Medium (0.25–0.50)</span>
            <span><span style="color:#F97316; font-size:18px;">●</span> High (0.50–0.75)</span>
            <span><span style="color:#EF4444; font-size:18px;">●</span> Severe (&gt;0.75)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Granular Data Expander ─────────────────────────────────────────────
    with st.expander("🔍 View All Grid Points & Factor Details"):
        table_rows = []
        for p in evaluated_points:
            table_rows.append(
                {
                    "Grid ID": p["id"],
                    "Lat": p["lat"],
                    "Lon": p["lon"],
                    "Risk Level": p["level"],
                    "Score": round(p["score"], 3),
                    "Rain 48h (mm)": p["precip_48h_mm"],
                    "Discharge (m³/s)": p["river_discharge_m3s"],
                    "Elevation (m)": p["elevation_m"],
                    "Primary Driver": p["explanation"],
                }
            )
        st.dataframe(table_rows, use_container_width=True)


if __name__ == "__main__":
    main()
