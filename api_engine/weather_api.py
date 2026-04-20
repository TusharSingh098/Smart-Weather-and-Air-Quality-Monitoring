import requests
import pandas as pd
import datetime
import os
import json

class WeatherBase:
    """
    Base client for retrieving meteorological data via the Open-Meteo API.
    Handles geocoding, state management, and historical data retrieval with local file caching.
    """
    def __init__(self):
        # Define API endpoints for geocoding and historical archive
        self.geo_endpoint = "/v1/search"
        self.geo_url = "https://geocoding-api.open-meteo.com"
        self.base_endpoint = "/v1/archive"
        self.base_url = "https://archive-api.open-meteo.com"

        # --- NEW ARCHITECTURAL PATH RESOLUTION ---
        # 1. os.path.abspath(__file__) gets the exact path of weather_api.py
        # 2. os.path.dirname() goes up one level to the 'api_engine' folder
        # 3. The second os.path.dirname() goes up to the 'WeatherPredictor' root
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define the absolute path to the secure data directory
        self.data_dir = os.path.join(self.project_root, "weather_data")
        
        # Define default meteorological variables for the API payload
        self.queries = [
            'temperature_2m', 'relative_humidity_2m', 'dew_point_2m',
            'apparent_temperature', 'rain', 'snowfall',
            'weather_code', 'wind_speed_10m', 'wind_direction_10m'
        ] 
        
        # Initialize state variables for location data
        self.location = None
        self.place = None

    def geolocator(self, place: str) -> bool:
        """
        Retrieves and caches geographic coordinates for a specified location.
        Checks the local file system for cached data before executing a network request.

        Args:
            place (str): The name of the city or location to geocode.

        Returns:
            bool: True if geolocation was successful (either from cache or API), False otherwise.
        """
        self.place = place
        file_path = os.path.join(self.data_dir, place, f"{place}.json")
        
        # Attempt to load location data from local cache
        try:
            if os.path.isfile(file_path):
                with open(file_path, "r") as fh:
                    self.location = json.load(fh)
                return True
        except json.JSONDecodeError as err:
            print(f"Cache read error (corrupted JSON): {err}. Proceeding with API request.")
        except Exception as err:
            print(f"File system error: {err}")
            
        # Execute network request if cache is unavailable or corrupted
        geo_payload = {"name": place, "language": "en", "format": "json", "count": "1"}
        
        try:
            geo = requests.get(self.geo_url + self.geo_endpoint, params=geo_payload, timeout=5)
            geo.raise_for_status()
            geo_data = geo.json()
            
            # Validate API response structure
            if ("results" not in geo_data) or (len(geo_data["results"]) == 0):
                print(f"Geocoding Error: No coordinates found for '{place}'.")
                return False
                
            self.location = geo_data["results"][0]

            # Cache the successful API response locally
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
        """
        Extracts the latitude and longitude from the cached location state.

        Returns:
            tuple: A tuple containing (latitude, longitude).

        Raises:
            ValueError: If the location state has not been initialized via geolocator().
        """
        if self.location is None:
            raise ValueError("State Error: Location not set. Execute geolocator() first.")
        return (self.location.get("latitude"), self.location.get("longitude"))

    def address(self) -> str:
        """
        Constructs a formatted address string from the geocoded location data.

        Returns:
            str: A comma-separated string of unique administrative boundaries.
            
        Raises:
            ValueError: If the location state has not been initialized.
        """
        if self.location is None:
            raise ValueError("State Error: Location not set. Execute geolocator() first.")
            
        # Compile available administrative fields
        address_parts = [
            self.location.get("name"), 
            self.location.get("admin3"), 
            self.location.get("admin2"), 
            self.location.get("admin1"), 
            self.location.get("country")
        ]
        
        # Filter None values and deduplicate while preserving order
        unique_parts = []
        for part in address_parts:
            if part and part not in unique_parts:
                unique_parts.append(part)
                
        return ", ".join(unique_parts)

    def historic_data(self, num_days: int = 7):
        """
        Fetches historical hourly weather data for a specified number of preceding days.

        Args:
            num_days (int): The number of days of historical data to retrieve. Defaults to 7.

        Returns:
            pd.DataFrame or None: A pandas DataFrame containing the hourly weather data, 
            or None if the request fails or location is unset.
        """
        if self.location is None:
            print("State Error: Cannot fetch data without a verified location.")
            return None
            
        # Calculate trailing date window
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
        return self.fetch_api_data(self.base_url + self.base_endpoint, payload, filename)

    def fetch_api_data(self, url: str, payload: dict, filename: str):
        """
        Executes the API GET request, processes the JSON response, and caches the data.

        Args:
            url (str): The target API endpoint URL.
            payload (dict): The query parameters for the API request.
            filename (str): The name of the file used for local CSV caching.

        Returns:
            pd.DataFrame or None: The formatted weather data, or None on failure.
        """
        if not self.place:
            print("System Error: 'self.place' is undefined. Run geolocator() first.")
            return None
            
        file_path = os.path.join(self.data_dir, self.place, filename)
        
        # Return cached DataFrame if it exists
        if os.path.isfile(file_path):
            return pd.read_csv(file_path, parse_dates=["time"])
            
        # Execute API request
        try:
            r = requests.get(url, params=payload, timeout=10)
            r.raise_for_status()
            r_dict = r.json()
            
            if "hourly" in r_dict:
                # Parse JSON payload into pandas DataFrame and cast datetimes
                df = pd.DataFrame(r_dict["hourly"])
                df['time'] = pd.to_datetime(df['time'])

                # Cache DataFrame to disk
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

class WeatherToday(WeatherBase):
    """
    Subclass of WeatherBase dedicated to retrieving current and future weather forecasts.
    Overrides base endpoints and query parameters to interface with the Open-Meteo Forecast API.
    """
    def __init__(self):
        super().__init__()
        
        # Override routing to Forecast API
        self.base_url = "https://api.open-meteo.com"
        self.base_endpoint = "/v1/forecast"
        
        # Override payload queries to include forecast-specific variables
        self.queries = [
            'temperature_2m', 'relative_humidity_2m',
            'apparent_temperature', 'rain', 'snowfall',
            'weather_code', 'wind_speed_10m', 
            'wind_direction_10m'
        ]

    def forecast_today(self):
        """
        Fetches the hourly weather forecast for the next 24 hours.

        Returns:
            pd.DataFrame or None: A pandas DataFrame containing the hourly forecast data,
            or None if the request fails or location is unset.
        """
        if not self.location: 
            return None
        
        lat, lon = self.coordinates()
        
        payload = {
            "latitude": lat, 
            "longitude": lon,
            "hourly": ",".join(self.queries),
            "timezone": "auto",
            "forecast_days": 1
        }
        
        filename = f"{datetime.date.today()}Today.csv"
        return self.fetch_api_data(self.base_url + self.base_endpoint, payload, filename)

class AirQuality(WeatherBase):
    """
    Subclass of WeatherBase dedicated to retrieving historical hourly air pollution metrics.
    Interfaces specifically with the Open-Meteo Air Quality API to generate time-series 
    datasets suitable for environmental and meteorological feature engineering.
    """
    def __init__(self):
        super().__init__()
        
        # Override routing to the Air Quality API subdomain
        self.aqi_url = "https://air-quality-api.open-meteo.com"
        self.aqi_endpoint = "/v1/air-quality"
        
        # Define default pollutant variables for the API payload
        self.queries = [
            "pm10", "pm2_5", "ozone", "nitrogen_dioxide",
            "carbon_monoxide", "sulphur_dioxide", "carbon_dioxide"
        ]

    def air_quality_data(self, num_days: int = 7):
        """
        Calculates a specific historical time window, constructs the API payload, and 
        triggers the data extraction process for hourly air quality metrics.

        Args:
            num_days (int): The number of retrospective days to extract data for. 
                            Defaults to 7. The extraction window strictly ends yesterday 
                            to ensure only complete 24-hour cycles are ingested.

        Returns:
            pd.DataFrame or None: A pandas DataFrame containing the historical hourly 
                                  pollutant data, or None if the request fails or 
                                  location is unset.
        """
        # Validate that geolocation state has been initialized
        if not self.location: 
            print("State Error: Cannot fetch air quality data without a verified location.")
            return None
            
        # Calculate trailing date window to prevent partial day ingestion (NaN errors)
        end_date = datetime.date.today() - datetime.timedelta(days=1)
        start_date = end_date - datetime.timedelta(days=num_days-1)
        
        # Extract coordinates from the parent class state
        lat, lon = self.coordinates()
        
        # Construct payload utilizing the API's native 'past_days' parameter
        payload = {
            "latitude": lat, 
            "longitude": lon,
            "hourly": ",".join(self.queries),
            "timezone": "auto",
            "past_days": num_days,
            "forecast_days": 0
        }
        
        # Construct a safe filename using the explicitly calculated date objects
        filename = f"{start_date}to{end_date}_AQI.csv"
        
        # Execute the HTTP request and caching logic inherited from WeatherBase
        return self.fetch_api_data(self.aqi_url + self.aqi_endpoint, payload, filename)