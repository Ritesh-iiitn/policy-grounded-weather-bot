import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from src.config import SOPS_PATH

SEVERITY_WEIGHTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MODERATE": 2,
    "LOW": 1
}

class SOPEngine:
    def __init__(self, sops_path: Optional[Path] = None):
        self.sops_path = sops_path or SOPS_PATH
        self._cached_sops: List[Dict[str, Any]] = []
        self._last_mtime: float = 0.0
        self.reload_sops()

    def reload_sops(self) -> List[Dict[str, Any]]:
        """Loads or reloads SOPs dynamically from YAML file."""
        if not os.path.exists(self.sops_path):
            self._cached_sops = []
            return self._cached_sops
            
        mtime = os.path.getmtime(self.sops_path)
        if mtime != self._last_mtime or not self._cached_sops:
            with open(self.sops_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._cached_sops = data.get("policies", [])
            self._last_mtime = mtime
        return self._cached_sops

    def get_all_sops(self) -> List[Dict[str, Any]]:
        return self.reload_sops()

    def _matches_activity(self, sop: Dict[str, Any], user_activity: Optional[str]) -> bool:
        """Determines if the SOP applies to the requested user activity."""
        applicable = [a.lower() for a in sop.get("applicable_activities", [])]
        if "all_outdoor_activities" in applicable:
            return True
            
        if not user_activity:
            return False
            
        norm_activity = user_activity.lower().strip()
        
        # Check direct or substring inclusion
        for app in applicable:
            if app in norm_activity or norm_activity in app:
                return True
                
        # Common semantic synonyms
        synonym_map = {
            "cycling": ["bike", "bicycle", "biking", "two-wheeler", "scooter", "motorcycle", "ride"],
            "running": ["jogging", "marathon", "sprint", "outdoor_workout", "exercise"],
            "picnic": ["brunch", "lawn", "barbecue", "bbq", "dining outdoors", "eating outside", "park lunch"],
            "travel": ["commute", "driving", "transit", "road trip", "highway"],
            "park": ["playground", "swing", "kids play", "family outing"],
            "dog_walking": ["pet walk", "walk the dog", "taking dog out", "puppy"]
        }
        
        for key, syns in synonym_map.items():
            if key in applicable or any(s in applicable for s in syns):
                if any(s in norm_activity for s in syns) or key in norm_activity:
                    return True

        return False

    def _eval_numeric_conditions(self, sop: Dict[str, Any], weather: Dict[str, Any]) -> bool:
        """Evaluates whether the weather metrics satisfy the SOP's condition thresholds."""
        conds = sop.get("conditions", {})
        if not conds:
            return True

        temp = float(weather.get("temperature_2m", 0.0))
        wind = float(weather.get("wind_speed_10m", 0.0))
        gusts = float(weather.get("wind_gusts_10m", 0.0))
        precip = float(weather.get("precipitation", 0.0))
        pop = float(weather.get("precipitation_probability", 0))
        uv = float(weather.get("uv_index", 0.0))
        wcode = int(weather.get("weather_code", 0))
        daily_precip = float(weather.get("daily_precipitation_sum", 0.0))
        daily_pop = float(weather.get("daily_max_precipitation_prob", 0))

        # Effective precipitation and pop factoring in daily / situational trends
        eff_precip = max(precip, daily_precip)
        eff_pop = max(pop, daily_pop)
        eff_wind = max(wind, gusts)

        if "min_wind_speed_kmh" in conds and conds["min_wind_speed_kmh"] is not None:
            if eff_wind < conds["min_wind_speed_kmh"]:
                return False

        if "max_wind_speed_kmh" in conds and conds["max_wind_speed_kmh"] is not None:
            if wind > conds["max_wind_speed_kmh"]:
                return False

        if "min_uv_index" in conds and conds["min_uv_index"] is not None:
            if uv < conds["min_uv_index"]:
                return False

        if "min_temperature_c" in conds and conds["min_temperature_c"] is not None:
            if temp < conds["min_temperature_c"]:
                return False

        if "max_temperature_c" in conds and conds["max_temperature_c"] is not None:
            if temp > conds["max_temperature_c"]:
                return False

        if "min_precipitation_mm" in conds and conds["min_precipitation_mm"] is not None:
            if eff_precip < conds["min_precipitation_mm"]:
                return False

        if "max_precipitation_mm" in conds and conds["max_precipitation_mm"] is not None:
            if precip > conds["max_precipitation_mm"]:
                return False

        if "min_precipitation_probability" in conds and conds["min_precipitation_probability"] is not None:
            if eff_pop < conds["min_precipitation_probability"]:
                return False

        if "max_precipitation_probability" in conds and conds["max_precipitation_probability"] is not None:
            if eff_pop > conds["max_precipitation_probability"]:
                return False

        if "weather_codes" in conds and conds["weather_codes"] is not None:
            if wcode not in conds["weather_codes"]:
                return False

        return True

    def evaluate(self, weather: Dict[str, Any], user_activity: Optional[str]) -> List[Dict[str, Any]]:
        """
        Evaluates all active SOPs against weather numbers and user activity.
        Returns all matched SOPs.
        """
        sops = self.reload_sops()
        matched = []

        for sop in sops:
            # 1. Activity filter
            if not self._matches_activity(sop, user_activity):
                continue
                
            # 2. Weather condition filter
            if not self._eval_numeric_conditions(sop, weather):
                continue

            matched.append(sop)

        return matched

    def resolve_conflicts(self, matched_sops: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], str]:
        """
        Resolves conflicts among multiple matching SOPs using a deterministic hierarchy:
        1. Situational Override (e.g. low-pressure / monsoon depression system) takes precedence.
        2. Highest Severity level (CRITICAL > HIGH > MODERATE > LOW).
        3. More specific activity rule over broad rule.
        
        Returns (primary_sop, secondary_sops, rationale).
        """
        if not matched_sops:
            return None, [], "No SOP met the activity and weather criteria."

        if len(matched_sops) == 1:
            return matched_sops[0], [], f"Single applicable policy: {matched_sops[0]['id']} ({matched_sops[0]['title']})."

        # Check for situational override
        situational = [s for s in matched_sops if s.get("situational_override") is True]
        if situational:
            primary = situational[0]
            secondaries = [s for s in matched_sops if s["id"] != primary["id"]]
            rationale = (
                f"Situational Risk Override: {primary['id']} ({primary['title']}) was prioritized over "
                f"{len(secondaries)} secondary rule(s) because regional severe systems compromise all outdoor safety."
            )
            return primary, secondaries, rationale

        # Sort by severity weight descending
        sorted_sops = sorted(
            matched_sops,
            key=lambda s: SEVERITY_WEIGHTS.get(s.get("severity", "LOW"), 1),
            reverse=True
        )

        primary = sorted_sops[0]
        secondaries = sorted_sops[1:]
        rationale = (
            f"Severity Hierarchy: {primary['id']} (Severity {primary.get('severity')}) selected as primary policy "
            f"over {', '.join(s['id'] for s in secondaries)} due to higher risk level."
        )
        return primary, secondaries, rationale

sop_engine = SOPEngine()
