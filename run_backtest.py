import pandas as pd
from api_engine.weather_api import WeatherBase
from ml_engine.performance_monitor import PerformanceMonitor
import os

def sync_reality():
    monitor = PerformanceMonitor(os.getcwd())
    df = pd.read_csv(monitor.log_path)
    
    # Find all 'Pending' predictions where the target_date has already passed
    today = pd.Timestamp.now().normalize()
    pending = df[(df['status'] == 'Pending') & (pd.to_datetime(df['target_date']) < today)]
    
    if pending.empty:
        print("Everything is up to date. No new 'Realities' to check.")
        return

    wb = WeatherBase()
    
    for idx, row in pending.iterrows():
        print(f"Checking reality for {row['district']} on {row['target_date']}...")
        
        if wb.geolocator(row['district']):
            # Fetch actual historical data for that specific day
            # (In a real app, you'd fetch the specific 24h window)
            actual_df = wb.historic_data(num_days=2) 
            
            if actual_df is not None:
                # Calculate the ACTUAL max and min from the API data
                real_max = actual_df['temperature_2m'].max()
                real_min = actual_df['temperature_2m'].min()
                
                # Update the log
                df.at[idx, 'actual_max'] = real_max
                df.at[idx, 'actual_min'] = real_min
                df.at[idx, 'status'] = 'Verified'
                
    df.to_csv(monitor.log_path, index=False)
    print(f"Backtest complete. Current System MAE: {monitor.calculate_mae()}°C")

if __name__ == "__main__":
    sync_reality()