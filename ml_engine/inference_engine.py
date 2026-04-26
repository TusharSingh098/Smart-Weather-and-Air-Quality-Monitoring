"""
ml_engine/inference_engine.py
Predictive Inference Module for the PyChaoS Weather Monitor.

Dynamically constructs 72-hour feature vectors entirely from live APIs 
to prevent temporal gaps, and evaluates them against pre-trained XGBoost 
regressors and classifiers. Features a self-healing architecture.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
import math
import subprocess
from ml_engine.performance_monitor import PerformanceMonitor

# ─── Environment Configuration ────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Import all three API engines for dynamic real-time matrix assembly
from api_engine.weather_api import WeatherBase, WeatherToday, AirQuality

def calculate_apparent_temperature(temp_c: float, humidity: float, wind_speed_kmh: float) -> float:
    """Calculates the human-perceived 'feels like' temperature using Steadman's equation."""
    wind_ms = wind_speed_kmh / 3.6
    e = (humidity / 100) * 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))
    apparent_temp = temp_c + (0.33 * e) - (0.70 * wind_ms) - 4.0
    return round(apparent_temp, 2)

class SpecializedWeatherPredictor:
    """Orchestrates dynamic live data ingestion, vectorization, and XGBoost inference."""
    
    def __init__(self, state_name: str, district_name: str, lag_hours: int = 72, forecast_horizon: int = 24):
        self.state = state_name
        self.district = district_name
        self.lag_hours = lag_hours
        self.forecast_horizon = forecast_horizon
        self.district_path = os.path.join(project_root, "weather_data", self.state, self.district)

        # ─── Autonomous Self-Healing Check ───
        core_model = os.path.join(self.district_path, f"{self.district}_temperature_2m_max_model.pkl")
        
        if not os.path.exists(core_model):
            print("\n[!] FIRST-RUN DETECTED: Intelligence models not found.")
            print("[!] Initiating full system ingestion and training. Please wait...")
            
            pipeline_path = os.path.join(project_root, "run_ml_pipeline.py")
            try:
                subprocess.run([sys.executable, pipeline_path], check=True)
                print("\n[SUCCESS] System built. Proceeding with forecast...")
            except subprocess.CalledProcessError:
                print("\n[FATAL] Automatic build failed. Check internet connection.")
                sys.exit(1)
        
        # Strict enforcement of the 8 historical features required by the matrix
        self.feature_variables = [
            'temperature_2m', 'relative_humidity_2m', 'rain', 
            'wind_speed_10m', 'pm10', 'pm2_5', 'wind_dir_sin', 'wind_dir_cos'
        ]

    def _get_latest_data(self) -> pd.DataFrame:
        """
        Assembles a 72-hour matrix with an 'After-Midnight' safety buffer.
        If today's forecast is empty (early morning), it shifts the window 
        back by one day to ensure a contiguous data block.
        """
        import datetime
        now = datetime.datetime.now()
        
        wb = WeatherBase()
        aq = AirQuality()
        wt = WeatherToday()
        
        # 1. Geolocation setup
        if not wb.geolocator(self.district):
            raise Exception(f"Geolocator failed for {self.district}")
            
        # Standardize location across all API objects
        aq.location = wt.location = wb.location
        aq.place = wt.place = wb.place = self.district # Fixed: Using .place instead of .district

        def fetch_72h_matrix():
            # Standard fetch: 2 days history + Today's forecast
            w_hist = wb.historic_data(num_days=2)
            a_hist = aq.air_quality_data(num_days=2)
            today_df = wt.forecast_today()
            
            if w_hist is None or a_hist is None or today_df is None or today_df.empty:
                return None
            
            hist_df = pd.merge(w_hist, a_hist, on='time', how='inner')
            return pd.concat([hist_df, today_df], ignore_index=True)

        print(f" -> Attempting live matrix assembly (System Time: {now.strftime('%H:%M')})...")
        
        # ATTEMPT 1: Try to get the standard 72h block
        combined_df = fetch_72h_matrix()

        # ATTEMPT 2: Midnight Safety Buffer
        # If today's forecast is missing/incomplete and it's between 00:00 and 04:00
        if (combined_df is None or len(combined_df) < self.lag_hours) and now.hour < 4:
            print(" [!] Early morning API gap. Shifting anchor to full historical block...")
            
            # Pull 3 full days of history (72 hours) to fill the gap
            w_hist_fallback = wb.historic_data(num_days=3)
            a_hist_fallback = aq.air_quality_data(num_days=3)
            
            if w_hist_fallback is not None and a_hist_fallback is not None:
                combined_df = pd.merge(w_hist_fallback, a_hist_fallback, on='time', how='inner')
                print(" [SUCCESS] Contiguous historical block recovered.")

        if combined_df is None or len(combined_df) < self.lag_hours:
            raise Exception("API engines returned insufficient data for a 72-hour window.")

        # --- Standard Data Healing ---
        for col in ['pm10', 'pm2_5']:
            if col not in combined_df.columns: 
                combined_df[col] = np.nan
            combined_df[col] = combined_df[col].ffill().bfill()

        if 'wind_direction_10m' in combined_df.columns:
            rad = combined_df['wind_direction_10m'] * np.pi / 180
            combined_df['wind_dir_sin'], combined_df['wind_dir_cos'] = np.sin(rad), np.cos(rad)

        combined_df['time'] = pd.to_datetime(combined_df['time'])
        
        # Enforce the strict 8-feature matrix order
        core_columns = ['time'] + self.feature_variables
        combined_df = combined_df[[col for col in core_columns if col in combined_df.columns]]
        
        return combined_df.tail(self.lag_hours).reset_index(drop=True)

    def _build_live_feature_vector(self, recent_data: pd.DataFrame) -> np.ndarray:
        """Flattens the 2D Pandas DataFrame into a 1D NumPy array required for XGBoost."""
        feature_vector = []
        
        # Ensure we pull the data backwards if your model was trained on lag_1 being the most recent hour
        for var in self.feature_variables:
            values = recent_data[var].values[::-1] 
            for i in range(self.lag_hours):
                feature_vector.append(values[i])
                
        last_timestamp = recent_data['time'].iloc[-1]
        target_time = last_timestamp + pd.Timedelta(hours=self.forecast_horizon)
        self.future_date = target_time.strftime('%A, %B %d, %Y at %I:%M %p')
        
        # Append target-time cyclical encodings (diurnal and seasonal awareness)
        feature_vector.append(np.sin(2 * np.pi * target_time.hour / 24))
        feature_vector.append(np.cos(2 * np.pi * target_time.hour / 24))
        feature_vector.append(np.sin(2 * np.pi * target_time.dayofyear / 365.25))
        feature_vector.append(np.cos(2 * np.pi * target_time.dayofyear / 365.25))
                
        return np.array(feature_vector).reshape(1, -1)

    def generate_forecast(self):
        """Executes the AI inference pipeline."""
        print("\n==================================================")
        print(f" Generating {self.forecast_horizon}-Hour Forecast for {self.district}")
        print("==================================================\n")
        
        try:
            recent_data = self._get_latest_data()
        except Exception as e:
            print(f" [FATAL ERROR] Could not retrieve data: {e}")
            return
            
        X_live = self._build_live_feature_vector(recent_data)
        predictions = {}

        monitor = PerformanceMonitor(project_root)
        # Extract the target date string (YYYY-MM-DD)
        target_dt_str = pd.to_datetime(self.future_date).strftime("%Y-%m-%d")
        
        monitor.log_prediction(
            state=self.state,
            district=self.district,
            target_date=target_dt_str,
            pred_max=predictions.get('temperature_2m_max', 0),
            pred_min=predictions.get('temperature_2m_min', 0)
        )
        
        print("\n--- AI Brain Execution ---")
        
        target_models = ['temperature_2m_max', 'temperature_2m_min', 'relative_humidity_2m', 'rain_probability']
        
        for var in target_models:
            model_path = os.path.join(self.district_path, f"{self.district}_{var}_model.pkl")
            if not os.path.exists(model_path):
                print(f" [WARNING] Model {var} not found. Ensure master_training was run.")
                continue
                
            with open(model_path, 'rb') as file:
                model = pickle.load(file)
                
            if var == 'rain_probability':
                chance_of_rain = model.predict_proba(X_live)[0][1] * 100
                predictions[var] = chance_of_rain
            else:
                predictions[var] = model.predict(X_live)[0]
                
        print("\n==================================================")
        print(f" EXACT FORECAST FOR: {self.future_date}")
        print("==================================================")
        
        if 'temperature_2m_max' in predictions:
            print(f" Maximum Temperature    : {predictions['temperature_2m_max']:>5.1f} °C")
            
        if 'temperature_2m_min' in predictions:
            print(f" Minimum Temperature    : {predictions['temperature_2m_min']:>5.1f} °C")
            
        if 'relative_humidity_2m' in predictions:
            print(f" Relative Humidity      : {predictions['relative_humidity_2m']:>5.1f} %")
            
        if 'temperature_2m_max' in predictions and 'relative_humidity_2m' in predictions:
            recent_wind = recent_data['wind_speed_10m'].iloc[-1]
            feels_like = calculate_apparent_temperature(
                predictions['temperature_2m_max'], predictions['relative_humidity_2m'], recent_wind
            )
            print(f" Feels Like (Max)       : {feels_like:>5.1f} °C")
            
        if 'rain_probability' in predictions:
            print(f" Chance of Rain (PoP)   : {predictions['rain_probability']:>5.1f} %")
            
        print("==================================================\n")

if __name__ == "__main__":
    predictor = SpecializedWeatherPredictor("Haryana", "Rohtak")
    predictor.generate_forecast()