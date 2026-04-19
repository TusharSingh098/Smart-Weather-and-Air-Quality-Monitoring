import os
import sys
import pickle
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from ml_engine.multi_target_pipeline import EnterpriseDataPipeline
from ml_engine.custom_xgboost import CustomXGBRegressor
from ml_engine.geography import TARGET_REGIONS

def execute_statewide_training(state_name: str, lag_hours: int = 72, forecast_horizon: int = 24):
    """
    Iterates through every district in a target state, generates the Universal X Matrix,
    and trains an independent XGBoost model for every meteorological and AQI variable.
    """
    if state_name not in TARGET_REGIONS:
        raise ValueError(f"State '{state_name}' not found in geography constants.")
        
    districts = TARGET_REGIONS[state_name]
    state_dir = os.path.join(project_root, "weather_data", state_name)
    
    print("==================================================")
    print(f" Initiating Multi-Target XGBoost Training")
    print(f" Target State: {state_name.replace('_', ' ')} ({len(districts)} Districts)")
    print("==================================================\n")

    start_time = time.time()

    for district in districts:
        print(f"\n>>> Processing District: {district} <<<")
        
        district_path = os.path.join(state_dir, district)
        if not os.path.exists(district_path):
            print(f"  [ERROR] Directory not found: {district_path}")
            continue
            
        csv_files = [f for f in os.listdir(district_path) if f.endswith('.csv')]
        if not csv_files:
            print(f"  [ERROR] No CSV data found for {district}. Run extraction first.")
            continue
            
        target_csv = os.path.join(district_path, csv_files[-1])
        
        try:
            pipeline = EnterpriseDataPipeline(target_csv, lag_hours=lag_hours, forecast_horizon=forecast_horizon)
            X_universal, y_targets_dict = pipeline.build_universal_matrices()
            
            X_matrix_values = X_universal.values
            
            for variable_name, y_vector in y_targets_dict.items():
                print(f"  -> Training Custom XGBoost for: {variable_name}...", end=" ")
                
                model = CustomXGBRegressor()
                model.fit(
                    X_train=X_matrix_values, 
                    y_train=y_vector.values, 
                    n_trees=15,
                    eta=0.2, 
                    max_depth=4 
                )
                
                model_filename = f"{district}_{variable_name}_model.pkl"
                model_path = os.path.join(district_path, model_filename)
                
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
    execute_statewide_training("Haryana", lag_hours=72, forecast_horizon=24)
    
    input("\nExecution Complete. Press the Enter key to close this window...")