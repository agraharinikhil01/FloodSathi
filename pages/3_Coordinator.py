"""
pages/3_Coordinator.py
----------------------
Emergency Coordinator Operations Dashboard.
Visualizes incoming help request queue ranked by urgency (1-5).
Executes nearest-resource matching (shelters, hospitals, volunteers) via Haversine geometry.
Renders real-time tactical map with assignment vectors connecting victims to responders.
"""

from __future__ import annotations

import io

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.auth.auth import authenticate, can_access_dashboard
from src.db.queries import (
    get_district_by_name,
    list_assignments_with_details,
    list_districts,
    list_facilities,
    list_help_requests,
    list_volunteers,
    update_request_status,
)
from src.matching.matcher import match_help_request, run_batch_matching

st.set_page_config(page_title="Coordinator Dashboard | FloodSaathi", page_icon="🧭", layout="wide")

lang = st.session_state.get("lang", "en")
is_hi = lang == "hi"

URGENCY_COLORS = {
    5: "#EF4444",  # Critical
    4: "#F97316",  # High
    3: "#EAB308",  # Medium
    2: "#22C55E",  # Low
    1: "#10B981",  # Minimal
}


def _render_sidebar(districts: list[dict]) -> tuple[str, str, int | None]:
    """Render sidebar filters and action controls."""
    st.sidebar.header("Operations Control / नियंत्रण" if is_hi else "Operations Control")
    names = ["All Districts"] + [d["name"] for d in districts]
    selected_dist = st.sidebar.selectbox(
        "Filter District / जिला" if is_hi else "Filter District", options=names
    )

    status_options = ["all", "new", "assigned", "resolved"]
    selected_status = st.sidebar.selectbox(
        "Filter Status / स्थिति" if is_hi else "Filter Status", options=status_options
    )

    urgency_opts = ["All Urgencies", "5 - Critical", "4 - High", "3 - Medium", "2 - Low"]
    selected_urg = st.sidebar.selectbox(
        "Min Urgency / न्यूनतम गंभीरता" if is_hi else "Min Urgency", options=urgency_opts
    )

    min_urg = int(selected_urg.split(" - ")[0]) if "-" in selected_urg else None
    return selected_dist, selected_status, min_urg


def _render_kpis(requests: list[dict], district_id: int | None) -> None:
    """Render executive operational metrics across requests and responders."""
    total_open = sum(1 for r in requests if r["status"] == "new")
    critical_count = sum(1 for r in requests if r["urgency"] == 5 and r["status"] == "new")
    vols = list_volunteers(district_id=district_id, available_only=True)
    shelters = list_facilities(district_id=district_id, facility_type="shelter")
    available_beds = sum(
        max(0, int(s.get("capacity", 100)) - int(s.get("capacity_used", 0))) for s in shelters
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚨 Open Requests", total_open)
    c2.metric("⚡ Critical (Level 5)", critical_count)
    c3.metric("🙋 Ready Volunteers", len(vols))
    c4.metric("🏠 Shelter Capacity Available", available_beds)


def _render_requests_table(requests: list[dict]) -> None:
    """Render interactive triage requests queue with instant match buttons."""
    st.subheader(
        "📋 Priority Request Queue / आपातकालीन अनुरोध कतार"
        if is_hi
        else "📋 Priority Request Queue"
    )
    if not requests:
        st.info("No help requests found matching current filter.")
        return

    for r in requests[:15]:
        req_id = r["id"]
        urg = r.get("urgency", 3)
        badge_color = URGENCY_COLORS.get(urg, "#EAB308")

        with st.container():
            c_info, c_action = st.columns([5, 1])
            with c_info:
                st.markdown(
                    f"""
                    <div style="border-left: 5px solid {badge_color}; background-color:#1E293B; padding:10px 14px; border-radius:6px; margin-bottom:8px;">
                        <b>#{req_id:03d}</b> | <span style="color:{badge_color}; font-weight:bold;">URGENCY {urg}/5</span> |
                        Need: <b>{r['need'].upper()}</b> | People: <b>{r['people_count']}</b> | Loc: <b>{r['location_raw'] or 'Unknown'}</b> |
                        Status: <code>{r['status'].upper()}</code><br/>
                        <span style="color:#CBD5E1; font-size:13px;">{r['summary_en'] or r['raw_text']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_action:
                if r["status"] == "new":
                    if st.button("⚡ Match", key=f"btn_match_{req_id}", use_container_width=True):
                        match_help_request(req_id, persist=True)
                        st.success(f"Matched #{req_id}!")
                        st.rerun()
                elif r["status"] == "assigned":
                    if st.button("✅ Resolve", key=f"btn_res_{req_id}", use_container_width=True):
                        update_request_status(req_id, "resolved")
                        st.rerun()


def _render_assignments_table(assignments: list[dict]) -> None:
    """Render summary table of active resource assignments."""
    st.subheader(
        "🤝 Active Resource Assignments / सक्रिय संसाधन आवंटन"
        if is_hi
        else "🤝 Active Resource Assignments"
    )
    if not assignments:
        st.info("No assignments recorded yet. Use 'Run Auto-Match' above.")
        return

    table_rows = []
    for a in assignments[:25]:
        table_rows.append(
            {
                "Req #": f"#{a['request_id']:03d}",
                "Resource Type": a["resource_type"].upper(),
                "Assigned Resource": a["resource_name"] or f"ID {a['resource_id']}",
                "Distance": f"{a['distance_km']:.2f} km",
                "Est. ETA": f"{a['eta_min']} mins",
                "Assigned At": a["assigned_at"][:19].replace("T", " "),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)


def _build_coordinator_map(
    district_info: dict | None,
    requests: list[dict],
    assignments: list[dict],
) -> folium.Map:
    """Build tactical Folium map showing requests, resources, and assignment vectors."""
    c_lat = float(district_info["centroid_lat"]) if district_info else 26.25
    c_lon = float(district_info["centroid_lon"]) if district_info else 92.34

    m = folium.Map(location=[c_lat, c_lon], zoom_start=11, tiles="CartoDB positron")

    # Draw Request Pins
    for r in requests[:30]:
        if r.get("lat") and r.get("lon"):
            urg = r.get("urgency", 3)
            color = "red" if urg >= 4 else "orange" if urg == 3 else "green"
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=7,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=f"Request #{r['id']} ({r['need']}) - Urgency {urg}/5",
                tooltip=f"Req #{r['id']}: {r['location_raw']}",
            ).add_to(m)

    # Draw Resource Points & Assignment Lines
    for a in assignments[:40]:
        r_lat, r_lon = a.get("request_lat"), a.get("request_lon")
        res_lat, res_lon = a.get("resource_lat"), a.get("resource_lon")
        if r_lat and r_lon and res_lat and res_lon:
            res_type = a.get("resource_type", "")
            line_color = (
                "#3B82F6"
                if res_type == "shelter"
                else "#EF4444" if res_type == "hospital" else "#10B981"
            )
            dash = "6, 6" if res_type != "volunteer" else None

            folium.PolyLine(
                locations=[[r_lat, r_lon], [res_lat, res_lon]],
                color=line_color,
                weight=3,
                opacity=0.75,
                dash_array=dash,
                tooltip=f"Req #{a['request_id']} -> {a['resource_name']} ({a['distance_km']} km, ~{a['eta_min']}m)",
            ).add_to(m)

    return m


def main() -> None:
    """Main dashboard entry point."""
    st.title(
        "🧭 Coordinator Operations Dashboard (समन्वयक डैशबोर्ड)"
        if is_hi
        else "🧭 Coordinator Operations Dashboard"
    )
    st.caption(
        "Real-time decision support: triage queue ranking, automated resource matching, and tactical routing."
    )

    current_role = st.session_state.get("role", "citizen")
    if not can_access_dashboard(current_role):
        st.error(
            "🔒 **ACCESS RESTRICTED / पहुंच प्रतिबंधित**: "
            "This operations portal requires a verified coordinator or volunteer account. "
            "Please log in below with your staff credentials."
            if not is_hi
            else "🔒 **पहुंच प्रतिबंधित**: यह पोर्टल केवल समन्वयकों और स्वयंसेवकों के लिए है। कृपया लॉगिन करें।"
        )
        with st.expander("🔑 Staff Login / स्टाफ लॉगिन", expanded=True):
            u = st.text_input("Username / उपयोगकर्ता नाम", key="coord_user")
            p = st.text_input("Password / पासवर्ड", type="password", key="coord_pass")
            if st.button("Authenticate / प्रवेश करें", type="primary"):
                user_rec = authenticate(u, p)
                if user_rec and can_access_dashboard(user_rec["role"]):
                    st.session_state["role"] = user_rec["role"]
                    st.session_state["username"] = user_rec["username"]
                    st.rerun()
                else:
                    st.error("Invalid credentials or unauthorized role.")
        return

    districts = list_districts()
    sel_dist, sel_status, min_urg = _render_sidebar(districts)

    dist_id = None
    dist_info = None
    if sel_dist != "All Districts":
        dist_info = get_district_by_name(sel_dist)
        dist_id = int(dist_info["id"]) if dist_info else None

    status_filter = None if sel_status == "all" else sel_status
    requests = list_help_requests(
        status=status_filter, urgency=min_urg, district_id=dist_id, limit=100
    )
    assignments = list_assignments_with_details(district_id=dist_id)

    _render_kpis(requests, dist_id)

    # ── Action Bar ─────────────────────────────────────────────────────────────
    st.markdown("---")
    c_btn1, c_btn2, _ = st.columns([2, 2, 4])
    with c_btn1:
        if st.button("⚡ Run Auto-Match for Open Requests", type="primary"):
            with st.spinner("Matching nearest shelters, hospitals, and volunteers..."):
                res = run_batch_matching(district_id=dist_id)
                st.success(f"Matched {len(res)} open requests!")
                st.rerun()

    with c_btn2:
        if assignments:
            df_export = pd.DataFrame(assignments)
            csv_buf = io.StringIO()
            df_export.to_csv(csv_buf, index=False)
            st.download_button(
                label="📥 Export Assignments CSV",
                data=csv_buf.getvalue(),
                file_name="floodsaathi_assignments.csv",
                mime="text/csv",
            )

    # ── Tactical Map ───────────────────────────────────────────────────────────
    st.markdown("##### 🗺️ Tactical Disaster Response Map (Vectors to Assigned Resources)")
    st.caption("🔵 Blue Dashed = Shelter | 🔴 Red Dashed = Hospital | 🟢 Green Solid = Volunteer")
    coord_map = _build_coordinator_map(dist_info, requests, assignments)
    st_folium(coord_map, width="100%", height=460, key="coordinator_tactical_map")

    # ── Queue & Assignments Tables ─────────────────────────────────────────────
    st.markdown("---")
    col_left, col_right = st.columns([1, 1])
    with col_left:
        _render_requests_table(requests)
    with col_right:
        _render_assignments_table(assignments)


if __name__ == "__main__":
    main()
