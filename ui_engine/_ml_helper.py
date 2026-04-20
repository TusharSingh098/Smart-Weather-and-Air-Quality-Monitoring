"""
ui_engine/_ml_helper.py
Internal helper that interfaces with ml_engine.inference_engine to
run tomorrow's prediction and return structured results.
"""
import os
import sys
import pickle
import math
import pandas as pd
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def run_prediction(state: str, district: str) -> dict:
    """
    Load trained .pkl models for the given district and run inference.
    Returns a dict with prediction keys, or raises on failure.
    """
    from ml_engine.inference_engine import SpecializedWeatherPredictor

    predictor = SpecializedWeatherPredictor(state, district)
    recent_data = predictor._get_latest_data()
    X_live = predictor._build_live_feature_vector(recent_data)

    predictions: dict = {}
    target_models = ["temperature_2m", "relative_humidity_2m", "rain_probability"]

    for var in target_models:
        model_path = os.path.join(
            predictor.district_path, f"{district}_{var}_model.pkl"
        )
        if not os.path.exists(model_path):
            continue
        with open(model_path, "rb") as fh:
            model = pickle.load(fh)

        if var == "rain_probability":
            predictions[var] = float(model.predict_proba(X_live)[0][1] * 100)
        else:
            predictions[var] = float(model.predict(X_live)[0])

    # Apparent temperature via Steadman formula
    if "temperature_2m" in predictions and "relative_humidity_2m" in predictions:
        temp  = predictions["temperature_2m"]
        humid = predictions["relative_humidity_2m"]
        wind_kmh = float(recent_data["wind_speed_10m"].iloc[-1])
        wind_ms  = wind_kmh / 3.6
        e = (humid / 100) * 6.105 * math.exp((17.27 * temp) / (237.7 + temp))
        predictions["feels_like"] = round(temp + 0.33 * e - 0.70 * wind_ms - 4.0, 1)

    predictions["future_date"] = getattr(predictor, "future_date", "Tomorrow")
    return predictions

def generate_tomorrow_hourly_df(predictions: dict) -> pd.DataFrame:
    """Takes single daily ML predictions and synthesizes a 24-hour realistic curve."""
    # Create 24 timestamps for tomorrow
    tomorrow = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)
    times = pd.date_range(start=tomorrow, periods=24, freq="h")
    
    # Extract the single predicted ML values
    base_temp = predictions.get("temperature_2m", 25.0)
    base_hum = predictions.get("relative_humidity_2m", 50.0)
    feels_like = predictions.get("feels_like", base_temp)
    rain_prob = predictions.get("rain_probability", 0.0)

    # Math trick: Create a sine wave that peaks at 2 PM (hour 14) and drops at 4 AM
    hours = times.hour
    # Shift so 14:00 is the peak (pi/2)
    phase = (hours - 8) * (np.pi / 12) 
    curve = np.sin(phase)

    # Temperature swings about 4 degrees up and down from the base prediction
    hourly_temp = base_temp + (curve * 4.0)
    hourly_feels = feels_like + (curve * 4.5)
    
    # Humidity does the exact opposite of temperature (highest when it's coldest)
    hourly_hum = base_hum - (curve * 15.0)
    hourly_hum = np.clip(hourly_hum, 10, 100) # Keep within 10-100%

    # Estimate hourly rain amount based on the daily probability
    hourly_rain = np.zeros(24)
    if rain_prob > 30.0:
        # If it's likely to rain, simulate a few millimeters during the afternoon
        hourly_rain = np.where((hours >= 12) & (hours <= 18), (rain_prob / 100) * 2.0, 0)

    return pd.DataFrame({
        "time": times,
        "temperature_2m": hourly_temp,
        "apparent_temperature": hourly_feels,
        "relative_humidity_2m": hourly_hum,
        "rain": hourly_rain
    })