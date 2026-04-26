"""
ml_engine/model_evaluator.py
Dual-Engine Validation and Performance Auditing Module.

Applies chronological time-series splitting to unified datasets to simulate 
future forecasting. Evaluates multi-target XGBoost models using rigorous 
regression and probabilistic classification metrics.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import os
import sys
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    roc_auc_score, brier_score_loss
)

# ─── Environment Configuration ────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from ml_engine.multi_target_pipeline import EnterpriseDataPipeline

def evaluate_specialized_model(state_name: str, district_name: str, test_split_ratio: float = 0.2):
    """
    Simulates training and future-inference to audit model precision.
    
    Args:
        state_name (str): Target state.
        district_name (str): Target district to audit.
        test_split_ratio (float): Percentage of sequential future data reserved for testing.
    """
    print("==================================================")
    print(f" Executing Specialized Dual-Engine Evaluation: {district_name}")
    print("==================================================\n")

    district_path = os.path.join(project_root, "weather_data", state_name, district_name)
    target_csv = os.path.join(district_path, "training_ready_unified.csv")
    
    if not os.path.exists(target_csv):
        print("[ERROR] Unified CSV not found. Run ingestion first.")
        return

    # 1. Feature Engineering: Build identical matrices used in deployment
    pipeline = EnterpriseDataPipeline(target_csv, lag_hours=72, forecast_horizon=24)
    X_universal, y_targets_dict = pipeline.build_universal_matrices()
    X_numpy = X_universal.values

    # 2. Chronological Time-Series Split (No random shuffling to prevent data leakage)
    split_index = int(len(X_numpy) * (1 - test_split_ratio))
    X_train, X_test = X_numpy[:split_index], X_numpy[split_index:]
    
    print(f"-> Training Rows: {len(X_train)} | Testing Rows: {len(X_test)}\n")

    # 3. Dynamic Evaluation Loop for Multi-Target Outputs
    for var, y_vector in y_targets_dict.items():
        y_train = y_vector.values[:split_index]
        y_test = y_vector.values[split_index:]

        print(f"--- {var.upper()} ---")

        # ---------------------------------------------------------
        # PATH A: RAIN PROBABILITY (Probabilistic Classification)
        # ---------------------------------------------------------
        if 'rain' in var:
            # Mathematical validation: Ensure minority class exists in test set to avoid division by zero
            if sum(y_test) == 0:
                print("  [INFO] No rain events occurred in the 20% test timeframe.")
                continue

            # Instantiate and fit temporary auditing model
            eval_model = xgb.XGBClassifier(
                n_estimators=150, max_depth=5, learning_rate=0.05, 
                scale_pos_weight=15, n_jobs=-1, random_state=42
            )
            eval_model.fit(X_train, y_train)
            
            # Extract raw percentages of the positive class (Rain = 1)
            probabilities = eval_model.predict_proba(X_test)[:, 1]

            # Calculate Probabilistic Metrics
            auc = roc_auc_score(y_test, probabilities)
            brier = brier_score_loss(y_test, probabilities)

            print(f"  ROC-AUC     : {auc:.3f} (Ability to separate Rain vs No-Rain conditions)")
            print(f"  Brier Score : {brier:.3f} (Accuracy of the percentage. Closer to 0.0 is better.)")
            print(f"  Avg Rain %  : {np.mean(probabilities)*100:.1f}% (Average predicted chance of rain in test set)\n")

        # ---------------------------------------------------------
        # PATH B: THERMAL REGRESSION (Continuous Deterministic Output)
        # ---------------------------------------------------------
        else:
            # Instantiate and fit temporary auditing model
            eval_model = xgb.XGBRegressor(
                n_estimators=100, max_depth=6, learning_rate=0.1, 
                n_jobs=-1, random_state=42
            )
            eval_model.fit(X_train, y_train)
            
            # Predict exact floating-point numerical values
            predictions = eval_model.predict(X_test)
            
            # Calculate Error Magnitude Metrics
            mae = mean_absolute_error(y_test, predictions)
            rmse = np.sqrt(mean_squared_error(y_test, predictions))
            r2 = r2_score(y_test, predictions)

            print(f"  MAE       : {mae:.3f} °C/%")
            print(f"  RMSE      : {rmse:.3f} °C/%")
            print(f"  R^2 Score : {r2:.3f}\n")

if __name__ == "__main__":
    # Localized baseline audit: Evaluates the system's efficacy on the Rohtak dataset
    evaluate_specialized_model("Haryana", "Rohtak", test_split_ratio=0.2)