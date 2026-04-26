"""
ml_engine/master_training.py
Multi-Target XGBoost Training Orchestrator.

Automates the ingestion, training, and serialization of independent 
XGBoost regressors and classifiers for every district defined in the 
geospatial configuration.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import os
import sys
import pickle
import time
import numpy as np
import xgboost as xgb  # Primary Gradient Boosting Engine

# ─── Environment Configuration ────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from ml_engine.multi_target_pipeline import EnterpriseDataPipeline
from ml_engine.geography import TARGET_REGIONS

def execute_statewide_training(state_name: str, lag_hours: int = 72, forecast_horizon: int = 24):
    """
    Executes the training pipeline for all districts within a specified state.
    Generates and serializes individual .pkl models for each meteorological target.
    
    Args:
        state_name (str): The state to process, must exist in TARGET_REGIONS.
        lag_hours (int): The size of the historical lookback window.
        forecast_horizon (int): The future target prediction hour.
    """
    if state_name not in TARGET_REGIONS:
        raise ValueError(f"State '{state_name}' not found in geography constants.")
        
    districts = TARGET_REGIONS[state_name]
    state_dir = os.path.join(project_root, "weather_data", state_name)
    
    print("==================================================")
    print(f" Initiating Official Multi-Target XGBoost Engine")
    print(f" Target State: {state_name.replace('_', ' ')} ({len(districts)} Districts)")
    print("==================================================\n")

    start_time = time.time()

    for district in districts:
        print(f"\n>>> Processing District: {district} <<<")
        
        district_path = os.path.join(state_dir, district)
        if not os.path.exists(district_path):
            print(f"  [ERROR] Directory not found: {district_path}")
            continue
            
        target_csv = os.path.join(district_path, "training_ready_unified.csv")
        
        if not os.path.exists(target_csv):
            print(f"  [ERROR] Unified training matrix not found for {district}. Run ingestion first.")
            continue
        
        try:
            # Initialize Data Engineering Pipeline to extract targets
            pipeline = EnterpriseDataPipeline(target_csv, lag_hours=lag_hours, forecast_horizon=forecast_horizon)
            X_universal, y_targets_dict = pipeline.build_universal_matrices()
            
            # Convert Pandas DataFrame to raw NumPy array for max XGBoost efficiency
            X_numpy = X_universal.values 
            
            # Iterate through the isolated target variables (e.g., Temp, Rain)
            for variable_name, y_vector in y_targets_dict.items():
                model_filename = f"{district}_{variable_name}_model.pkl"
                model_path = os.path.join(district_path, model_filename)

                print(f"  -> Training Engine for: {variable_name}...", end=" ", flush=True)
                
                # ─── Algorithmic Bifurcation ───
                if 'rain' in variable_name:
                    # CLASSIFICATION: Optimize for rare precipitation events
                    model = xgb.XGBClassifier(
                        n_estimators=150,
                        max_depth=5,            
                        learning_rate=0.05,
                        scale_pos_weight=15,  # Force model to penalize missed rain heavily
                        n_jobs=-1,            # Utilize all CPU cores
                        random_state=42
                    )
                else:
                    # REGRESSION: Optimize for continuous meteorological variables
                    model = xgb.XGBRegressor(
                        n_estimators=100, 
                        max_depth=6, 
                        learning_rate=0.1, 
                        n_jobs=-1, 
                        random_state=42
                    )
                
                # Fit the model to the localized district data
                model.fit(X_numpy, y_vector.values)
                
                # Serialize the trained model binaries for inference
                with open(model_path, 'wb') as file:
                    pickle.dump(model, file)
                    
                print("[SAVED]")
                
        except Exception as e:
            print(f"  [CRITICAL ALGORITHM FAILURE in {district}]: {e}")

    execution_time = (time.time() - start_time) / 60
    print("\n==================================================")
    print(f" State Training Complete. Execution Time: {execution_time:.2f} minutes.")
    print("==================================================")

if __name__ == "__main__":
    # Execute full build cycle for the active project regions
    execute_statewide_training("Haryana", lag_hours=72, forecast_horizon=24)
    execute_statewide_training("West_Bengal", lag_hours=72, forecast_horizon=24)
    execute_statewide_training("Uttar_Pradesh", lag_hours=72, forecast_horizon=24)