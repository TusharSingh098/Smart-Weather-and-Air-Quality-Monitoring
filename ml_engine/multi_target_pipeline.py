import pandas as pd
import numpy as np
import os

class EnterpriseDataPipeline:
    def __init__(self, data_file_path: str, lag_hours: int = 72, forecast_horizon: int = 24):
        self.file_path = data_file_path
        self.lag_hours = lag_hours
        self.forecast_horizon = forecast_horizon
        
        print(f"Loading and healing data matrix from: {os.path.basename(self.file_path)}")
        self.df = pd.read_csv(self.file_path, parse_dates=["time"]).set_index("time")
        self.df = self.df.interpolate(method='time').bfill()
        
        self.variables = self.df.select_dtypes(include=[np.number]).columns.tolist()

    def build_universal_matrices(self) -> tuple:
        print(f"Engineering Universal Feature Matrix ({self.lag_hours}-hour lookback)...")
        
        new_columns_dict = {}
        feature_columns = []
        target_columns = []
        
        for var in self.variables:
            for i in range(1, self.lag_hours + 1):
                col_name = f"{var}_lag_{i}"
                new_columns_dict[col_name] = self.df[var].shift(i)
                feature_columns.append(col_name)
                
        for var in self.variables:
            target_name = f"{var}_target_{self.forecast_horizon}h"
            new_columns_dict[target_name] = self.df[var].shift(-self.forecast_horizon)
            target_columns.append(target_name)
            
        shifted_df = pd.DataFrame(new_columns_dict, index=self.df.index)
        
        working_df = pd.concat([self.df, shifted_df], axis=1)
            
        working_df = working_df.dropna(subset=feature_columns + target_columns)
        
        X_universal = working_df[feature_columns]
        
        y_dict = {}
        for var, target_name in zip(self.variables, target_columns):
            y_dict[var] = working_df[target_name]
            
        print(f"-> Universal X Matrix Shape: {X_universal.shape} ({len(feature_columns)} temporal dimensions)")
        print(f"-> Generated {len(y_dict)} independent target vectors ready for XGBoost routing.\n")
        
        return X_universal, y_dict

if __name__ == "__main__":
    test_file = os.path.join(os.getcwd(), "weather_data", "Haryana", "Rohtak", "YOUR_WEATHER_FILE_HERE.csv")
    
    if os.path.exists(test_file):
        pipeline = EnterpriseDataPipeline(test_file, lag_hours=72, forecast_horizon=24)
        X_matrix, y_targets = pipeline.build_universal_matrices()
        
        print(f"Sample Targets Available: {list(y_targets.keys())[:5]}...")
    else:
        print("Please update the test_file path to a valid CSV to test the matrix.")