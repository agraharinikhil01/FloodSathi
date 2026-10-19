"""
app.py
------
FloodSaathi — Streamlit entry point.
This file only handles page config, navigation, and the login sidebar.
All business logic lives in src/.
"""

from __future__ import annotations

import streamlit as st

import config
from src.auth.auth import authenticate
from src.utils.logging_setup import setup_logging

setup_logging(config.LOG_LEVEL)

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="🌊 FloodSaathi",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ─────────────────────────────────────────────────
if "role" not in st.session_state:
    st.session_state["role"] = "citizen"  # anonymous default
if "username" not in st.session_state:
    st.session_state["username"] = None
if "lang" not in st.session_state:
    st.session_state["lang"] = "en"
if "selected_district" not in st.session_state:
    st.session_state["selected_district"] = config.DEFAULT_DISTRICT

# ── Sidebar — language + login ─────────────────────────────────────────────
with st.sidebar:
    st.title("🌊 FloodSaathi")
    st.caption("Flood Emergency Decision Support")
    st.divider()

    # Language toggle
    lang = st.radio("Language / भाषा", ["English", "हिन्दी"], horizontal=True)
    st.session_state["lang"] = "en" if lang == "English" else "hi"

    st.divider()

    # Login / logout
    if st.session_state["role"] == "citizen":
        with st.expander("🔐 Coordinator / Volunteer Login", expanded=False):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                user_record = authenticate(username, password)
                if user_record:
                    st.session_state["role"] = user_record["role"]
                    st.session_state["username"] = user_record["username"]
                    st.rerun()
                else:
                    st.error("Invalid credentials / अमान्य विवरण")
    else:
        st.success(
            f"✅ Logged in as **{st.session_state['username']}** ({st.session_state['role']})"
        )
        if st.button("Logout"):
            st.session_state["role"] = "citizen"
            st.session_state["username"] = None
            st.rerun()

    st.divider()
    st.caption("⚠️ Decision-support tool only. " "Not an official IMD/NDMA warning system.")

# ── Main landing page ──────────────────────────────────────────────────────
st.title("🌊 FloodSaathi")
st.subheader("Flood Emergency Decision Support — India")

st.markdown(f"""
    Welcome to **FloodSaathi**. Use the sidebar to navigate between pages.

    | Page | Description |
    |------|-------------|
    | 🗺️ **Risk Map** | District-level flood risk with colour-coded severity |
    | 🆘 **Help Request** | Submit and triage emergency messages |
    | 📋 **Coordinator Dashboard** | Request queue and resource assignments |
    | 🔔 **Alerts** | Generate bilingual public alerts |
    | 📡 **Integration Status** | Live/cached/failed data source health |

    **Selected district:** `{st.session_state['selected_district']}`
    """)

st.info(
    "⚠️ This is a **decision-support prototype** built for a hackathon. "
    "All data shown is synthetic. Not a replacement for official IMD/NDMA alerts.",
    icon="⚠️",
)
