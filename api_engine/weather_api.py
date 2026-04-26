"""
api_engine/weather_api.py
Asynchronous Geocoding & Open-Meteo REST Client.

Provides Object-Oriented wrappers for the Open-Meteo API suite. 
Features defensive local file caching to respect rate limits and 
ensure high-speed data ingestion for the ML pipelines.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import requests
import pandas as pd
import datetime
import os
import json

class WeatherBase:
    """
    Core HTTP Client and Caching Engine.
    Handles coordinate resolution, error trapping, and JSON-to-Pandas serialization.
    """
    def __init__(self):
        # Define base Open-Meteo endpoints
        self.geo_endpoint = "/v1/search"
        self.geo_url = "https://geocoding-api.open-meteo.com"
        self.base_endpoint = "/v1/archive"
        self.base_url = "https://archive-api.open-meteo.com"

        # ─── Dynamic Path Resolution ───
        # Ensures the data directory is correctly mapped regardless of where the script is executed
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.project_root, "weather_data")
        
        # Standardized meteorological feature extraction list
        self.queries = [
            'temperature_2m', 'relative_humidity_2m', 'dew_point_2m',
            'apparent_temperature', 'rain', 'snowfall',
            'weather_code', 'wind_speed_10m', 'wind_direction_10m'
        ] 
        
        self.location = None
        self.place = None

    def geolocator(self, place: str) -> bool:
        """
        Translates a city string into latitude/longitude coordinates.
        Checks local disk cache before executing an external HTTP request.
        """
        self.place = place
        file_path = os.path.join(self.data_dir, place, f"{place}.json")
        
        # 1. Local Cache Interception
        try:
            if os.path.isfile(file_path):
                with open(file_path, "r") as fh:
                    self.location = json.load(fh)
                return True
        except json.JSONDecodeError as err:
            print(f"Cache read error (corrupted JSON): {err}. Proceeding with API request.")
        except Exception as err:
            print(f"File system error: {err}")
            
        # 2. External Network Execution
        geo_payload = {"name": place, "language": "en", "format": "json", "count": "1"}
        
        try:
            geo = requests.get(self.geo_url + self.geo_endpoint, params=geo_payload, timeout=5)
            geo.raise_for_status() # Trigger exception for 4xx/5xx server errors
            geo_data = geo.json()
            
            if ("results" not in geo_data) or (len(geo_data["results"]) == 0):
                print(f"Geocoding Error: No coordinates found for '{place}'.")
                return False
                
            self.location = geo_data["results"][0]

            # 3. Disk Persistence (Caching the result for future use)
            try:
                folder_path = os.path.dirname(file_path) 
                os.makedirs(folder_path, exist_ok=True)
                with open(file_path, "w") as fh:
                    json.dump(self.location, fh, indent=4)
            except Exception as err:
                print(f"Cache write error: {err}")
                
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Network Request Error: {e}")
            return False
    
    def coordinates(self) -> tuple:
        """Safely extracts the lat/lon floats from the geocoded payload."""
        if self.location is None:
            raise ValueError("State Error: Location not set. Execute geolocator() first.")
        return (self.location.get("latitude"), self.location.get("longitude"))

    def address(self) -> str:
        """Constructs a clean, human-readable hierarchy (e.g., 'Rohtak, Haryana, India')."""
        if self.location is None:
            raise ValueError("State Error: Location not set. Execute geolocator() first.")
            
        address_parts = [
            self.location.get("name"), 
            self.location.get("admin3"), 
            self.location.get("admin2"), 
            self.location.get("admin1"), 
            self.location.get("country")
        ]
        
        # Deduplicate while preserving order (removes None values)
        unique_parts = []
        for part in address_parts:
            if part and part not in unique_parts:
                unique_parts.append(part)
                
        return ", ".join(unique_parts)

    def historic_data(self, num_days: int = 7):
        """Constructs the payload for the historical Archive API."""
        if self.location is None:
            return None
            
        # Ensure extraction window ends strictly yesterday to avoid partial-day NaNs
        end_date = datetime.date.today() - datetime.timedelta(days=1)
        start_date = end_date - datetime.timedelta(days=num_days-1)
        lat, lon = self.coordinates()
        
        payload = {
            "latitude": lat, 
            "longitude": lon, 
            "start_date": str(start_date), 
            "end_date": str(end_date),
            "hourly": ",".join(self.queries),
            "timezone": "auto"
        } 
        
        filename = f"{payload['start_date']}to{payload['end_date']}Weather.csv"
        # Delegate HTTP execution to the shared base function
        return self.fetch_api_data(self.base_url + self.base_endpoint, payload, filename)

    def fetch_api_data(self, url: str, payload: dict, filename: str):
        """
        The Core I/O Engine. 
        Executes HTTP requests, transforms JSON to Pandas, and handles disk serialization.
        """
        if not self.place:
            return None
            
        file_path = os.path.join(self.data_dir, self.place, filename)
        
        # 1. Local Cache Interception
        if os.path.isfile(file_path):
            return pd.read_csv(file_path, parse_dates=["time"])
            
        # 2. HTTP Network Request
        try:
            r = requests.get(url, params=payload, timeout=10)
            r.raise_for_status()
            r_dict = r.json()
            
            if "hourly" in r_dict:
                # 3. Data Transformation
                df = pd.DataFrame(r_dict["hourly"])
                df['time'] = pd.to_datetime(df['time'])

                # 4. Disk Persistence
                try:
                    folder_path = os.path.dirname(file_path) 
                    os.makedirs(folder_path, exist_ok=True)
                    df.to_csv(file_path, index=False, sep=",", encoding="utf-8")
                except Exception as err:
                    print(f"I/O Error saving CSV cache: {err}")
                    
                return df
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Failed: {e}")
            return None

# ─── Subclass Implentations ──────────────────────────────────────────────────

class WeatherToday(WeatherBase):
    """Overrides WeatherBase to target the live T-Zero Forecast API."""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.open-meteo.com"
        self.base_endpoint = "/v1/forecast"
        
        self.queries = [
            'temperature_2m', 'relative_humidity_2m',
            'apparent_temperature', 'rain', 'snowfall',
            'weather_code', 'wind_speed_10m', 'wind_direction_10m'
        ]

    def forecast_today(self):
        """Constructs a 24-hour forward-looking payload."""
        if not self.location: 
            return None
        
        lat, lon = self.coordinates()
        payload = {
            "latitude": lat, 
            "longitude": lon,
            "hourly": ",".join(self.queries),
            "timezone": "auto",
            "forecast_days": 1 # Request strictly tomorrow's data
        }
        
        filename = f"{datetime.date.today()}Today.csv"
        return self.fetch_api_data(self.base_url + self.base_endpoint, payload, filename)

class AirQuality(WeatherBase):
    """Overrides WeatherBase to target the specific Environmental API."""
    def __init__(self):
        super().__init__()
        self.aqi_url = "https://air-quality-api.open-meteo.com"
        self.aqi_endpoint = "/v1/air-quality"
        
        self.queries = [
            "pm10", "pm2_5", "ozone", "nitrogen_dioxide",
            "carbon_monoxide", "sulphur_dioxide", "carbon_dioxide"
        ]

    def air_quality_data(self, num_days: int = 7):
        """Constructs a payload utilizing the API's native 'past_days' parameter."""
        if not self.location: 
            return None
            
        end_date = datetime.date.today() - datetime.timedelta(days=1)
        start_date = end_date - datetime.timedelta(days=num_days-1)
        lat, lon = self.coordinates()
        
        payload = {
            "latitude": lat, 
            "longitude": lon,
            "hourly": ",".join(self.queries),
            "timezone": "auto",
            "past_days": num_days,
            "forecast_days": 0
        }
        
        filename = f"{start_date}to{end_date}_AQI.csv"
        return self.fetch_api_data(self.aqi_url + self.aqi_endpoint, payload, filename)