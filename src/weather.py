import requests
from typing import Dict, Any, Optional, Tuple
from src.config import GEOCODING_API_URL, FORECAST_API_URL

class WeatherClient:
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocodes a location query to lat/lon using Open-Meteo Geocoding API.
        Returns None if location is not found or Api fails.
        """
        if not query or not query.strip():
            return None
            
        params = {
            "name": query.strip(),
            "count": 5,
            "language": "en",
            "format": "json"
        }
        try:
            response = requests.get(GEOCODING_API_URL, params=params, timeout=self.timeout)
            if response.status_code != 200:
                return None
            data = response.json()
            results = data.get("results")
            if not results or len(results) == 0:
                return None
            
            # Take the top match
            top_result = results[0]
            return {
                "latitude": float(top_result.get("latitude")),
                "longitude": float(top_result.get("longitude")),
                "name": top_result.get("name"),
                "country": top_result.get("country", ""),
                "admin1": top_result.get("admin1", ""),
                "timezone": top_result.get("timezone", "UTC")
            }
        except Exception:
            return None

    def fetch_forecast(self, latitude: float, longitude: float, timezone: str = "auto") -> Optional[Dict[str, Any]]:
        """
        Fetches live current, hourly, and daily weather data from Open-Meteo forecast endpoint.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
                "wind_gusts_10m",
                "uv_index"
            ],
            "hourly": [
                "temperature_2m",
                "precipitation",
                "precipitation_probability",
                "wind_speed_10m",
                "uv_index"
            ],
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "uv_index_max"
            ]
        }
        
        try:
            response = requests.get(FORECAST_API_URL, params=params, timeout=self.timeout)
            if response.status_code != 200:
                return None
            return response.json()
        except Exception:
            return None

    def get_live_weather(self, location_query: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
        """
        End-to-end lookup: Geocodes city name, then queries Open-Meteo weather.
        Returns (location_meta, weather_data, error_message).
        """
        loc_meta = self.geocode(location_query)
        if not loc_meta:
            return None, None, f"Could not resolve geographic location for '{location_query}'."
            
        raw_weather = self.fetch_forecast(
            latitude=loc_meta["latitude"],
            longitude=loc_meta["longitude"],
            timezone=loc_meta.get("timezone", "auto")
        )
        if not raw_weather or "current" not in raw_weather:
            return loc_meta, None, f"Weather forecast service is unreachable for {loc_meta['name']}."
            
        current = raw_weather.get("current", {})
        daily = raw_weather.get("daily", {})
        
        # Build clean verified dictionary of numbers
        weather_summary = {
            "location_name": loc_meta["name"],
            "country": loc_meta["country"],
            "admin1": loc_meta["admin1"],
            "latitude": loc_meta["latitude"],
            "longitude": loc_meta["longitude"],
            "time": current.get("time"),
            "temperature_2m": current.get("temperature_2m", 0.0),
            "apparent_temperature": current.get("apparent_temperature", current.get("temperature_2m", 0.0)),
            "relative_humidity_2m": current.get("relative_humidity_2m", 0.0),
            "precipitation": current.get("precipitation", 0.0),
            "precipitation_probability": current.get("precipitation_probability", 0),
            "weather_code": current.get("weather_code", 0),
            "wind_speed_10m": current.get("wind_speed_10m", 0.0),
            "wind_gusts_10m": current.get("wind_gusts_10m", 0.0),
            "uv_index": current.get("uv_index", 0.0),
            # Daily aggregates for situational system detection
            "daily_precipitation_sum": daily.get("precipitation_sum", [0.0])[0] if daily.get("precipitation_sum") else 0.0,
            "daily_max_precipitation_prob": daily.get("precipitation_probability_max", [0])[0] if daily.get("precipitation_probability_max") else 0,
            "daily_max_wind_speed": daily.get("wind_speed_10m_max", [0.0])[0] if daily.get("wind_speed_10m_max") else 0.0,
            "raw_payload": raw_weather
        }
        return loc_meta, weather_summary, None

weather_client = WeatherClient()
