"""
ui_engine/data_bridge.py
Frontend-Backend Interface & Graceful Degradation Controller.

Acts as a Facade to decouple the CustomTkinter UI from the API and ML engines.
Implements automatic offline-fallback data synthesis using NumPy to prevent 
application crashes during network outages.

Author: Team PyChaoS
College: NIT Kurukshetra
"""
import os
import sys
import math
import numpy as np
import pandas as pd

# ─── Resolve Project Root ────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Attempt to load the primary backend APIs. 
# If they fail (e.g., missing dependencies or network blocks), flag the API as offline.
try:
    from api_engine.weather_api import WeatherBase, WeatherToday, AirQuality
    _API_OK = True
except Exception:
    _API_OK = False

# Safely load the geography Configuration (SSOT)
try:
    from ml_engine.geography import TARGET_REGIONS
except Exception:
    # Hardcoded fallback to ensure the UI dropdowns never render empty
    TARGET_REGIONS = {
        "Haryana":       ["Bhiwani", "Faridabad", "Jind", "Kaithal", "Kurukshetra", "Rohtak"],
        "West_Bengal":   ["Asansol", "Darjeeling", "Kolkata"],
        "Uttar_Pradesh": ["Agra", "Ayodhya", "Bareilly", "Basti", "Gorakhpur",
                          "Kanpur", "Lalitpur", "Lucknow", "Noida", "Prayagraj", "Varanasi"],
    }

# ─── Geography Helpers ────────────────────────────────────────────────────────

def get_states() -> list[str]:
    return list(TARGET_REGIONS.keys())

def get_districts(state: str) -> list[str]:
    return TARGET_REGIONS.get(state, [])

def get_all_districts() -> list[str]:
    return [d for ds in TARGET_REGIONS.values() for d in ds]

def models_exist(state: str, district: str) -> bool:
    """Verifies the existence of trained XGBoost binaries before allowing ML inference."""
    path = os.path.join(_ROOT, "weather_data", state, district,
                        f"{district}_temperature_2m_max_model.pkl")
    return os.path.exists(path)

# ─── Weather – Historic ───────────────────────────────────────────────────────

def fetch_historic_weather(city: str, num_days: int) -> pd.DataFrame:
    """Returns hourly historical weather DataFrame or routes to mock data on failure."""
    if _API_OK:
        try:
            client = WeatherBase()
            if client.geolocator(city):
                df = client.historic_data(num_days=num_days)
                if df is not None:
                    return df
        except Exception as exc:
            print(f"[data_bridge] historic_weather: {exc}")
            
    # Trigger Graceful Degradation
    return _mock_weather(num_days * 24)

# ─── Weather – Today ──────────────────────────────────────────────────────────

def fetch_today_weather(city: str) -> pd.DataFrame:
    """Fetches real-time T-Zero data, embedding the resolved geocoded address into the DataFrame metadata."""
    if _API_OK:
        try:
            client = WeatherToday()
            if client.geolocator(city):
                df = client.forecast_today()
                if df is not None:
                    # Attach the human-readable API location to the dataframe attributes
                    df.attrs["address"] = client.address()
                    return df
        except Exception as exc:
            print(f"[data_bridge] today_weather: {exc}")
            
    return _mock_weather(24)

# ─── AQI – Historic ───────────────────────────────────────────────────────────

def fetch_historic_aqi(city: str, num_days: int) -> pd.DataFrame:
    """Returns hourly historical Air Quality DataFrame or routes to mock data."""
    if _API_OK:
        try:
            client = AirQuality()
            if client.geolocator(city):
                df = client.air_quality_data(num_days=num_days)
                if df is not None:
                    return df
        except Exception as exc:
            print(f"[data_bridge] historic_aqi: {exc}")
            
    return _mock_aqi(num_days * 24)

# ─── ML Tomorrow Prediction ───────────────────────────────────────────────────

def predict_tomorrow(state: str, district: str) -> tuple[dict, pd.DataFrame] | None:
    """
    Invokes the Machine Learning adapter to generate next-day forecasting.
    Returns both the raw prediction dictionary and the synthesized 24-hour diurnal curve.
    """
    if not models_exist(state, district):
        return None
    try:
        from ui_engine._ml_helper import run_prediction, generate_tomorrow_hourly_df
        pred_dict = run_prediction(state, district)
        hourly_df = generate_tomorrow_hourly_df(pred_dict)
        return pred_dict, hourly_df
    except Exception as exc:
        print(f"[data_bridge] predict_tomorrow: {exc}")
        return None

# ─── Mock / Fallback Data Generators ──────────────────────────────────────────

def _mock_weather(n: int) -> pd.DataFrame:
    """
    Generates synthetic meteorological data using trigonometric waves and Gaussian noise.
    Ensures the UI can still render charts even if the machine has no internet connection.
    """
    rng = np.random.default_rng(42)
    times = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="h")
    phase = np.linspace(0, 4 * np.pi, n)
    
    # Simulate diurnal cycles with mathematical variance
    temp = 26 + 8 * np.sin(phase) + rng.normal(0, 1.2, n)
    humid = 65 + 20 * np.cos(phase * 0.8) + rng.normal(0, 2, n)
    wind = np.abs(rng.normal(18, 5, n))
    rain = np.maximum(0, rng.normal(0.3, 0.8, n))
    
    return pd.DataFrame({
        "time":               times,
        "temperature_2m":     temp,
        "apparent_temperature": temp - 2.5,
        "relative_humidity_2m": np.clip(humid, 5, 100),
        "wind_speed_10m":     wind,
        "wind_direction_10m": rng.uniform(0, 360, n),
        "rain":               rain,
        "weather_code":       rng.choice([0, 1, 2, 3, 61, 80], n),
        "snowfall":           np.zeros(n),
    })

def _mock_aqi(n: int) -> pd.DataFrame:
    """Generates synthetic Air Quality temporal data."""
    rng = np.random.default_rng(42)
    times = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="h")
    trend = 45 + 30 * np.sin(np.linspace(0, 3 * np.pi, n))
    
    return pd.DataFrame({
        "time":             times,
        "pm2_5":            np.abs(trend + rng.normal(0, 8, n)),
        "pm10":             np.abs(trend * 1.8 + rng.normal(0, 12, n)),
        "ozone":            np.abs(rng.normal(42, 10, n)),
        "nitrogen_dioxide": np.abs(rng.normal(28, 7, n)),
        "carbon_monoxide":  np.abs(rng.normal(520, 90, n)),
        "sulphur_dioxide":  np.abs(rng.normal(12, 4, n)),
    })

# ─── AQI & WMO Code Resolvers ─────────────────────────────────────────────────

AQI_BANDS = [
    (0.0,   12.0,  "#00E400", "Good"),
    (12.0,  35.4,  "#F0D000", "Moderate"),
    (35.4,  55.4,  "#FF7E00", "Unhealthy (Sensitive)"),
    (55.4,  150.4, "#FF0000", "Unhealthy"),
    (150.4, 250.4, "#8F3F97", "Very Unhealthy"),
    (250.4, 999.0, "#7E0023", "Hazardous"),
]

def aqi_level(pm25: float) -> tuple[str, str]:
    """Return (level_label, color_hex) based on EPA standards for a PM2.5 value."""
    for lo, hi, color, label in AQI_BANDS:
        if pm25 <= hi:
            return label, color
    return "Hazardous", "#7E0023"

# Standard WMO (World Meteorological Organization) Code Mappings
WEATHER_ICONS = {
    0: "☀️",  1: "🌤",  2: "⛅",  3: "☁️",
    45: "🌫", 48: "🌫",
    51: "🌦", 53: "🌦", 55: "🌧",
    61: "🌧", 63: "🌧", 65: "🌧",
    71: "❄️", 73: "❄️", 75: "❄️",
    80: "🌦", 81: "🌦", 82: "⛈",
    95: "⛈", 96: "⛈", 99: "⛈",
}

WEATHER_LABELS = {
    0: "Clear Sky",       1: "Mainly Clear",    2: "Partly Cloudy",  3: "Overcast",
    45: "Foggy",          48: "Icy Fog",
    51: "Light Drizzle",  53: "Drizzle",         55: "Heavy Drizzle",
    61: "Slight Rain",    63: "Moderate Rain",   65: "Heavy Rain",
    71: "Slight Snow",    73: "Moderate Snow",   75: "Heavy Snow",
    80: "Rain Showers",   81: "Rain Showers",    82: "Heavy Showers",
    95: "Thunderstorm",   96: "Thunderstorm+Hail", 99: "Heavy Thunderstorm",
}