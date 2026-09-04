from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ExtractedEntities(BaseModel):
    location: Optional[str] = Field(None, description="Resolved city or region name")
    activity: Optional[str] = Field(None, description="Outdoor activity, e.g. cycling, running, picnic, travel, walking dog")
    time_window: Optional[str] = Field("current", description="Time window: current, evening, tomorrow, etc.")
    is_adversarial: bool = Field(False, description="Flag if query attempts prompt injection or safety bypass")

class AgentState(TypedDict, total=False):
    # Chat session & conversation history
    messages: List[Dict[str, Any]]
    session_id: str
    
    # Extracted / Resolved contextual entities
    extracted_location: Optional[str]
    coordinates: Optional[Dict[str, Any]] # {"lat": float, "lon": float, "name": str, "country": str}
    extracted_activity: Optional[str]
    target_time_window: Optional[str]
    
    # Real weather data payload from Open-Meteo
    weather_data: Optional[Dict[str, Any]]
    weather_error_msg: Optional[str]
    
    # SOP Policy Evaluation & Conflict Resolution
    matched_sops: List[Dict[str, Any]]
    selected_sop: Optional[Dict[str, Any]]
    secondary_sops: List[Dict[str, Any]]
    conflict_resolution_rationale: Optional[str]
    
    # Final Output & State Tracking
    execution_status: str # "SUCCESS", "NO_LOCATION", "WEATHER_FETCH_FAILED", "NO_SOP_MATCH", "CLARIFICATION_NEEDED", "ADVERSARIAL_REJECTED"
    final_answer: str
