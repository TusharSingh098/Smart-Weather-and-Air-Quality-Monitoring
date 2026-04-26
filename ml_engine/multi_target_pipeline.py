"""
ml_engine/multi_target_pipeline.py
Time-Series to Supervised Learning Transformation Pipeline.

This Object-Oriented module ingests unified temporal data and engineers 
high-dimensional lag matrices (X) alongside shifted future target vectors (y) 
for direct ingestion into XGBoost.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import pandas as pd
import numpy as np
import os
import sys

# ─── Environment Configuration ────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

class EnterpriseDataPipeline:
    """
    An Object-Oriented data processing pipeline for temporal matrix construction.
    """
    
    # The __init__ method is the constructor. It initializes the object's state when created.
    def __init__(self, data_path: str, lag_hours: int = 72, forecast_horizon: int = 24):
        self.data_path = data_path
        self.lag_hours = lag_hours
        self.forecast_horizon = forecast_horizon
        
        print(f"Loading and healing data matrix from: {data_path.split('/')[-1]}")
        
        # Load the CSV and set the 'time' column as the DataFrame's primary index
        self.df = pd.read_csv(self.data_path)
        self.df['time'] = pd.to_datetime(self.df['time'])
        self.df.set_index('time', inplace=True)
        
        # Data Healing: Forward-fill (ffill) and Backward-fill (bfill) to eliminate NaNs
        self.df = self.df.ffill().bfill()
        
        # Define the base variables that will be duplicated into lag features
        self.feature_variables = [
            'temperature_2m', 'relative_humidity_2m', 'rain', 
            'wind_speed_10m', 'pm10', 'pm2_5', 'wind_dir_sin', 'wind_dir_cos'
        ]
        
        # Define the variables the ML engine is trying to predict
        self.target_variables = ['temperature_2m_max', 'temperature_2m_min', 'relative_humidity_2m', 'rain']

    def build_universal_matrices(self) -> tuple:
        """
        Transforms the 1D time-series DataFrame into a 2D Supervised Learning Matrix.
        
        Returns:
            tuple: (X_universal_matrix, dictionary_of_y_targets)
        """
        print(f"Engineering Universal Feature Matrix ({self.lag_hours}-hour lookback)...")
        
        new_columns_dict = {}
        feature_columns = []
        target_columns = []
        
        # 1. Construct the Lag Features (The 'Past')
        for var in self.feature_variables:
            for i in range(1, self.lag_hours + 1):
                col_name = f"{var}_lag_{i}"
                # .shift(i) pushes the data down by 'i' rows. 
                # This effectively brings past data onto the current timestamp's row.
                new_columns_dict[col_name] = self.df[var].shift(i)
                feature_columns.append(col_name)
                
        # 2. Construct the Target Variables (The 'Future')
        for var in self.target_variables:
            if var == 'temperature_2m_max':
                # TARGET: The MAXIMUM temperature over the entire next 24-hour block
                target_name = f"{var}_target_{self.forecast_horizon}h"
                new_columns_dict[target_name] = self.df['temperature_2m'].rolling(window=self.forecast_horizon).max().shift(-self.forecast_horizon)

            elif var == 'temperature_2m_min':
                # TARGET: The MINIMUM temperature
                # Note: We pull from the base 'temperature_2m' column to find the minimum
                target_name = f"{var}_target_{self.forecast_horizon}h"
                new_columns_dict[target_name] = self.df['temperature_2m'].rolling(window=self.forecast_horizon).min().shift(-self.forecast_horizon)
                
            elif var == 'relative_humidity_2m':
                # TARGET: The AVERAGE humidity over the entire next 24-hour block
                target_name = f"{var}_target_{self.forecast_horizon}h"
                new_columns_dict[target_name] = self.df[var].rolling(window=self.forecast_horizon).mean().shift(-self.forecast_horizon)
                
            elif var == 'rain':
                # TARGET: Will it rain AT ALL (sum > 0) in the next 24-hour block?
                target_name = f"{var}_class_target_{self.forecast_horizon}h"
                new_columns_dict[target_name] = (self.df[var].rolling(window=self.forecast_horizon).sum().shift(-self.forecast_horizon) > 0).astype(int)
            
            target_columns.append(target_name)
            
        # Compile all shifted columns efficiently using dictionary unpacking
        shifted_df = pd.DataFrame(new_columns_dict, index=self.df.index)
        working_df = pd.concat([self.df, shifted_df], axis=1)
        
        # 3. Cyclical Encoding of the Target Horizon
        # We calculate exactly what time/day it will be when the forecast matures
        target_time = pd.DatetimeIndex(working_df.index + pd.Timedelta(hours=self.forecast_horizon))
        
        # Convert diurnal (24h) and seasonal (365d) cycles into continuous sine/cosine waves
        working_df['target_hour_sin'] = np.sin(2 * np.pi * target_time.hour / 24)
        working_df['target_hour_cos'] = np.cos(2 * np.pi * target_time.hour / 24)
        working_df['target_day_sin'] = np.sin(2 * np.pi * target_time.dayofyear / 365.25)
        working_df['target_day_cos'] = np.cos(2 * np.pi * target_time.dayofyear / 365.25)
        
        time_features = ['target_hour_sin', 'target_hour_cos', 'target_day_sin', 'target_day_cos']
        feature_columns.extend(time_features)

        # Drop any rows that contain NaNs (inevitable at the very beginning and end of the dataset due to shifting)
        working_df = working_df.dropna(subset=feature_columns + target_columns)
        
        # 4. Final Matrix Separation
        X_universal = working_df[feature_columns]
        
        X_universal = working_df[feature_columns]
        
        y_dict = {
            'temperature_2m_max': working_df[f"temperature_2m_max_target_{self.forecast_horizon}h"],
            'temperature_2m_min': working_df[f"temperature_2m_min_target_{self.forecast_horizon}h"],
            'relative_humidity_2m': working_df[f"relative_humidity_2m_target_{self.forecast_horizon}h"],
            'rain_probability': working_df[f"rain_class_target_{self.forecast_horizon}h"]
        }
            
        print(f"-> Universal X Matrix Shape: {X_universal.shape} ({len(feature_columns)} dimensions)")
        print(f"-> Generated {len(y_dict)} core target vectors.\n")
        
        return X_universal, y_dict

if __name__ == "__main__":
    # Development testing block: Ensure the matrix builds successfully on a known dataset
    test_file = os.path.join(project_root, "weather_data", "Haryana", "Rohtak", "training_ready_unified.csv")
    
    if os.path.exists(test_file):
        pipeline = EnterpriseDataPipeline(test_file, lag_hours=72, forecast_horizon=24)
        X_matrix, y_targets = pipeline.build_universal_matrices()
        
        print(f"Sample Targets Available: {list(y_targets.keys())[:5]}...")
    else:
        print("Please update the test_file path to a valid CSV to test the matrix.")