"""
api_engine/mass_ingestion.py
Automated ETL pipeline for bulk historical data collection and preprocessing.
Synchronizes Weather and AQI data into a training-ready unified matrix.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import os
import sys
import time
import numpy as np
import pandas as pd

# ─── Environment Configuration ────────────────────────────────────────────────
# Dynamically locate project root to ensure absolute import stability
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from api_engine.weather_api import WeatherBase, AirQuality
from ml_engine.geography import TARGET_REGIONS

def run_mass_ingestion(num_days: int = 30):
    """
    Executes the bulk ingestion protocol across all target regions.
    
    Args:
        num_days (int): The historical window size in days (default 30).
    """
    print("==================================================")
    print(" Initiating Enterprise Mass Ingestion Protocol")
    print(f" Target History Window: {num_days} days")
    print("==================================================\n")

    # Initialize API Clients
    weather_client = WeatherBase()
    aqi_client = AirQuality()

    # Iterate through State-level hierarchies
    for state, districts in TARGET_REGIONS.items():
        print(f"\n>>> PROCESSING STATE: {state.replace('_', ' ')} ({len(districts)} Districts) <<<")
        
        # Setup filesystem structure for data persistence
        state_data_dir = os.path.join(project_root, "weather_data", state)
        weather_client.data_dir = state_data_dir
        aqi_client.data_dir = state_data_dir

        # Process individual Districts within the State
        for district in districts:
            print(f"  -> Extracting data for {district}...")
            district_path = os.path.join(state_data_dir, district)
            os.makedirs(district_path, exist_ok=True)
            
            try:
                # 1. Geolocation Anchor: Resolve district names to Lat/Long coordinates
                if weather_client.geolocator(district):
                    
                    # 2. Extract Weather Data & Prune redundant features
                    w_df = weather_client.historic_data(num_days=num_days)
                    if w_df is not None:
                        w_df = w_df.drop(columns=[
                            'dew_point_2m', 'apparent_temperature', 'weather_code', 
                            'snowfall', 'precipitation'
                        ], errors='ignore')

                    # 3. Extract AQI Data & Prune redundant features
                    aqi_client.location = weather_client.location
                    aqi_client.place = district
                    a_df = aqi_client.air_quality_data(num_days=num_days)
                    if a_df is not None:
                        a_df = a_df.drop(columns=[
                            "ozone", "nitrogen_dioxide", "carbon_monoxide", 
                            "sulphur_dioxide", "carbon_dioxide"
                        ], errors='ignore')
                    
                    # 4. Data Integration: Merge Weather and AQI on 'time' index
                    if w_df is not None and a_df is not None:
                        merged_df = pd.merge(w_df, a_df, on='time', how='inner')

                        # 5. Feature Engineering: Trigonometric Periodic Encoding
                        # Converts 0-360 degrees into continuous Sin/Cos components
                        if 'wind_direction_10m' in merged_df.columns:
                            wind_radians = merged_df['wind_direction_10m'] * np.pi / 180
                            merged_df['wind_dir_sin'] = np.sin(wind_radians)
                            merged_df['wind_dir_cos'] = np.cos(wind_radians)
                            merged_df = merged_df.drop(columns=['wind_direction_10m'])

                        # 6. Persistence: Save unified matrix for ML Training
                        final_filename = "training_ready_unified.csv"
                        final_filepath = os.path.join(district_path, final_filename)
                        merged_df.to_csv(final_filepath, index=False)
                        print("      [SUCCESS] Unified Matrix Saved.")
                        
                        # 7. Cleanup: Purge raw cache files to maintain storage integrity
                        for filename in os.listdir(district_path):
                            if filename.endswith(".csv") and filename != final_filename:
                                file_to_delete = os.path.join(district_path, filename)
                                os.remove(file_to_delete)
                                print(f"      [CLEANUP] Deleted raw cache: {filename}")
                                
                    else:
                        print("      [PARTIAL DATA / FAIL] Missing API data.")
                else:
                    print("      [GEOLOCATION FAILED]")
                
                # API Rate Limiting: Respect Open-Meteo's non-commercial usage tier
                time.sleep(2.0) 
                
            except Exception as e:
                print(f"      [CRITICAL ERROR]: {e}")

    print("\n==================================================")
    print(" Mass Ingestion Protocol Complete.")
    print("==================================================")

if __name__ == "__main__":
    # Execute 1-year ingestion for high-variance seasonal training data
    run_mass_ingestion(num_days=365)