"""
pages/4_Alerts.py
-----------------
Emergency Alerts Generation and Public Notification Page.
Visualizes 48-hour precipitation and river discharge forecast charts with danger thresholds.
Generates concise bilingual alerts (Hindi & English, <= 160 characters) using Claude/templates.
Includes mock dispatch logging and mandatory decision-support disclaimer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import streamlit as st

import config
from src.alerts.generator import (
    generate_alert_for_district,
)
from src.auth.auth import can_manage_alerts
from src.data.weather import fetch_weather_and_discharge
from src.db.queries import get_district_by_name, list_alerts, list_districts
from src.utils.charts import plot_48h_rainfall, plot_river_discharge

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Emergency Alerts | FloodSaathi", page_icon="🔔", layout="wide")

lang = st.session_state.get("lang", "en")
is_hi = lang == "hi"

title_text = (
    "🔔 आपातकालीन चेतावनी और अलर्ट (Emergency Alerts)"
    if is_hi
    else "🔔 Emergency Alerts & Public Warning"
)
st.title(title_text)

# ── Statutory Disclaimer Banner ────────────────────────────────────────────
st.warning(
    "⚠️ **DECISION-SUPPORT NOTICE / निर्णय-समर्थन सूचना**: "
    "FloodSaathi is an emergency coordination and decision-support tool built for relief teams. "
    "Generated alerts assist local volunteers and coordinators and **DO NOT** replace official "
    "warning bulletins issued by the India Meteorological Department (IMD) or NDMA."
    if not is_hi
    else "⚠️ **निर्णय-समर्थन सूचना**: FloodSaathi एक आपातकालीन समन्वय उपकरण है। उत्पन्न अलर्ट आधिकारिक IMD/NDMA चेतावनियों का विकल्प नहीं हैं।"
)

# ── Session State for Mock Dispatches ──────────────────────────────────────
if "broadcast_logs" not in st.session_state:
    st.session_state["broadcast_logs"] = []

# ── Sidebar Controls ───────────────────────────────────────────────────────
st.sidebar.header("Alert Settings / सेटिंग्स" if is_hi else "Alert Settings")
districts = list_districts()
district_names = [d["name"] for d in districts] if districts else [config.DEFAULT_DISTRICT]

selected_district_name = st.sidebar.selectbox(
    "Select Focus District" if not is_hi else "जिला चुनें",
    options=district_names,
    index=(
        0
        if config.DEFAULT_DISTRICT not in district_names
        else district_names.index(config.DEFAULT_DISTRICT)
    ),
)

target_channel = st.sidebar.selectbox(
    "Target Channel" if not is_hi else "प्रसारण चैनल",
    options=["Public Broadcast", "Volunteers Only", "All Channels"],
)

district_info = get_district_by_name(selected_district_name)
c_lat = float(district_info["centroid_lat"]) if district_info else 26.25
c_lon = float(district_info["centroid_lon"]) if district_info else 92.34

# ── 1. Interactive Forecast Line Charts ─────────────────────────────────────
st.subheader(f"📈 48-Hour Forecasts & Danger Thresholds — {selected_district_name}")

with st.spinner("Fetching 48-hour forecast metrics..."):
    df_weather = fetch_weather_and_discharge(
        [{"id": 1, "lat": c_lat, "lon": c_lon}], district_name=selected_district_name
    )

w_row = df_weather.iloc[0] if not df_weather.empty else {}
rain_48h = float(w_row.get("precip_48h_mm", 145.0))
river_flow = float(w_row.get("river_discharge_m3s", 4200.0))

# Build 48 hourly simulation series for chart
times = [f"+{i}h" for i in range(1, 49)]
# Model a realistic frontal rain peak over 48h
base_rain = rain_48h / 48.0
hourly_series = [
    round(max(0.0, base_rain + (4.5 if 10 <= i <= 28 else -1.2) + 0.8 * ((i % 4) - 2)), 2)
    for i in range(1, 49)
]

dates_7d = [f"Day {i}" for i in range(1, 8)]
discharge_series = [
    round(river_flow * (0.85 + 0.08 * i if i <= 4 else 1.15 - 0.07 * (i - 4)), 0)
    for i in range(1, 8)
]

col_left, col_right = st.columns(2)
with col_left:
    fig_rain = plot_48h_rainfall(times, hourly_series, threshold_mm_per_hr=8.0)
    st.plotly_chart(fig_rain, use_container_width=True)

with col_right:
    fig_discharge = plot_river_discharge(dates_7d, discharge_series, danger_threshold_m3s=3500.0)
    st.plotly_chart(fig_discharge, use_container_width=True)

st.divider()

# ── 2. AI Alert Generator ──────────────────────────────────────────────────
st.subheader("⚡ Automated Bilingual Alert Generator (Claude Haiku)")
st.caption("Generates tailored emergency bulletins under the 160-character SMS limit.")

gen_col1, gen_col2 = st.columns([2, 1])
with gen_col1:
    level_choice = st.selectbox(
        "Risk Level for Generated Advisory",
        options=["Severe", "High"],
        index=0 if rain_48h > 120 or river_flow > 3500 else 1,
    )

with gen_col2:
    st.write("")
    st.write("")
    generate_btn = st.button(
        "✨ Generate AI Alert Now / अलर्ट तैयार करें", use_container_width=True
    )

if generate_btn or "current_generated_alert" not in st.session_state:
    with st.spinner("Generating bilingual advisory with Claude / Fallback rules..."):
        alert_data = generate_alert_for_district(
            district_id=district_info["id"] if district_info else 1,
            district_name=selected_district_name,
            level=level_choice,
            metrics={"precip_48h_mm": rain_48h, "river_discharge_m3s": river_flow},
            channel="public" if "Public" in target_channel else "volunteer",
        )
        st.session_state["current_generated_alert"] = alert_data

curr_alert = st.session_state["current_generated_alert"]

# Display Alert Preview Cards
card_col1, card_col2 = st.columns(2)
with card_col1:
    st.markdown(
        f"""
        <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; background-color: #F8FAFC;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:bold; color:#0F172A;">🇬🇧 English Alert Message</span>
                <span style="background-color:#E0F2FE; color:#0369A1; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:bold;">
                    {curr_alert['char_count_en']} / 160 chars
                </span>
            </div>
            <div style="font-size:15px; color:#1E293B; line-height:1.5;">
                {curr_alert['message_en']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_col2:
    st.markdown(
        f"""
        <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; background-color: #F8FAFC;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:bold; color:#0F172A;">🇮🇳 हिन्दी अलर्ट संदेश (Hindi Alert)</span>
                <span style="background-color:#E0F2FE; color:#0369A1; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:bold;">
                    {curr_alert['char_count_hi']} / 160 chars
                </span>
            </div>
            <div style="font-size:15px; color:#1E293B; line-height:1.5;">
                {curr_alert['message_hi']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
col_send1, col_send2 = st.columns([1, 3])
with col_send1:
    if st.button(
        "📢 Mock Send Alert / अलर्ट भेजें (Simulated)", type="primary", use_container_width=True
    ):
        current_role = st.session_state.get("role", "citizen")
        if not can_manage_alerts(current_role):
            st.error(
                "🔒 Coordinator role required to broadcast alerts. "
                "Please log in as a coordinator from the home portal."
                if not is_hi
                else "🔒 अलर्ट भेजने के लिए समन्वयक (Coordinator) का लॉगिन आवश्यक है।"
            )
        else:
            now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            log_entry = {
                "time": now_str,
                "district": selected_district_name,
                "level": curr_alert["level"],
                "channel": target_channel,
                "message_en": curr_alert["message_en"],
                "status": "Simulated Broadcast Logged (No Real SMS Sent)",
            }
            st.session_state["broadcast_logs"].insert(0, log_entry)
            logger.info(
                "[MOCK ALERT SENT] %s -> %s: %s",
                selected_district_name,
                target_channel,
                curr_alert["message_en"],
            )
            st.success(
                f"✅ Alert dispatch successfully logged for {selected_district_name} ({target_channel})."
            )

with col_send2:
    st.caption(
        "ℹ️ The **Send Alert** button simulates broadcast transmission and writes to the dispatch audit log. "
        "No real SMS or telecom carrier charges are incurred."
    )

# ── 3. Dispatch History and Table ──────────────────────────────────────────
st.divider()
st.subheader("📋 Broadcast History & Stored Advisories")

tab1, tab2 = st.tabs(["Recent Session Dispatches", "Database Alert Archive"])

with tab1:
    if st.session_state["broadcast_logs"]:
        st.dataframe(st.session_state["broadcast_logs"], use_container_width=True)
    else:
        st.info("No alerts dispatched in current browser session yet.")

with tab2:
    db_alerts = list_alerts(district_id=district_info["id"] if district_info else None)
    if db_alerts:
        table_rows = [
            {
                "ID": a["id"],
                "Source": a.get("source", "internal"),
                "Level": a["level"].upper(),
                "English": a["message_en"],
                "Hindi": a["message_hi"],
                "Sent At": a["sent_at"],
            }
            for a in db_alerts[:15]
        ]
        st.dataframe(table_rows, use_container_width=True)
    else:
        st.info("No alerts archived in database for this district.")
