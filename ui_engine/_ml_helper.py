"""
ui_engine/_ml_helper.py
Machine Learning Frontend Adapter & Data Synthesizer.

Internal helper that interfaces with ml_engine.inference_engine to
run tomorrow's prediction and return structured results for the UI.
Includes mathematical synthesis for 24-hour UI charting.

Author: Team PyChaoS
College: NIT Kurukshetra
"""
import os
import sys
import pickle
import math
import pandas as pd
import numpy as np

# ─── Environment Configuration ────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

def run_prediction(state: str, district: str) -> dict:
    """
    Acts as the Adapter between the UI and the ML Inference Engine.
    Loads trained .pkl models for the given district, executes the inference 
    vectors, and structures the output for frontend rendering.
    
    Args:
        state (str): Target state.
        district (str): Target district.
        
    Returns:
        dict: A structured dictionary containing all formatted prediction targets.
    """
    from ml_engine.inference_engine import SpecializedWeatherPredictor

    # Initialize backend inference engine
    predictor = SpecializedWeatherPredictor(state, district)
    recent_data = predictor._get_latest_data()
    X_live = predictor._build_live_feature_vector(recent_data)

    predictions: dict = {}
    target_models = ["temperature_2m_max", "temperature_2m_min", "relative_humidity_2m", "rain_probability"]

    # Iterate and evaluate each model independently
    for var in target_models:
        model_path = os.path.join(
            predictor.district_path, f"{district}_{var}_model.pkl"
        )
        if not os.path.exists(model_path):
            continue
            
        with open(model_path, "rb") as fh:
            model = pickle.load(fh)

        # Handle exact output based on algorithm paradigm
        if var == "rain_probability":
            predictions[var] = float(model.predict_proba(X_live)[0][1] * 100)
        else:
            predictions[var] = float(model.predict(X_live)[0])

    # ─── Biometeorological UX Enhancements ───
    # Apparent temperature via Steadman formula
    if "temperature_2m_max" in predictions and "relative_humidity_2m" in predictions:
        temp  = predictions["temperature_2m_max"]
        humid = predictions["relative_humidity_2m"]
        wind_kmh = float(recent_data["wind_speed_10m"].iloc[-1])
        wind_ms  = wind_kmh / 3.6
        
        # Calculate water vapor pressure (e)
        e = (humid / 100) * 6.105 * math.exp((17.27 * temp) / (237.7 + temp))
        predictions["feels_like"] = round(temp + 0.33 * e - 0.70 * wind_ms - 4.0, 1)

    # Attach future exact timestamp for UI display
    predictions["future_date"] = getattr(predictor, "future_date", "Tomorrow")
    return predictions

def generate_tomorrow_hourly_df(predictions: dict) -> pd.DataFrame:
    """
    Takes single daily ML predictions and synthesizes a 24-hour realistic 
    diurnal curve using phase-shifted trigonometric functions.
    
    Returns:
        pd.DataFrame: A 24-row DataFrame compatible with the Matplotlib charting engine.
    """
    # 1. Temporal Framework: Create 24 timestamps for tomorrow
    tomorrow = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)
    times = pd.date_range(start=tomorrow, periods=24, freq="h")
    
    # 2. Extract the single predicted ML anchor values
    predicted_max_temp = predictions.get("temperature_2m_max", 25.0)

    # NEW: Extract the AI's predicted minimum (fallback to max - 8 if model is missing)
    predicted_min_temp = predictions.get("temperature_2m_min", predicted_max_temp - 8.0)

    amplitude = (predicted_max_temp - predicted_min_temp) / 2.0
    base_temp = predicted_max_temp - amplitude 

    predicted_max_feels = predictions.get("feels_like", predicted_max_temp)
    feels_amplitude = amplitude + 0.5 # Feels-like swings slightly wider than base temp
    feels_base = predicted_max_feels - feels_amplitude

    base_hum = predictions.get("relative_humidity_2m", 50.0)
    rain_prob = predictions.get("rain_probability", 0.0)

    # 3. Diurnal Math Engine: Create a sine wave that peaks at 2 PM (hour 14) and drops at 4 AM
    hours = times.hour
    # Shift phase so 14:00 evaluates to pi/2 (the peak of the sine wave)
    phase = (hours - 8) * (np.pi / 12) 
    curve = np.sin(phase)

    # 4. Feature Synthesis
    # Temperature swings about 4 degrees up and down from the base ML prediction
    hourly_temp = base_temp + (curve * amplitude)
    hourly_feels = feels_base + (curve * feels_amplitude)
    
    # Humidity does the exact opposite of temperature (highest when it's coldest)
    hourly_hum = base_hum - (curve * 15.0)
    hourly_hum = np.clip(hourly_hum, 10, 100) # Ensure physics constraints (10-100%)

    # 5. Precipitation Simulation
    # Estimate hourly rain amount based on the daily classification probability
    hourly_rain = np.zeros(24)
    if rain_prob > 30.0:
        # If the ML engine predicts a high likelihood of rain, simulate accumulation during the afternoon
        hourly_rain = np.where((hours >= 12) & (hours <= 18), (rain_prob / 100) * 2.0, 0)

    # Package and return for UI charting
    return pd.DataFrame({
        "time": times,
        "temperature_2m": hourly_temp,
        "apparent_temperature": hourly_feels,
        "relative_humidity_2m": hourly_hum,
        "rain": hourly_rain
    })