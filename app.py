import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import json
import yaml
from pathlib import Path
from datetime import datetime
from src.graph import graph
from src.sop_engine import sop_engine
from src.config import SOPS_PATH

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AERO-GUARD | Weather Safety & SOP Policy Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# State Initialization
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_state" not in st.session_state:
    st.session_state.agent_state = {
        "messages": [],
        "session_id": f"aero-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "extracted_location": None,
        "coordinates": None,
        "extracted_activity": None,
        "target_time_window": "current",
        "weather_data": None,
        "matched_sops": [],
        "selected_sop": None,
        "secondary_sops": [],
        "conflict_resolution_rationale": None,
        "execution_status": "READY",
        "final_answer": ""
    }

def reset_session():
    st.session_state.messages = []
    st.session_state.agent_state = {
        "messages": [],
        "session_id": f"aero-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "extracted_location": None,
        "coordinates": None,
        "extracted_activity": None,
        "target_time_window": "current",
        "weather_data": None,
        "matched_sops": [],
        "selected_sop": None,
        "secondary_sops": [],
        "conflict_resolution_rationale": None,
        "execution_status": "READY",
        "final_answer": ""
    }

# -----------------------------------------------------------------------------
# WMO Weather Code Descriptions & Icons
# -----------------------------------------------------------------------------
WMO_WEATHER_MAP = {
    0: ("Clear sky", "☀️", "#FBBF24"),
    1: ("Mainly clear", "🌤️", "#FBBF24"),
    2: ("Partly cloudy", "⛅", "#94A3B8"),
    3: ("Overcast", "☁️", "#94A3B8"),
    45: ("Foggy", "🌫️", "#94A3B8"),
    48: ("Depositing rime fog", "🌫️", "#94A3B8"),
    51: ("Light drizzle", "🌦️", "#60A5FA"),
    53: ("Moderate drizzle", "🌦️", "#3B82F6"),
    55: ("Dense drizzle", "🌧️", "#2563EB"),
    56: ("Light freezing drizzle", "🌨️", "#93C5FD"),
    57: ("Dense freezing drizzle", "🌨️", "#60A5FA"),
    61: ("Slight rain", "🌧️", "#60A5FA"),
    63: ("Moderate rain", "🌧️", "#3B82F6"),
    65: ("Heavy rain", "🌧️", "#1D4ED8"),
    66: ("Light freezing rain", "🌨️", "#93C5FD"),
    67: ("Heavy freezing rain", "🌨️", "#60A5FA"),
    71: ("Slight snowfall", "❄️", "#7DD3FC"),
    73: ("Moderate snowfall", "❄️", "#38BDF8"),
    75: ("Heavy snowfall", "❄️", "#0284C7"),
    77: ("Snow grains", "❄️", "#7DD3FC"),
    80: ("Slight rain showers", "🌦️", "#60A5FA"),
    81: ("Moderate rain showers", "🌧️", "#3B82F6"),
    82: ("Violent rain showers", "⛈️", "#6366F1"),
    85: ("Slight snow showers", "🌨️", "#7DD3FC"),
    86: ("Heavy snow showers", "🌨️", "#38BDF8"),
    95: ("Thunderstorm", "⛈️", "#A855F7"),
    96: ("Thunderstorm with hail", "⛈️⚡", "#C084FC"),
    99: ("Severe thunderstorm", "⛈️⚡", "#9333EA"),
}

def get_wmo_info(code):
    if code is None:
        return ("Variable Conditions", "⛅", "#94A3B8")
    return WMO_WEATHER_MAP.get(int(code), ("Variable Conditions", "⛅", "#94A3B8"))

# -----------------------------------------------------------------------------
# PulseTrack Dark Canvas & High-Contrast Design System
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    /* Global Canvas Styling matching screenshot */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #070913 !important;
        background-image: 
            radial-gradient(circle at 12% 18%, rgba(99, 102, 241, 0.14) 0%, transparent 35%),
            radial-gradient(circle at 88% 78%, rgba(168, 85, 247, 0.12) 0%, transparent 40%),
            radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 0.6) 0%, transparent 100%) !important;
        background-attachment: fixed !important;
        color: #F8FAFC !important;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: transparent !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0A0D18 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Force all text inside sidebar to be fully bright and readable */
    [data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 3rem !important;
        max-width: 1240px !important;
    }

    /* Top Navigation Header (matching PulseTrack top bar) */
    .pulsetrack-nav {
        background: rgba(13, 18, 36, 0.85);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }

    .nav-brand-box {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .logo-icon {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
    }
    
    .nav-title {
        color: #FFFFFF !important;
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.025em;
    }

    .nav-tag {
        display: inline-block;
        background: rgba(99, 102, 241, 0.18);
        border: 1px solid rgba(99, 102, 241, 0.35);
        color: #C7D2FE !important;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-left: 0.5rem;
    }
    
    .nav-sub-text {
        color: #94A3B8 !important;
        font-size: 0.8rem;
        margin-top: 0.15rem;
    }

    .nav-pills {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }

    .status-pill-live {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.75rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #6EE7B7 !important;
    }

    .status-pill-purple {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.75rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(139, 92, 246, 0.15);
        border: 1px solid rgba(139, 92, 246, 0.3);
        color: #D8B4FE !important;
    }

    .dot-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 10px #10B981;
    }

    /* Hero Heading matching image */
    .hero-container {
        margin-bottom: 1.5rem;
    }

    .hero-badge-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #A5B4FC !important;
        padding: 0.3rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    .hero-heading {
        font-size: 2.2rem;
        font-weight: 800;
        color: #FFFFFF !important;
        letter-spacing: -0.03em;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }

    .gradient-highlight {
        background: linear-gradient(90deg, #60A5FA 0%, #34D399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-sub {
        color: #94A3B8 !important;
        font-size: 0.95rem;
        max-width: 800px;
        line-height: 1.5;
        margin-bottom: 1.5rem;
    }

    /* Dark Panel Cards (matching Reviewer Quick-Start) */
    .dark-card {
        background: rgba(13, 18, 36, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 4px 20px -5px rgba(0, 0, 0, 0.4);
        margin-bottom: 1rem;
    }

    .quick-start-box {
        background: rgba(13, 18, 36, 0.75);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }

    .quick-start-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .quick-start-title {
        color: #F8FAFC !important;
        font-weight: 700;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .role-badge {
        font-size: 0.68rem;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .role-CRITICAL { background: #581C87; color: #E9D5FF !important; border: 1px solid #7E22CE; }
    .role-HIGH { background: #7C2D12; color: #FED7AA !important; border: 1px solid #C2410C; }
    .role-MODERATE { background: #713F12; color: #FEF08A !important; border: 1px solid #A16207; }
    .role-LOW { background: #064E3B; color: #A7F3D0 !important; border: 1px solid #059669; }

    /* Telemetry Metric Tile */
    .dark-metric-tile {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1rem 1.1rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }

    .dark-metric-tile:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-2px);
    }

    .dark-metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .dark-metric-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #FFFFFF !important;
        margin-top: 0.3rem;
    }

    .dark-metric-sub {
        font-size: 0.75rem;
        color: #64748B !important;
        margin-top: 0.2rem;
    }

    /* Primary Gradient Button (matching Register Account & Sign In button) */
    .stButton > button {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
        transform: translateY(-1px) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
    }

    /* Chat Messages styling */
    [data-testid="stChatMessage"] {
        background-color: rgba(13, 18, 36, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 1rem 1.25rem !important;
        margin-bottom: 0.85rem !important;
    }

    [data-testid="stChatMessage"] * {
        color: #F8FAFC !important;
    }

    /* Chat Input */
    [data-testid="stChatInput"] textarea {
        background-color: #0E1322 !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
    }

    /* Expanders & Tabs */
    .streamlit-expanderHeader {
        background-color: rgba(15, 23, 42, 0.6) !important;
        color: #F8FAFC !important;
        border-radius: 8px !important;
    }

    [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    [data-baseweb="tab"] {
        color: #94A3B8 !important;
    }

    [aria-selected="true"] {
        color: #818CF8 !important;
        font-weight: 700 !important;
    }

    /* Severity Banners */
    .sop-banner-CRITICAL {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.2) 0%, rgba(239, 68, 68, 0.05) 100%);
        border-left: 4px solid #EF4444;
        border-top: 1px solid rgba(239, 68, 68, 0.35);
        border-right: 1px solid rgba(239, 68, 68, 0.2);
        border-bottom: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin: 0.75rem 0;
    }
    
    .sop-banner-HIGH {
        background: linear-gradient(90deg, rgba(249, 115, 22, 0.2) 0%, rgba(249, 115, 22, 0.05) 100%);
        border-left: 4px solid #F97316;
        border-top: 1px solid rgba(249, 115, 22, 0.35);
        border-right: 1px solid rgba(249, 115, 22, 0.2);
        border-bottom: 1px solid rgba(249, 115, 22, 0.2);
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin: 0.75rem 0;
    }

    .sop-banner-MODERATE {
        background: linear-gradient(90deg, rgba(234, 179, 8, 0.2) 0%, rgba(234, 179, 8, 0.05) 100%);
        border-left: 4px solid #EAB308;
        border-top: 1px solid rgba(234, 179, 8, 0.35);
        border-right: 1px solid rgba(234, 179, 8, 0.2);
        border-bottom: 1px solid rgba(234, 179, 8, 0.2);
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin: 0.75rem 0;
    }

    .sop-banner-LOW {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.05) 100%);
        border-left: 4px solid #10B981;
        border-top: 1px solid rgba(16, 185, 129, 0.35);
        border-right: 1px solid rgba(16, 185, 129, 0.2);
        border-bottom: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin: 0.75rem 0;
    }

    /* Pipeline tracker row */
    .pipe-step-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        font-size: 0.8rem;
        margin-bottom: 0.4rem;
        color: #94A3B8 !important;
    }
    
    .pipe-step-row.completed {
        border-color: rgba(16, 185, 129, 0.4);
        background: rgba(16, 185, 129, 0.08);
        color: #F8FAFC !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Top Navigation Header
# -----------------------------------------------------------------------------
all_sops = sop_engine.get_all_sops()
current_state = st.session_state.agent_state
weather = current_state.get("weather_data")
selected_sop = current_state.get("selected_sop")
coords = current_state.get("coordinates")
status = current_state.get("execution_status", "READY")

st.markdown(f"""
<div class="pulsetrack-nav">
    <div class="nav-brand-box">
        <div class="logo-icon">🛡️</div>
        <div>
            <div style="display:flex; align-items:center;">
                <span class="nav-title">AERO-GUARD</span>
                <span class="nav-tag">ENTERPRISE SAFETY AI</span>
            </div>
            <div class="nav-sub-text">Autonomous LangGraph Decision Engine • Live Open-Meteo Telemetry</div>
        </div>
    </div>
    <div class="nav-pills">
        <div class="status-pill-live">
            <span class="dot-pulse"></span>
            <span>SYSTEM ONLINE</span>
        </div>
        <div class="status-pill-purple">
            <span>📚 {len(all_sops)} POLICIES LOADED</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Hero Title Section
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div class="hero-badge-tag">⚡ SOP POLICY & METEOROLOGY ENGINE</div>
    <div class="hero-heading">Autonomous Weather Safety & <span class="gradient-highlight">Policy Decision System</span></div>
    <div class="hero-sub">
        Enterprise-grade outdoor risk verification grounded strictly in corporate Standard Operating Procedures (SOPs) and real-time Open-Meteo meteorological telemetry.
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Sidebar: Control Panel & Knowledge Base
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Control Panel")
    
    col_r, col_c = st.columns(2)
    with col_r:
        if st.button("🔄 New Session", use_container_width=True):
            reset_session()
            st.rerun()
    with col_c:
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.divider()

    tab_telem, tab_sops, tab_trace = st.tabs([
        "📡 Telemetry", 
        "📚 SOP Policies", 
        "🔍 Pipeline Trace"
    ])

    # ------------------ TAB 1: TELEMETRY ------------------
    with tab_telem:
        if weather and coords:
            wcode = weather.get("weather_code", 0)
            desc, icon, color = get_wmo_info(wcode)
            
            st.markdown(f"""
            <div style="background:rgba(15, 23, 42, 0.85); border-radius:10px; padding:12px; border:1px solid rgba(255, 255, 255, 0.08); margin-bottom:12px;">
                <div style="font-size:0.72rem; color:#94A3B8; text-transform:uppercase; font-weight:600;">Active Location</div>
                <div style="font-size:1.1rem; color:#FFFFFF; font-weight:700; margin-top:2px;">
                    📍 {coords.get('name')}, {coords.get('country')}
                </div>
                <div style="font-size:0.75rem; color:#64748B;">
                    Lat: {coords.get('latitude'):.3f}° | Lon: {coords.get('longitude'):.3f}° | {coords.get('timezone', 'UTC')}
                </div>
                <div style="margin-top:8px; display:flex; align-items:center; gap:6px;">
                    <span style="font-size:1.2rem;">{icon}</span>
                    <span style="font-size:0.85rem; font-weight:600; color:{color};">{desc}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Temperature", f"{weather.get('temperature_2m')} °C", f"Feels {weather.get('apparent_temperature')} °C")
                st.metric("Wind Speed", f"{weather.get('wind_speed_10m')} km/h", f"Gusts: {weather.get('wind_gusts_10m')} km/h")
            with c2:
                st.metric("Precipitation", f"{weather.get('precipitation')} mm", f"{weather.get('precipitation_probability')}% PoP")
                uv_val = weather.get('uv_index', 0.0)
                uv_tier = "Extreme" if uv_val >= 11 else "Very High" if uv_val >= 8 else "High" if uv_val >= 6 else "Moderate" if uv_val >= 3 else "Low"
                st.metric("UV Index", f"{uv_val}", f"{uv_tier}")

            if selected_sop:
                st.divider()
                sev = selected_sop.get("severity", "LOW")
                st.markdown(f"""
                <div class="sop-banner-{sev}">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span class="role-badge role-{sev}">{sev} RISK</span>
                        <span style="font-size:0.75rem; font-family:monospace; color:#CBD5E1;">{selected_sop['id']}</span>
                    </div>
                    <div style="font-weight:700; color:#FFFFFF; font-size:0.95rem;">{selected_sop['title']}</div>
                    <div style="font-size:0.8rem; color:#CBD5E1; margin-top:4px;">{selected_sop['rationale']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("📋 View Mandatory Guidance"):
                    for g in selected_sop.get("mandatory_guidance", []):
                        st.markdown(f"• {g}")

                if current_state.get("secondary_sops"):
                    st.caption(f"**Secondary Policies Matched**: {len(current_state.get('secondary_sops'))}")
                    for sec in current_state.get("secondary_sops"):
                        st.caption(f"- `{sec['id']}` {sec['title']} ({sec['severity']})")

                if current_state.get("conflict_resolution_rationale"):
                    st.info(f"**Conflict Logic**: {current_state.get('conflict_resolution_rationale')}")
        else:
            st.info("💡 Submit a query to inspect live weather metrics & governing policy evaluation.")

    # ------------------ TAB 2: SOP LIBRARY ------------------
    with tab_sops:
        st.markdown(f"**Corporate Safety Policies** (`{len(all_sops)}` registered)")
        
        search_kw = st.text_input("🔍 Search policies", placeholder="e.g. wind, rain, heat, cycling...", label_visibility="collapsed")
        severity_filter = st.selectbox("Filter by Severity", ["All Severities", "CRITICAL", "HIGH", "MODERATE", "LOW"])
        
        filtered = all_sops
        if severity_filter != "All Severities":
            filtered = [s for s in filtered if s.get("severity") == severity_filter]
        if search_kw:
            kw = search_kw.lower()
            filtered = [s for s in filtered if kw in s.get("id", "").lower() or kw in s.get("title", "").lower() or kw in s.get("rationale", "").lower() or any(kw in a.lower() for a in s.get("applicable_activities", []))]

        st.caption(f"Showing {len(filtered)} matching policies:")
        for p in filtered:
            sev = p.get("severity", "LOW")
            with st.expander(f"{p['id']} • {p['title']} [{sev}]"):
                st.markdown(f"**Category**: `{p.get('category')}`")
                st.markdown(f"**Severity**: <span class='role-badge role-{sev}'>{sev}</span>", unsafe_allow_html=True)
                if p.get("situational_override"):
                    st.warning("⚡ **Situational Override Policy** (Takes precedence over single activities)")
                st.markdown(f"**Applicable Activities**: `{', '.join(p.get('applicable_activities', []))}`")
                st.markdown(f"**Conditions Required**:")
                for k, v in p.get("conditions", {}).items():
                    st.markdown(f"- `{k}`: `{v}`")
                st.markdown(f"**Rationale**: {p.get('rationale')}")
                st.markdown("**Mandatory Directives**:")
                for d in p.get("mandatory_guidance", []):
                    st.markdown(f"- {d}")

    # ------------------ TAB 3: PIPELINE TRACE ------------------
    with tab_trace:
        st.markdown("**LangGraph State Machine Steps**")
        
        steps = [
            ("1. Intent & Context Extraction", bool(current_state.get("extracted_location"))),
            ("2. Open-Meteo Telemetry Lookup", bool(current_state.get("weather_data"))),
            ("3. SOP Condition Evaluation", bool(current_state.get("matched_sops"))),
            ("4. Conflict Resolution Logic", bool(current_state.get("selected_sop"))),
            ("5. Grounded Safety Synthesis", bool(current_state.get("final_answer"))),
        ]
        
        for name, is_done in steps:
            cls = "pipe-step-row completed" if is_done else "pipe-step-row"
            icon = "✅" if is_done else "⚪"
            st.markdown(f"""
            <div class="{cls}">
                <span>{icon}</span>
                <span>{name}</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("**State Inspector**")
        with st.expander("View Raw Agent State JSON"):
            clean_state = {k: v for k, v in current_state.items() if k != "messages"}
            st.json(clean_state)

# -----------------------------------------------------------------------------
# Main Screen: Reviewer Quick-Start Scenarios (matching screenshot)
# -----------------------------------------------------------------------------
st.markdown("""
<div class="quick-start-box">
    <div class="quick-start-header">
        <div class="quick-start-title">
            <span>⚡</span> REVIEWER QUICK-START (1-CLICK SAFETY AUDITS)
        </div>
        <div style="font-size:0.75rem; color:#94A3B8; text-transform:uppercase; letter-spacing:0.04em;">
            CLICK ANY SCENARIO TO TEST INSTANTLY
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

p_cols = st.columns(4)
sample_query = None

with p_cols[0]:
    if st.button("🌧️ **Bhopal Monsoon**\n\nBike in heavy rain\n*Test SOP-SYS-001*", use_container_width=True):
        sample_query = "Is it safe to bike to work in Bhopal today?"
with p_cols[1]:
    if st.button("☀️ **Madrid Midday Run**\n\nSolar UV & Heat index\n*Test SOP-EX-002*", use_container_width=True):
        sample_query = "Should I go for an outdoor midday run in Madrid today?"
with p_cols[2]:
    if st.button("🧺 **London Lawn Picnic**\n\nOpen-air brunch\n*Test SOP-LEIS-001*", use_container_width=True):
        sample_query = "Planning an open-air family brunch with a blanket on the lawn in London, is today a good day?"
with p_cols[3]:
    if st.button("♟️ **Paris Indoor Chess**\n\nBasement boundary check\n*Test No-Match Rule*", use_container_width=True):
        sample_query = "Is it safe to play indoor chess in my basement in Paris today?"

# Live Weather Dashboard Card if active
if weather and coords:
    wcode = weather.get("weather_code", 0)
    desc, icon, color = get_wmo_info(wcode)
    
    st.markdown(f"""
    <div class="dark-card" style="margin-top:1.5rem; margin-bottom:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.5rem;">{icon}</span>
                <div>
                    <span style="font-size:1.15rem; font-weight:700; color:#FFFFFF;">{coords.get('name')}, {coords.get('country')}</span>
                    <span style="font-size:0.8rem; color:#94A3B8; margin-left:8px;">Verified Open-Meteo Telemetry</span>
                </div>
            </div>
            <div style="font-size:0.85rem; font-weight:600; color:{color}; background:rgba(255,255,255,0.06); padding:4px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.1);">
                {desc}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(f"""
        <div class="dark-metric-tile">
            <div class="dark-metric-label">🌡️ Temperature</div>
            <div class="dark-metric-value">{weather.get('temperature_2m')} °C</div>
            <div class="dark-metric-sub">Feels: {weather.get('apparent_temperature')} °C • Humidity: {weather.get('relative_humidity_2m')}%</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
        <div class="dark-metric-tile">
            <div class="dark-metric-label">💨 Wind Dynamics</div>
            <div class="dark-metric-value">{weather.get('wind_speed_10m')} <span style="font-size:0.9rem; font-weight:500;">km/h</span></div>
            <div class="dark-metric-sub">Peak Gusts: {weather.get('wind_gusts_10m')} km/h</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        st.markdown(f"""
        <div class="dark-metric-tile">
            <div class="dark-metric-label">🌧️ Precipitation</div>
            <div class="dark-metric-value">{weather.get('precipitation')} <span style="font-size:0.9rem; font-weight:500;">mm/h</span></div>
            <div class="dark-metric-sub">Probability: {weather.get('precipitation_probability')}% • Daily: {weather.get('daily_precipitation_sum')}mm</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col4:
        uv_val = weather.get('uv_index', 0.0)
        uv_tier = "Extreme" if uv_val >= 11 else "Very High" if uv_val >= 8 else "High" if uv_val >= 6 else "Moderate" if uv_val >= 3 else "Low"
        st.markdown(f"""
        <div class="dark-metric-tile">
            <div class="dark-metric-label">☀️ UV Radiation</div>
            <div class="dark-metric-value">{uv_val} <span style="font-size:0.9rem; font-weight:500;">Index</span></div>
            <div class="dark-metric-sub">Rating: <b style="color:#FFFFFF;">{uv_tier}</b></div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Conversational Feed & Grounded Assistant Stream
# -----------------------------------------------------------------------------
if not st.session_state.messages:
    st.markdown("""
    <div style="text-align:center; padding: 2.25rem 1rem; background: rgba(13, 18, 36, 0.6); border-radius: 14px; border: 1px dashed rgba(255, 255, 255, 0.1); margin: 1.5rem 0;">
        <div style="font-size: 2.2rem; margin-bottom: 0.4rem;">🌦️ 🛡️</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #FFFFFF;">AERO-GUARD Safety Machine Ready</div>
        <div style="font-size: 0.9rem; color: #94A3B8; max-width: 600px; margin: 0.4rem auto 1.25rem auto;">
            Inquire about outdoor safety for any city. The engine verifies live Open-Meteo meteorological telemetry and applies strictly governed Standard Operating Procedures (SOPs).
        </div>
        <div style="display:inline-flex; gap:0.5rem; flex-wrap:wrap; justify-content:center;">
            <span class="status-pill-purple">🔒 Deterministic SOP Matching</span>
            <span class="status-pill-live">🌐 Open-Meteo Live API</span>
            <span class="status-pill-purple">🛡️ Prompt Injection Defense</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🛡️"):
        st.markdown(msg["content"])

# User Input Processing
user_input = st.chat_input("Ask about outdoor activity safety (e.g. 'Is it safe to cycle in Bhopal today?')...") or sample_query

if user_input:
    # 1. Append User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # 2. Prepare Agent State with conversational memory
    agent_state = st.session_state.agent_state
    agent_state["messages"] = st.session_state.messages

    # 3. Execute LangGraph Pipeline
    with st.chat_message("assistant", avatar="🛡️"):
        with st.status("⚡ **Evaluating Safety Policies**...", expanded=True) as status_box:
            st.write("🔍 Resolving location & activity intent...")
            result = graph.invoke(agent_state)
            st.write("📡 Fetching Open-Meteo meteorological telemetry...")
            st.write("🛡️ Evaluating corporate Standard Operating Procedures (SOPs)...")
            st.write("📋 Synthesizing grounded compliance directives...")
            status_box.update(label="✅ **Safety Advisory Formulated**", state="complete", expanded=False)
            
            # Update state with execution results
            st.session_state.agent_state = result
            answer = result.get("final_answer", "No response generated.")
            
            # Display answer
            st.markdown(answer)
            
            # Append Assistant Message
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
            # Refresh to update sidebar telemetry and metrics
            st.rerun()




