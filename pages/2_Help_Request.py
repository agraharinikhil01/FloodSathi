"""
pages/2_Help_Request.py
-----------------------
Emergency Help Request submission and AI-powered triage interface.
Parses distress messages in Hindi, English, and Hinglish using Claude / fallback engine.
Extracts structured parameters, geocodes locations via Nominatim, and visualizes on a mini-map.
Privacy notice: Strictly synthetic demonstration data. No real personal records are stored.
"""

from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium

import config
from src.auth.auth import check_rate_limit, sanitize_input
from src.db.queries import list_districts, list_help_requests
from src.matching.matcher import match_help_request
from src.triage.triage import triage_help_request

st.set_page_config(page_title="Help Request | FloodSaathi", page_icon="🆘", layout="wide")

lang = st.session_state.get("lang", "en")
is_hi = lang == "hi"

URGENCY_COLORS = {
    "critical": "#EF4444",
    "high": "#F97316",
    "medium": "#EAB308",
    "low": "#22C55E",
}

SAMPLE_MESSAGES = [
    {
        "label": "मयोंग में 4 लोग फंसे (Hindi)",
        "text": "मदद करो! मयोंग में पानी गले तक पहुंच गया है। 4 लोग छत पर हैं। 2 बच्चे और बुजुर्ग हैं, नाव भेजो जल्दी!",
    },
    {
        "label": "Laharighat Rooftop Rescue (English)",
        "text": "EMERGENCY: House sinking near Laharighat! 5 family members trapped on rooftop including pregnant woman. Need rescue boat immediately!",
    },
    {
        "label": "Jagiroad Car Stranded (Hinglish)",
        "text": "Jagiroad bypass ke pas 10 log phas gaye hain car mein. Road block ho gaya hai flood water se, evacuation boat bhejiye.",
    },
    {
        "label": "Medical Emergency (Silchar)",
        "text": "Elderly patient having severe heart attack symptoms surrounded by 4ft water in Silchar. Doctor needed urgently!",
    },
    {
        "label": "Food & Clean Water (Morigaon)",
        "text": "Morigaon ward 3 mein 8 log hain, khana pani sab doob gaya hai. Ration packets distribute karwayiye please.",
    },
]


def _render_sidebar(districts: list[dict]) -> str:
    """Render sidebar controls and return selected district name."""
    st.sidebar.header("Emergency Settings / सेटिंग्स" if is_hi else "Emergency Settings")
    st.sidebar.markdown(
        "🔒 **Privacy Guarantee**: All submissions in this system are synthetic "
        "demonstration messages. No actual personal names or phones are stored."
    )
    names = [d["name"] for d in districts] if districts else [config.DEFAULT_DISTRICT]
    return st.sidebar.selectbox(
        "Focus District / जिला" if is_hi else "Focus District",
        options=names,
        index=0,
    )


def _render_triage_card(result: dict) -> None:
    """Render live structured triage details and metadata card."""
    triage = result["triage"]
    urgency = triage.urgency
    color = URGENCY_COLORS.get(urgency, "#22C55E")
    match_info = result.get("match")

    st.markdown(
        f"""
        <div style="background-color:#1E293B; border-radius:8px; padding:16px; margin-bottom:16px; border-left:6px solid {color};">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <span style="background-color:{color}; color:white; font-weight:bold; padding:4px 12px; border-radius:4px; font-size:14px;">
                    URGENCY: {urgency.upper()} (Priority Score: {triage.urgency_score}/5)
                </span>
                <span style="background-color:#334155; color:#E2E8F0; padding:4px 10px; border-radius:4px; font-size:13px;">
                    Need: <b>{triage.need.upper()}</b> | People: <b>{triage.people_count}</b>
                </span>
                <span style="background-color:#0F172A; color:#94A3B8; padding:4px 8px; border-radius:4px; font-size:12px;">
                    Method: {result['triage_method'].upper()} | Lang: {triage.language.upper()}
                </span>
            </div>
            <div style="margin-top:12px; font-size:15px; color:#F1F5F9;">
                <b>Detected Location:</b> {triage.location_text}
                <span style="color:#94A3B8; font-size:13px;">({result['display_name']} - Confidence: <b>{result['location_confidence'].upper()}</b>)</span>
            </div>
            <div style="margin-top:8px; color:#CBD5E1; font-size:14px;">
                <b>Summary (EN):</b> {triage.summary}
            </div>
            <div style="margin-top:4px; color:#CBD5E1; font-size:14px;">
                <b>सारांश (HI):</b> {triage.summary_hi or 'लागू नहीं'}
            </div>
            <div style="margin-top:8px; color:#94A3B8; font-size:13px;">
                <b>Vulnerable Groups:</b> {', '.join(triage.vulnerable) if triage.vulnerable else 'None reported'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if match_info:
        _render_match_subcard(match_info)


def _render_match_subcard(match_info: dict) -> None:
    """Render matched nearest shelter, hospital, and volunteer details."""
    h = match_info.get("hospital", {})
    s = match_info.get("shelter", {})
    v = match_info.get("volunteer", {})

    h_name = (
        h.get("resource", {}).get("name", "District Hospital")
        if h.get("resource")
        else "Hospital Pending"
    )
    s_name = (
        s.get("resource", {}).get("name", "Emergency Relief Camp")
        if s.get("resource")
        else "Shelter Pending"
    )
    v_name = (
        v.get("resource", {}).get("name", "Local Responder")
        if v.get("resource")
        else "Volunteer Pending"
    )

    st.markdown(
        f"""
        <div style="background-color:#0F172A; border-radius:6px; padding:12px; margin-top:8px; border:1px solid #334155;">
            <div style="font-weight:bold; color:#38BDF8; margin-bottom:6px;">🎯 Assigned Nearest Resources:</div>
            <div style="font-size:13px; color:#E2E8F0; margin-bottom:4px;">
                🏥 <b>Hospital:</b> {h_name} — <code>{h.get('distance_km', 0):.2f} km</code> (~{h.get('eta_min', 0)} mins)
            </div>
            <div style="font-size:13px; color:#E2E8F0; margin-bottom:4px;">
                🏠 <b>Shelter:</b> {s_name} — <code>{s.get('distance_km', 0):.2f} km</code> (~{s.get('eta_min', 0)} mins)
            </div>
            <div style="font-size:13px; color:#E2E8F0;">
                🙋 <b>Volunteer:</b> {v_name} — <code>{v.get('distance_km', 0):.2f} km</code> (~{v.get('eta_min', 0)} mins)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_mini_map(result: dict) -> None:
    """Render small Folium map showing geocoded request pin and assigned resources."""
    lat = result["lat"]
    lon = result["lon"]
    urgency = result["triage"].urgency
    location_name = result["triage"].location_text

    m = folium.Map(location=[lat, lon], zoom_start=13, tiles="CartoDB positron")
    color = (
        "red" if urgency in ("critical", "high") else "orange" if urgency == "medium" else "green"
    )

    folium.Marker(
        location=[lat, lon],
        popup=f"<b>{location_name}</b><br>Urgency: {urgency.upper()}",
        tooltip=f"{location_name} ({urgency})",
        icon=folium.Icon(color=color, icon="ambulance", prefix="fa"),
    ).add_to(m)

    match_info = result.get("match")
    if match_info:
        for res_type, icon_name, col in [
            ("shelter", "home", "blue"),
            ("hospital", "plus", "red"),
            ("volunteer", "user", "green"),
        ]:
            entry = match_info.get(res_type, {})
            res_obj = entry.get("resource")
            if res_obj and res_obj.get("lat") and res_obj.get("lon"):
                folium.Marker(
                    location=[res_obj["lat"], res_obj["lon"]],
                    popup=f"{res_obj['name']} ({entry.get('distance_km')} km)",
                    tooltip=res_obj["name"],
                    icon=folium.Icon(color=col, icon=icon_name, prefix="fa"),
                ).add_to(m)

    st_folium(m, width="100%", height=320, key="mini_triage_map")


def _render_recent_requests(selected_district: str) -> None:
    """Show the queue of recently triaged requests."""
    st.subheader("📋 Recent Triaged Queue / हाल के अनुरोध" if is_hi else "📋 Recent Triaged Queue")
    requests = list_help_requests(limit=5)
    if not requests:
        st.info("No requests currently triaged." if not is_hi else "कोई अनुरोध उपलब्ध नहीं है।")
        return

    table_data = []
    for r in requests:
        table_data.append(
            {
                "ID": r["id"],
                "Urgency": f"{r['urgency']}/5",
                "Need": r["need"].upper(),
                "People": r["people_count"],
                "Location": r["location_raw"] or "-",
                "Summary": r["summary_en"] or r["raw_text"][:50],
                "Method": r["triage_method"],
                "Status": r["status"].upper(),
            }
        )
    st.dataframe(table_data, use_container_width=True)


def main() -> None:
    """Main page entry point."""
    st.title("🆘 Help Request Triage (मदद अनुरोध)" if not is_hi else "🆘 आपातकालीन मदद अनुरोध")
    st.caption(
        "Enter citizen distress messages in Hindi, English, or Hinglish. "
        "The AI triage engine structures parameters and auto-matches nearby resources."
    )

    districts = list_districts()
    selected_district = _render_sidebar(districts)

    st.markdown("##### Quick Test Examples / त्वरित उदाहरण:")
    cols = st.columns(len(SAMPLE_MESSAGES))
    for i, sample in enumerate(SAMPLE_MESSAGES):
        if cols[i].button(sample["label"], key=f"sample_{i}"):
            st.session_state["msg_input"] = sample["text"]

    current_text = st.session_state.get("msg_input", "")
    user_input = st.text_area(
        "Distress Message (Hindi / English / Hinglish)" if not is_hi else "संकट संदेश",
        value=current_text,
        height=110,
        placeholder="e.g. Bhuragaon me pani gale tak aa gaya hai, 6 log chat par fase hain...",
    )

    if st.button("🚀 Submit & Triage Request (अनुरोध भेजें)", type="primary"):
        # Input validation
        valid, clean_text_or_err = sanitize_input(user_input, max_length=1000)
        if not valid:
            st.error(clean_text_or_err)
            return

        # Session rate limiting (max 5 submissions per minute)
        sub_history = st.session_state.setdefault("submission_history", [])
        if not check_rate_limit(sub_history, max_requests=5, window_seconds=60):
            st.error(
                "⚠️ Rate limit reached (max 5 requests/min). Please wait before submitting again."
                if not is_hi
                else "⚠️ अनुरोध सीमा पार हो गई है (अधिकतम 5/मिनट)। कृपया प्रतीक्षा करें।"
            )
            return

        with st.spinner("Analyzing message, geocoding location, and assigning resources..."):
            res = triage_help_request(
                raw_text=clean_text_or_err,
                fallback_district=selected_district,
                save_to_db=True,
            )
            if res.get("request_id"):
                match_res = match_help_request(res["request_id"], persist=True)
                res["match"] = match_res

            st.session_state["last_triage_result"] = res
            st.success(f"Request triaged & resources matched! (Request ID #{res['request_id']})")

    last_res = st.session_state.get("last_triage_result")
    if last_res:
        st.markdown("---")
        st.subheader("🎯 Structured Triage & Matched Resources / परिणाम")
        col_card, col_map = st.columns([3, 2])
        with col_card:
            _render_triage_card(last_res)
        with col_map:
            _render_mini_map(last_res)

    st.markdown("---")
    _render_recent_requests(selected_district)


if __name__ == "__main__":
    main()
