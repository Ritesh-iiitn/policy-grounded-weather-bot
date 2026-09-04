from typing import Dict, Any, List
from src.state import AgentState
from src.llm import intent_extractor, get_llm
from src.weather import weather_client
from src.sop_engine import sop_engine

def extract_intent_and_context(state: AgentState) -> Dict[str, Any]:
    """Node 1: Extracts intent, location, activity, and handles multi-turn memory."""
    messages = state.get("messages", [])
    if not messages:
        return {"execution_status": "CLARIFICATION_NEEDED", "final_answer": "How can I assist you with weather safety today?"}

    latest_msg = messages[-1]
    prompt = latest_msg.get("content", "")
    
    existing_loc = state.get("extracted_location")
    existing_act = state.get("extracted_activity")
    
    extracted = intent_extractor.extract(
        current_prompt=prompt,
        history=messages[:-1],
        existing_location=existing_loc,
        existing_activity=existing_act
    )
    
    if extracted.is_adversarial:
        return {
            "execution_status": "ADVERSARIAL_REJECTED",
            "extracted_location": extracted.location or existing_loc,
            "extracted_activity": extracted.activity or existing_act,
            "target_time_window": extracted.time_window
        }
        
    if not extracted.location:
        return {
            "execution_status": "NO_LOCATION",
            "extracted_activity": extracted.activity,
            "target_time_window": extracted.time_window
        }
        
    return {
        "extracted_location": extracted.location,
        "extracted_activity": extracted.activity,
        "target_time_window": extracted.time_window,
        "execution_status": "IN_PROGRESS"
    }

def fetch_weather(state: AgentState) -> Dict[str, Any]:
    """Node 2: Fetches live weather data from Open-Meteo API."""
    loc = state.get("extracted_location")
    if not loc:
        return {"execution_status": "NO_LOCATION", "weather_error_msg": "Location is missing."}
        
    loc_meta, weather_data, error = weather_client.get_live_weather(loc)
    if error or not weather_data:
        return {
            "execution_status": "WEATHER_FETCH_FAILED",
            "weather_error_msg": error or f"Unable to retrieve live forecast for {loc}."
        }
        
    return {
        "coordinates": loc_meta,
        "weather_data": weather_data,
        "weather_error_msg": None,
        "execution_status": "IN_PROGRESS"
    }

def evaluate_sops(state: AgentState) -> Dict[str, Any]:
    """Node 3: Evaluates SOP rules against live weather metrics and user activity."""
    weather = state.get("weather_data")
    activity = state.get("extracted_activity")
    
    if not weather:
        return {"execution_status": "WEATHER_FETCH_FAILED", "matched_sops": []}
        
    matched = sop_engine.evaluate(weather=weather, user_activity=activity)
    return {
        "matched_sops": matched,
        "execution_status": "IN_PROGRESS"
    }

def resolve_sop_conflicts(state: AgentState) -> Dict[str, Any]:
    """Node 4: Resolves conflicts when multiple SOPs match using severity and situational overrides."""
    matched = state.get("matched_sops", [])
    if not matched:
        return {
            "selected_sop": None,
            "secondary_sops": [],
            "conflict_resolution_rationale": "No SOP conditions were met.",
            "execution_status": "NO_SOP_MATCH"
        }
        
    primary, secondaries, rationale = sop_engine.resolve_conflicts(matched)
    return {
        "selected_sop": primary,
        "secondary_sops": secondaries,
        "conflict_resolution_rationale": rationale,
        "execution_status": "SUCCESS"
    }

def synthesize_grounded_response(state: AgentState) -> Dict[str, Any]:
    """Node 5: Formulates policy-grounded response citing exact SOP ID and API weather numbers."""
    selected_sop = state.get("selected_sop")
    secondary_sops = state.get("secondary_sops", [])
    weather = state.get("weather_data", {})
    loc_meta = state.get("coordinates", {})
    activity = state.get("extracted_activity", "outdoor activity")
    
    location_name = loc_meta.get("name") if loc_meta else state.get("extracted_location", "the requested area")
    admin1 = loc_meta.get("admin1", "")
    country = loc_meta.get("country", "")
    full_loc_str = f"{location_name}, {admin1}, {country}".strip(", ")

    # Verified weather metrics
    temp = weather.get("temperature_2m")
    wind = weather.get("wind_speed_10m")
    gusts = weather.get("wind_gusts_10m")
    precip = weather.get("precipitation")
    pop = weather.get("precipitation_probability")
    uv = weather.get("uv_index")
    wcode = weather.get("weather_code")

    guidance_points = selected_sop.get("mandatory_guidance", [])
    guidance_bullets = "\n".join([f"- {g}" for g in guidance_points])
    
    secondary_notes = ""
    if secondary_sops:
        sec_ids = ", ".join([f"`{s['id']}` ({s['title']})" for s in secondary_sops])
        secondary_notes = f"\n\n**Additional Applicable Policies**: {sec_ids}"

    llm = get_llm()
    if llm:
        try:
            prompt = f"""You are the Weather Safety Advisory Bot. You must generate a safety response strictly grounded in the provided Standard Operating Procedure (SOP) and exact live weather metrics.
DO NOT invent any safety advice, severity levels, or numbers. Every factual number and policy point must come directly from below.

POLICY INFORMATION:
- SOP ID: {selected_sop['id']}
- Policy Title: {selected_sop['title']}
- Category: {selected_sop['category']}
- Severity Level: {selected_sop['severity']}
- Mandatory Guidance Points:
{guidance_bullets}

LIVE WEATHER TELEMETRY (Open-Meteo verified for {full_loc_str}):
- Temperature: {temp}°C
- Precipitation: {precip} mm/h
- Precipitation Probability: {pop}%
- Wind Speed: {wind} km/h (Gusts: {gusts} km/h)
- UV Index: {uv}
- Weather Code: {wcode}

USER ACTIVITY: {activity}
LOCATION: {full_loc_str}

REQUIRED RESPONSE STRUCTURE:
1. Lead directly with the severity rating and whether the activity is recommended or advised against.
2. Explicitly cite the governing policy by ID (`{selected_sop['id']}`) and Title.
3. Cite the exact relevant live weather numbers from above that triggered this policy.
4. Provide the mandatory guidance points clearly and professionally.
5. End with policy traceability note."""

            response = llm.invoke(prompt)
            final_text = response.content if hasattr(response, "content") else str(response)
            return {"final_answer": final_text, "execution_status": "SUCCESS"}
        except Exception:
            pass

    # Deterministic Grounded Template Fallback
    severity_badge = f"**[{selected_sop.get('severity', 'ADVISORY')} SEVERITY]**"
    
    response_lines = [
        f"### {severity_badge} Weather Safety Advisory for {activity.capitalize()} in {full_loc_str}",
        f"\n**Governing Policy**: `{selected_sop['id']}` — *{selected_sop['title']}*",
        f"**Risk Severity**: `{selected_sop.get('severity')}`",
        f"\n**Live Verified Weather Data ({full_loc_str})**:",
        f"- **Temperature**: {temp}°C",
        f"- **Precipitation**: {precip} mm (Probability: {pop}%)",
        f"- **Wind Speed**: {wind} km/h (Gusts: {gusts} km/h)",
        f"- **UV Index**: {uv}",
        f"\n**Mandated Safety Guidance**:",
        guidance_bullets,
        secondary_notes,
        f"\n\n*Traceability: This advisory was generated strictly under corporate SOP `{selected_sop['id']}` based on live Open-Meteo telemetry.*"
    ]
    
    return {"final_answer": "\n".join(response_lines), "execution_status": "SUCCESS"}

def ask_clarification(state: AgentState) -> Dict[str, Any]:
    """Fallback Node: Requests missing location or parameters."""
    act = state.get("extracted_activity")
    if not state.get("extracted_location"):
        if act:
            msg = f"I see you are inquiring about safety for **{act}**. Could you please specify which city or location you're planning this for?"
        else:
            msg = "Could you please specify your location (city name) and the outdoor activity you're planning, so I can check our safety policies against live weather data?"
    else:
        msg = "Could you clarify what outdoor activity you are planning?"
        
    return {"final_answer": msg, "execution_status": "CLARIFICATION_NEEDED"}

def handle_weather_error(state: AgentState) -> Dict[str, Any]:
    """Fallback Node: Honest failure reporting for unreachable weather API or unknown location."""
    err = state.get("weather_error_msg") or "Unable to retrieve weather data."
    loc = state.get("extracted_location", "the requested location")
    msg = (
        f"⚠️ **Weather Data Unavailable**: I could not retrieve live weather information for **{loc}**.\n\n"
        f"**Reason**: {err}\n\n"
        f"As our safety policy requires strictly grounded live meteorological data, I cannot provide safety advice without verified current readings. Please verify the city name or try again shortly."
    )
    return {"final_answer": msg, "execution_status": "WEATHER_FETCH_FAILED"}

def handle_no_sop_match(state: AgentState) -> Dict[str, Any]:
    """Fallback Node: Honest reporting when no SOP covers the query."""
    act = state.get("extracted_activity", "this activity")
    loc = state.get("extracted_location", "your area")
    weather = state.get("weather_data", {})
    temp = weather.get("temperature_2m", "N/A")
    precip = weather.get("precipitation", "N/A")
    wind = weather.get("wind_speed_10m", "N/A")
    
    msg = (
        f"ℹ️ **No Governing SOP Found**: We currently do not have an established Standard Operating Procedure (SOP) "
        f"for **{act}** under the current environmental conditions in **{loc}**.\n\n"
        f"**Current Verified Weather Readings**:\n"
        f"- Temperature: {temp}°C\n"
        f"- Precipitation: {precip} mm\n"
        f"- Wind Speed: {wind} km/h\n\n"
        f"Our policy strictly forbids generating improvised safety advice. We recommend consulting local municipal guidelines."
    )
    return {"final_answer": msg, "execution_status": "NO_SOP_MATCH"}

def handle_adversarial(state: AgentState) -> Dict[str, Any]:
    """Fallback Node: Rejects jailbreak or policy bypass attempts."""
    msg = (
        f"🛡️ **Policy Protection Triggered**: I am programmed to provide outdoor safety recommendations "
        f"strictly grounded in verified Standard Operating Procedures (SOPs) and live meteorological data.\n\n"
        f"I cannot bypass safety guidelines, fabricate safety assurances, or provide ungrounded advice. "
        f"Please ask a standard question regarding outdoor safety for your city."
    )
    return {"final_answer": msg, "execution_status": "ADVERSARIAL_REJECTED"}
