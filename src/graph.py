from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes import (
    extract_intent_and_context,
    fetch_weather,
    evaluate_sops,
    resolve_sop_conflicts,
    synthesize_grounded_response,
    ask_clarification,
    handle_weather_error,
    handle_no_sop_match,
    handle_adversarial
)

def route_after_extraction(state: AgentState) -> str:
    status = state.get("execution_status")
    if status == "ADVERSARIAL_REJECTED":
        return "handle_adversarial"
    elif status == "NO_LOCATION" or status == "CLARIFICATION_NEEDED" or not state.get("extracted_location"):
        return "ask_clarification"
    return "fetch_weather"

def route_after_weather(state: AgentState) -> str:
    status = state.get("execution_status")
    if status == "WEATHER_FETCH_FAILED" or not state.get("weather_data"):
        return "handle_weather_error"
    return "evaluate_sops"

def route_after_resolution(state: AgentState) -> str:
    status = state.get("execution_status")
    if status == "NO_SOP_MATCH" or not state.get("selected_sop"):
        return "handle_no_sop_match"
    return "synthesize_grounded_response"

def create_weather_advisory_graph():
    """Builds and compiles the full LangGraph state machine with conditional branching."""
    workflow = StateGraph(AgentState)

    # Core execution nodes
    workflow.add_node("extract_intent_and_context", extract_intent_and_context)
    workflow.add_node("fetch_weather", fetch_weather)
    workflow.add_node("evaluate_sops", evaluate_sops)
    workflow.add_node("resolve_sop_conflicts", resolve_sop_conflicts)
    workflow.add_node("synthesize_grounded_response", synthesize_grounded_response)

    # Fallback and safety nodes
    workflow.add_node("ask_clarification", ask_clarification)
    workflow.add_node("handle_weather_error", handle_weather_error)
    workflow.add_node("handle_no_sop_match", handle_no_sop_match)
    workflow.add_node("handle_adversarial", handle_adversarial)

    # Wire edges
    workflow.add_edge(START, "extract_intent_and_context")

    workflow.add_conditional_edges(
        "extract_intent_and_context",
        route_after_extraction,
        {
            "handle_adversarial": "handle_adversarial",
            "ask_clarification": "ask_clarification",
            "fetch_weather": "fetch_weather"
        }
    )

    workflow.add_conditional_edges(
        "fetch_weather",
        route_after_weather,
        {
            "handle_weather_error": "handle_weather_error",
            "evaluate_sops": "evaluate_sops"
        }
    )

    workflow.add_edge("evaluate_sops", "resolve_sop_conflicts")

    workflow.add_conditional_edges(
        "resolve_sop_conflicts",
        route_after_resolution,
        {
            "handle_no_sop_match": "handle_no_sop_match",
            "synthesize_grounded_response": "synthesize_grounded_response"
        }
    )

    # Terminal edges
    workflow.add_edge("synthesize_grounded_response", END)
    workflow.add_edge("ask_clarification", END)
    workflow.add_edge("handle_weather_error", END)
    workflow.add_edge("handle_no_sop_match", END)
    workflow.add_edge("handle_adversarial", END)

    return workflow.compile()

graph = create_weather_advisory_graph()
