import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from api_engine.weather_api import WeatherBase, AirQuality
from ml_engine.geography import TARGET_REGIONS

def run_mass_ingestion(num_days: int = 30):
    print("==================================================")
    print(" Initiating Enterprise Mass Ingestion Protocol")
    print(f" Target History Window: {num_days} days")
    print("==================================================\n")

    weather_client = WeatherBase()
    aqi_client = AirQuality()

    for state, districts in TARGET_REGIONS.items():
        print(f"\n>>> PROCESSING STATE: {state.replace('_', ' ')} ({len(districts)} Districts) <<<")
        
        state_data_dir = os.path.join(project_root, "weather_data", state)
        weather_client.data_dir = state_data_dir
        aqi_client.data_dir = state_data_dir

        for district in districts:
            print(f"  -> Extracting data for {district}...", end=" ")
            
            try:
                if weather_client.geolocator(district):
                    
                    w_df = weather_client.historic_data(num_days=num_days)
                    
                    aqi_client.location = weather_client.location
                    aqi_client.place = district
                    a_df = aqi_client.air_quality_data(num_days=num_days)
                    
                    if w_df is not None and a_df is not None:
                        print("[SUCCESS]")
                    else:
                        print("[PARTIAL DATA / FAIL]")
                else:
                    print("[GEOLOCATION FAILED]")
                
                time.sleep(2.0) 
                
            except Exception as e:
                print(f"[CRITICAL ERROR]: {e}")

    print("\n==================================================")
    print(" Mass Ingestion Protocol Complete.")
    print("==================================================")

if __name__ == "__main__":
    run_mass_ingestion(num_days=30)