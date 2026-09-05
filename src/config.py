import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SOPS_PATH = DATA_DIR / "sops.yaml"

# Open-Meteo Endpoints
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# LLM Configurations
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_GEMINI_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash")
DEFAULT_OPENAI_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
