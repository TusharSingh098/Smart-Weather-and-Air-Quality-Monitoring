import os
from weather_api import WeatherBase, WeatherToday, AirQuality

def test_geolocator():
    print("\n--- Testing Geolocator ---")
    wb = WeatherBase()
    success = wb.geolocator("Moradabad")

    assert success, "Geolocation failed"
    print("Location fetched successfully")

    lat, lon = wb.coordinates()
    print(f"Coordinates: {lat}, {lon}")

    addr = wb.address()
    print(f"Address: {addr}")


def test_historic_data():
    print("\n--- Testing Historic Data ---")
    wb = WeatherBase()
    wb.geolocator("Moradabad")

    df = wb.historic_data(num_days=3)
    assert df is not None, "Historic data fetch failed"

    print(df.head())
    print("Rows:", len(df))


def test_forecast_today():
    print("\n--- Testing Forecast Today ---")
    wt = WeatherToday()
    wt.geolocator("Moradabad")

    df = wt.forecast_today()
    assert df is not None, "Forecast fetch failed"

    print(df.head())
    print("Rows:", len(df))


def test_air_quality():
    print("\n--- Testing Air Quality ---")
    aq = AirQuality()
    aq.geolocator("Moradabad")

    df = aq.air_quality_data(num_days=3)
    assert df is not None, "Air quality fetch failed"

    print(df.head())
    print("Rows:", len(df))


def test_cache():
    print("\n--- Testing Cache Mechanism ---")
    wb = WeatherBase()
    wb.geolocator("Moradabad")

    # First call (API hit)
    df1 = wb.historic_data(num_days=2)

    # Second call (should load from cache)
    df2 = wb.historic_data(num_days=2)

    assert df1.equals(df2), "Cache mismatch!"
    print("Cache working correctly")


if __name__ == "__main__":
    test_geolocator()
    test_historic_data()
    test_forecast_today()
    test_air_quality()
    test_cache()

    print("\n✅ All tests completed successfully!")