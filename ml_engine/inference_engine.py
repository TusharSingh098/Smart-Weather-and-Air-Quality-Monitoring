import os
import sys
import pickle
import numpy as np
import pandas as pd
import math

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from api_engine.weather_api import WeatherToday

def calculate_apparent_temperature(temp_c, humidity, wind_speed_kmh):
    wind_ms = wind_speed_kmh / 3.6
    e = (humidity / 100) * 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))
    apparent_temp = temp_c + (0.33 * e) - (0.70 * wind_ms) - 4.0
    return round(apparent_temp, 2)

class SpecializedWeatherPredictor:
    def __init__(self, state_name: str, district_name: str, lag_hours: int = 72, forecast_horizon: int = 24):
        self.state = state_name
        self.district = district_name
        self.lag_hours = lag_hours
        self.forecast_horizon = forecast_horizon
        self.district_path = os.path.join(project_root, "weather_data", self.state, self.district)
        
        # The 8 historical clues needed to build the matrix
        self.feature_variables = [
            'temperature_2m', 'relative_humidity_2m', 'rain', 
            'wind_speed_10m', 'pm10', 'pm2_5', 'wind_dir_sin', 'wind_dir_cos'
        ]

    def _get_latest_data(self) -> pd.DataFrame:
        target_csv = os.path.join(self.district_path, "training_ready_unified.csv")
        if not os.path.exists(target_csv):
            raise FileNotFoundError(f"Unified CSV not found. Run ingestion.")
        history_df = pd.read_csv(target_csv)
        history_df['time'] = pd.to_datetime(history_df['time'])
        
        print(" -> Fetching live T-Zero Weather forecast to anchor predictions...")
        today_client = WeatherToday()
        if today_client.geolocator(self.district):
            today_df = today_client.forecast_today()
            if today_df is not None:
                drop_cols = ['dew_point_2m', 'apparent_temperature', 'weather_code', 'snowfall', 'precipitation']
                today_df = today_df.drop(columns=drop_cols, errors='ignore')
                
                if 'wind_direction_10m' in today_df.columns:
                    wind_radians = today_df['wind_direction_10m'] * np.pi / 180
                    today_df['wind_dir_sin'] = np.sin(wind_radians)
                    today_df['wind_dir_cos'] = np.cos(wind_radians)
                    today_df = today_df.drop(columns=['wind_direction_10m'])
                    
                for col in ['pm10', 'pm2_5']:
                    if col not in today_df.columns:
                        today_df[col] = history_df[col].iloc[-1]
                        
                today_df['time'] = pd.to_datetime(today_df['time'])
                
                # Strict enforcement using the 8 base features + time
                core_columns = ['time'] + self.feature_variables
                today_df = today_df[[col for col in core_columns if col in today_df.columns]]
                
                combined_df = pd.concat([history_df, today_df], ignore_index=True)
            else:
                combined_df = history_df
        else:
            combined_df = history_df
            
        if len(combined_df) < self.lag_hours:
            raise ValueError("Not enough data to form lookback window.")
            
        return combined_df.tail(self.lag_hours).reset_index(drop=True)

    def _build_live_feature_vector(self, recent_data: pd.DataFrame) -> np.ndarray:
        feature_vector = []
        
        for var in self.feature_variables:
            values = recent_data[var].values[::-1] 
            for i in range(self.lag_hours):
                feature_vector.append(values[i])
                
        # Calculate exactly when "Tomorrow" is and save it
        last_timestamp = recent_data['time'].iloc[-1]
        target_time = last_timestamp + pd.Timedelta(hours=self.forecast_horizon)
        self.future_date = target_time.strftime('%A, %B %d, %Y at %I:%00 %p')
        
        feature_vector.append(np.sin(2 * np.pi * target_time.hour / 24))
        feature_vector.append(np.cos(2 * np.pi * target_time.hour / 24))
        feature_vector.append(np.sin(2 * np.pi * target_time.dayofyear / 365.25))
        feature_vector.append(np.cos(2 * np.pi * target_time.dayofyear / 365.25))
                
        return np.array(feature_vector).reshape(1, -1)

    def generate_forecast(self):
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
        
        print("\n--- AI Brain Execution ---")
        
        # Load and predict the 3 specific targets
        target_models = ['temperature_2m', 'relative_humidity_2m', 'rain_probability']
        
        for var in target_models:
            model_path = os.path.join(self.district_path, f"{self.district}_{var}_model.pkl")
            if not os.path.exists(model_path):
                print(f" [WARNING] Model {var} not found. Ensure master_training was run.")
                continue
                
            with open(model_path, 'rb') as file:
                model = pickle.load(file)
                
            if var == 'rain_probability':
                # CLASSIFIER: Ask for the exact probability percentage instead of 0 or 1
                chance_of_rain = model.predict_proba(X_live)[0][1] * 100
                predictions[var] = chance_of_rain
            else:
                # REGRESSOR: Ask for the exact number
                predictions[var] = model.predict(X_live)[0]
                
        # Display Results
        print("\n==================================================")
        print(f" EXACT FORECAST FOR: {self.future_date}")
        print("==================================================")
        
        if 'temperature_2m' in predictions:
            print(f" Base Temperature       : {predictions['temperature_2m']:>5.1f} °C")
            
        if 'relative_humidity_2m' in predictions:
            print(f" Relative Humidity      : {predictions['relative_humidity_2m']:>5.1f} %")
            
        if 'temperature_2m' in predictions and 'relative_humidity_2m' in predictions:
            # We use the most recent known wind speed as a baseline for the UX calculation
            recent_wind = recent_data['wind_speed_10m'].iloc[-1]
            feels_like = calculate_apparent_temperature(
                predictions['temperature_2m'], predictions['relative_humidity_2m'], recent_wind
            )
            print(f" Feels Like (Apparent)  : {feels_like:>5.1f} °C")
            
        if 'rain_probability' in predictions:
            print(f" Chance of Rain (PoP)   : {predictions['rain_probability']:>5.1f} %")
            
        print("==================================================\n")

if __name__ == "__main__":
    predictor = SpecializedWeatherPredictor("West_Bengal", "Asansol")
    predictor.generate_forecast()