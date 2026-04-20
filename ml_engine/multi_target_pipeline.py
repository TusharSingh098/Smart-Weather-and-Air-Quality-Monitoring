import pandas as pd
import numpy as np
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

class EnterpriseDataPipeline:
    def __init__(self, data_path: str, lag_hours: int = 72, forecast_horizon: int = 24):
        self.data_path = data_path
        self.lag_hours = lag_hours
        self.forecast_horizon = forecast_horizon
        
        print(f"Loading and healing data matrix from: {data_path.split('/')[-1]}")
        self.df = pd.read_csv(self.data_path)
        self.df['time'] = pd.to_datetime(self.df['time'])
        self.df.set_index('time', inplace=True)
        self.df = self.df.ffill().bfill()
        
        self.feature_variables = [
            'temperature_2m', 'relative_humidity_2m', 'rain', 
            'wind_speed_10m', 'pm10', 'pm2_5', 'wind_dir_sin', 'wind_dir_cos'
        ]
        
        self.target_variables = ['temperature_2m', 'relative_humidity_2m', 'rain']

    def build_universal_matrices(self) -> tuple:
        print(f"Engineering Universal Feature Matrix ({self.lag_hours}-hour lookback)...")
        
        new_columns_dict = {}
        feature_columns = []
        target_columns = []
        
        for var in self.feature_variables:
            for i in range(1, self.lag_hours + 1):
                col_name = f"{var}_lag_{i}"
                new_columns_dict[col_name] = self.df[var].shift(i)
                feature_columns.append(col_name)
                
        for var in self.target_variables:
            if var == 'rain':
                target_name = f"{var}_class_target_{self.forecast_horizon}h"
                new_columns_dict[target_name] = (self.df[var].shift(-self.forecast_horizon) > 0).astype(int)
            else:
                target_name = f"{var}_target_{self.forecast_horizon}h"
                new_columns_dict[target_name] = self.df[var].shift(-self.forecast_horizon)
            
            target_columns.append(target_name)
            
        shifted_df = pd.DataFrame(new_columns_dict, index=self.df.index)
        working_df = pd.concat([self.df, shifted_df], axis=1)
        
        target_time = pd.DatetimeIndex(working_df.index + pd.Timedelta(hours=self.forecast_horizon))
        working_df['target_hour_sin'] = np.sin(2 * np.pi * target_time.hour / 24)
        working_df['target_hour_cos'] = np.cos(2 * np.pi * target_time.hour / 24)
        working_df['target_day_sin'] = np.sin(2 * np.pi * target_time.dayofyear / 365.25)
        working_df['target_day_cos'] = np.cos(2 * np.pi * target_time.dayofyear / 365.25)
        
        time_features = ['target_hour_sin', 'target_hour_cos', 'target_day_sin', 'target_day_cos']
        feature_columns.extend(time_features)

        working_df = working_df.dropna(subset=feature_columns + target_columns)
        
        X_universal = working_df[feature_columns]
        
        y_dict = {
            'temperature_2m': working_df[f"temperature_2m_target_{self.forecast_horizon}h"],
            'relative_humidity_2m': working_df[f"relative_humidity_2m_target_{self.forecast_horizon}h"],
            'rain_probability': working_df[f"rain_class_target_{self.forecast_horizon}h"]
        }
            
        print(f"-> Universal X Matrix Shape: {X_universal.shape} ({len(feature_columns)} dimensions)")
        print(f"-> Generated {len(y_dict)} core target vectors.\n")
        
        return X_universal, y_dict

if __name__ == "__main__":
    test_file = os.path.join(project_root, "weather_data", "Haryana", "Rohtak", "training_ready_unified.csv")
    
    if os.path.exists(test_file):
        pipeline = EnterpriseDataPipeline(test_file, lag_hours=72, forecast_horizon=24)
        X_matrix, y_targets = pipeline.build_universal_matrices()
        
        print(f"Sample Targets Available: {list(y_targets.keys())[:5]}...")
    else:
        print("Please update the test_file path to a valid CSV to test the matrix.")