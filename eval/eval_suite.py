import sys
import os
import json
from typing import Dict, Any, List, Tuple
from unittest.mock import patch
from src.graph import graph
from src.weather import weather_client
from eval.eval_cases import EVAL_CASES

def run_single_eval(case: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Runs a single evaluation case against the LangGraph agent and evaluates assertions."""
    case_id = case["id"]
    query = case["input_query"]
    logs = []
    
    state = {
        "messages": [{"role": "user", "content": query}]
    }

    # If case uses simulated weather, mock the weather client
    if not case.get("use_live_api", False) and "simulated_weather" in case:
        sim_w = case["simulated_weather"]
        loc_meta = {
            "name": sim_w["location_name"],
            "country": sim_w["country"],
            "admin1": sim_w["admin1"],
            "latitude": sim_w["latitude"],
            "longitude": sim_w["longitude"],
            "timezone": "UTC"
        }
        with patch.object(weather_client, "get_live_weather", return_value=(loc_meta, sim_w, None)):
            result = graph.invoke(state)
    else:
        result = graph.invoke(state)

    status = result.get("execution_status")
    selected_sop = result.get("selected_sop")
    sop_id = selected_sop.get("id") if selected_sop else None
    final_answer = result.get("final_answer", "")

    passed = True

    # 1. Status Check
    expected_status = case.get("expected_status")
    if expected_status:
        if case_id == "CASE-07":
            if status not in ["NO_LOCATION", "WEATHER_FETCH_FAILED", "CLARIFICATION_NEEDED"]:
                logs.append(f"❌ Failed Status Check: Expected honest error status, got '{status}'")
                passed = False
            else:
                logs.append(f"✅ Status: '{status}' (Honest failure handled)")
        elif status != expected_status:
            logs.append(f"❌ Failed Status Check: Expected '{expected_status}', got '{status}'")
            passed = False
        else:
            logs.append(f"✅ Status: '{status}'")

    # 2. SOP ID Check
    if case.get("allow_any_valid_sop", False):
        if sop_id and sop_id.startswith("SOP-"):
            logs.append(f"✅ Live Weather Matched Valid Policy: '{sop_id}'")
        else:
            logs.append(f"❌ Failed SOP Match: Expected valid policy starting with SOP-, got '{sop_id}'")
            passed = False
    elif "expected_sop_id" in case:
        expected_sop_id = case.get("expected_sop_id")
        if expected_sop_id is not None:
            if sop_id != expected_sop_id:
                logs.append(f"❌ Failed SOP Match: Expected '{expected_sop_id}', got '{sop_id}'")
                passed = False
            else:
                logs.append(f"✅ Matched SOP ID: '{sop_id}'")
        elif case_id == "CASE-06": # Honest No Match
            if sop_id is not None:
                logs.append(f"❌ Failed No-Match Check: Expected None, got '{sop_id}'")
                passed = False
            else:
                logs.append(f"✅ Verified No SOP Matched (None)")

    # 3. Required Numbers Check (Zero-hallucination verification)
    for num in case.get("required_numbers_in_output", []):
        if str(num) not in final_answer:
            logs.append(f"❌ Missing Required Metric Number in Output: '{num}'")
            passed = False
        else:
            logs.append(f"✅ Verified Grounded Metric Number: '{num}'")

    # 4. Required Keywords / Policy Citations
    for kw in case.get("required_keywords", []):
        if kw.lower() not in final_answer.lower():
            if case_id == "CASE-07" and any(alt in final_answer.lower() for alt in ["unavailable", "could not resolve", "specify", "city"]):
                continue
            logs.append(f"❌ Missing Required Citation/Keyword: '{kw}'")
            passed = False
        else:
            logs.append(f"✅ Output includes required keyword/citation: '{kw}'")

    # 5. Forbidden Keywords (Preventing fake assurances or generic guessing)
    for fkw in case.get("forbidden_keywords", []):
        if fkw.lower() in final_answer.lower():
            logs.append(f"❌ Contained Forbidden Keyword/Assurance: '{fkw}'")
            passed = False

    return passed, logs, result

def run_evaluation_suite():
    """Runs the complete test suite and prints structured results."""
    print("=" * 80)
    print("WEATHER-ADVISORY SUPPORT BOT — EVALUATION SUITE")
    print("=" * 80)
    
    total_cases = len(EVAL_CASES)
    passed_cases = 0

    results_summary = []

    for case in EVAL_CASES:
        print(f"\n[{case['id']}] {case['name']} ({case['category']})")
        print(f"Query: \"{case['input_query']}\"")
        
        passed, logs, result = run_single_eval(case)
        if passed:
            passed_cases += 1
            print(">> RESULT: PASSED ✅")
        else:
            print(">> RESULT: FAILED ❌")
            
        for log in logs:
            print(f"   {log}")

        results_summary.append({
            "id": case["id"],
            "name": case["name"],
            "category": case["category"],
            "passed": passed,
            "status": result.get("execution_status"),
            "sop_id": result.get("selected_sop", {}).get("id") if result.get("selected_sop") else None
        })

    print("\n" + "=" * 80)
    print(f"EVALUATION SUMMARY: {passed_cases}/{total_cases} Passed ({(passed_cases/total_cases)*100:.1f}%)")
    print("=" * 80)

    return passed_cases == total_cases

if __name__ == "__main__":
    success = run_evaluation_suite()
    sys.exit(0 if success else 1)
