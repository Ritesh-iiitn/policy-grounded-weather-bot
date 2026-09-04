import streamlit as st
import json
import yaml
from pathlib import Path
from src.graph import graph
from src.sop_engine import sop_engine
from src.config import SOPS_PATH

st.set_page_config(
    page_title="Weather Safety Advisory Assistant",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #3B82F6;
        margin-bottom: 10px;
    }
    .sop-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-CRITICAL { background-color: #FEE2E2; color: #991B1B; border: 1px solid #F87171; }
    .badge-HIGH { background-color: #FFEDD5; color: #9A3412; border: 1px solid #FB923C; }
    .badge-MODERATE { background-color: #FEF9C3; color: #854D0E; border: 1px solid #FACC15; }
    .badge-LOW { background-color: #DCFCE7; color: #166534; border: 1px solid #4ADE80; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_state" not in st.session_state:
    st.session_state.agent_state = {
        "messages": [],
        "session_id": "streamlit-session-01",
        "extracted_location": None,
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
        "session_id": "streamlit-session-01",
        "extracted_location": None,
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

# Top Header
st.markdown('<div class="main-header">🌦️ Policy-Governed Weather Advisory Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">LangGraph Agent backed by live Open-Meteo data & strictly enforced Standard Operating Procedures (SOPs).</div>', unsafe_allow_html=True)

# Sidebar: Audit Telemetry & SOP Inspector
with st.sidebar:
    st.header("⚙️ Session & Diagnostics")
    if st.button("🔄 Reset Conversation / Clear Memory", use_container_width=True):
        reset_session()
        st.rerun()

    st.divider()
    
    # 1. Live Weather Telemetry & Policy Audit
    st.subheader("📡 Live Telemetry & Audit")
    current_state = st.session_state.agent_state
    weather = current_state.get("weather_data")
    selected_sop = current_state.get("selected_sop")
    coords = current_state.get("coordinates")
    
    if weather and coords:
        st.success(f"📍 **{coords.get('name')}, {coords.get('country')}** ({coords.get('latitude'):.2f}, {coords.get('longitude'):.2f})")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Temperature", f"{weather.get('temperature_2m')} °C")
            st.metric("Wind Speed", f"{weather.get('wind_speed_10m')} km/h")
        with col2:
            st.metric("Precipitation", f"{weather.get('precipitation')} mm")
            st.metric("UV Index", f"{weather.get('uv_index')}")
        
        st.caption(f"Precipitation Probability: **{weather.get('precipitation_probability')}%** | Gusts: **{weather.get('wind_gusts_10m')} km/h**")
    else:
        st.info("No active weather telemetry for this turn yet. Ask a query to inspect live API metrics.")

    if selected_sop:
        st.markdown("#### 🛡️ Governing Policy Audit")
        sev = selected_sop.get("severity", "LOW")
        st.markdown(f"<span class='sop-badge badge-{sev}'>{sev} SEVERITY</span> **{selected_sop['id']}**", unsafe_allow_html=True)
        st.write(f"*{selected_sop['title']}*")
        with st.expander("View Policy Details & Rationale"):
            st.write(f"**Category:** `{selected_sop['category']}`")
            st.write(f"**Rationale:** {selected_sop['rationale']}")
            st.write("**Mandatory Guidance:**")
            for g in selected_sop.get("mandatory_guidance", []):
                st.write(f"- {g}")
            if current_state.get("conflict_resolution_rationale"):
                st.info(f"**Conflict Resolution:** {current_state.get('conflict_resolution_rationale')}")

    st.divider()

    # 2. Live SOP Policy Library
    st.subheader("📚 Active SOP Policy Library")
    all_sops = sop_engine.get_all_sops()
    st.caption(f"Currently loaded: **{len(all_sops)} policies** directly from `data/sops.yaml`.")
    
    with st.expander("Browse All SOP Policies"):
        for p in all_sops:
            st.markdown(f"**{p['id']}** — *{p['title']}* (`{p['severity']}`)")
            st.caption(f"Activities: {p.get('applicable_activities')}")
            st.divider()

# Quick Starter Buttons
st.markdown("##### 💡 Try Sample Queries:")
q_cols = st.columns(4)
sample_query = None

if q_cols[0].button("🚲 Bike in Bhopal (Live)", use_container_width=True):
    sample_query = "Is it safe to bike to work in Bhopal today?"
if q_cols[1].button("🏃 Noon Run in Madrid", use_container_width=True):
    sample_query = "Should I go for an outdoor midday run in Madrid today?"
if q_cols[2].button("🧺 Lawn Picnic in London", use_container_width=True):
    sample_query = "Planning an open-air family brunch with a blanket on the lawn in London, is today a good day?"
if q_cols[3].button("♟️ Basement Chess (Paris)", use_container_width=True):
    sample_query = "Is it safe to play indoor chess in my basement in Paris today?"

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input Processing
user_input = st.chat_input("Ask about outdoor activity safety (e.g. 'Is it safe to cycle in Bhopal today?')...") or sample_query

if user_input:
    # 1. Append User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Prepare Agent State with conversational memory
    agent_state = st.session_state.agent_state
    agent_state["messages"] = st.session_state.messages

    # 3. Execute LangGraph Pipeline
    with st.chat_message("assistant"):
        with st.spinner("Analyzing intent, fetching live Open-Meteo weather, and verifying SOP policies..."):
            result = graph.invoke(agent_state)
            
            # Update state with execution results
            st.session_state.agent_state = result
            answer = result.get("final_answer", "No response generated.")
            
            # Display answer
            st.markdown(answer)
            
            # Append Assistant Message
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
            # Refresh sidebar telemetry
            st.rerun()
