import os
import sys
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    roc_auc_score, brier_score_loss
)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from ml_engine.multi_target_pipeline import EnterpriseDataPipeline

def evaluate_specialized_model(state_name: str, district_name: str, test_split_ratio: float = 0.2):
    print("==================================================")
    print(f" Executing Specialized Dual-Engine Evaluation: {district_name}")
    print("==================================================\n")

    district_path = os.path.join(project_root, "weather_data", state_name, district_name)
    target_csv = os.path.join(district_path, "training_ready_unified.csv")
    
    if not os.path.exists(target_csv):
        print("[ERROR] Unified CSV not found. Run ingestion first.")
        return

    # 1. Build the matrices (Outputs exactly 3 targets)
    pipeline = EnterpriseDataPipeline(target_csv, lag_hours=72, forecast_horizon=24)
    X_universal, y_targets_dict = pipeline.build_universal_matrices()
    X_numpy = X_universal.values

    # 2. Time-Series Split (80% Train, 20% Test)
    split_index = int(len(X_numpy) * (1 - test_split_ratio))
    X_train, X_test = X_numpy[:split_index], X_numpy[split_index:]
    
    print(f"-> Training Rows: {len(X_train)} | Testing Rows: {len(X_test)}\n")

    # 3. Evaluate Target Variables
    for var, y_vector in y_targets_dict.items():
        y_train = y_vector.values[:split_index]
        y_test = y_vector.values[split_index:]

        print(f"--- {var.upper()} ---")

        # ---------------------------------------------------------
        # PATH A: RAIN PROBABILITY (Meteorological PoP)
        # ---------------------------------------------------------
        if 'rain' in var:
            if sum(y_test) == 0:
                print("  [INFO] No rain events occurred in the 20% test timeframe.")
                continue

            eval_model = xgb.XGBClassifier(
                n_estimators=150, max_depth=5, learning_rate=0.05, 
                scale_pos_weight=15, n_jobs=-1, random_state=42
            )
            eval_model.fit(X_train, y_train)
            
            # We completely ignore .predict() and ONLY evaluate the raw percentages
            probabilities = eval_model.predict_proba(X_test)[:, 1]

            # Probabilistic Math
            auc = roc_auc_score(y_test, probabilities)
            brier = brier_score_loss(y_test, probabilities)

            print(f"  ROC-AUC     : {auc:.3f} (Ability to separate Rain vs No-Rain conditions)")
            print(f"  Brier Score : {brier:.3f} (Accuracy of the percentage. Closer to 0.0 is better.)")
            print(f"  Avg Rain %  : {np.mean(probabilities)*100:.1f}% (Average predicted chance of rain in test set)\n")

        # ---------------------------------------------------------
        # PATH B: THERMAL REGRESSION (Exact Numbers)
        # ---------------------------------------------------------
        else:
            eval_model = xgb.XGBRegressor(
                n_estimators=100, max_depth=6, learning_rate=0.1, 
                n_jobs=-1, random_state=42
            )
            eval_model.fit(X_train, y_train)
            
            predictions = eval_model.predict(X_test)
            
            # Regression Math
            mae = mean_absolute_error(y_test, predictions)
            rmse = np.sqrt(mean_squared_error(y_test, predictions))
            r2 = r2_score(y_test, predictions)

            print(f"  MAE       : {mae:.3f}")
            print(f"  RMSE      : {rmse:.3f}")
            print(f"  R^2 Score : {r2:.3f}\n")

if __name__ == "__main__":
    evaluate_specialized_model("Haryana", "Rohtak", test_split_ratio=0.2)