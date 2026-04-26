import os
import sys
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

# ─── Environment Configuration ────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Import your existing pipeline to generate the exact X and y matrices
from ml_engine.multi_target_pipeline import EnterpriseDataPipeline

class ResidualAnalyzer:
    def __init__(self, state: str, district: str):
        self.district = district
        self.data_path = os.path.join(project_root, "weather_data", state, district, "training_ready_unified.csv")
        self.model_dir = os.path.join(project_root, "weather_data", state, district)
        self.analysis_dir = os.path.join(project_root, "logs", "analysis")
        os.makedirs(self.analysis_dir, exist_ok=True)

    def analyze_residuals(self, target_name: str = "temperature_2m_max"):
        """Calculates and plots the error distribution (Actual - Predicted)."""
        print(f"Loading data for {self.district}...")
        
        # 1. Build the true matrices using your exact pipeline logic
        pipeline = EnterpriseDataPipeline(self.data_path, lag_hours=72, forecast_horizon=24)
        X_matrix, y_targets = pipeline.build_universal_matrices()
        
        # 2. Extract the actual target values
        if target_name not in y_targets:
            print(f"[!] Target {target_name} not found in pipeline output.")
            return
        actual_y = y_targets[target_name].values
        
        # 3. Load the trained model
        model_path = os.path.join(self.model_dir, f"{self.district}_{target_name}_model.pkl")
        if not os.path.exists(model_path):
            print(f"[!] Model not found at: {model_path}")
            return
            
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
            
        # 4. Generate Predictions for the entire historical dataset
        print(f"Running inference on {len(X_matrix)} historical data points...")
        predicted_y = model.predict(X_matrix)
        
        # 5. The Core Mathematics: Calculate the Residuals
        residuals = actual_y - predicted_y
        
        # Calculate statistical moments
        mean_res = np.mean(residuals)
        std_res = np.std(residuals)
        mae = np.mean(np.abs(residuals))
        
        print("\n--- Statistical Summary ---")
        print(f"Mean Absolute Error (MAE) : {mae:.2f}")
        print(f"Residual Mean (Bias)      : {mean_res:.3f}")
        print(f"Residual Std Deviation    : {std_res:.3f}")
        
        # 6. Matplotlib Rendering: The Bell Curve
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot the histogram of errors
        n, bins, patches = ax.hist(residuals, bins=50, density=True, color='#00E400', alpha=0.7, edgecolor='black')
        
        # Overlay the theoretical perfect Gaussian (Bell Curve)
        xmin, xmax = plt.xlim()
        x = np.linspace(xmin, xmax, 100)
        p = norm.pdf(x, mean_res, std_res)
        ax.plot(x, p, 'w', linewidth=2, label='Normal Distribution Fit')
        
        # Add a zero-error baseline
        ax.axvline(0, color='red', linestyle='dashed', linewidth=2, label='Perfect Prediction (Zero Error)')
        
        ax.set_xlabel('Error / Residual (°C)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency Density', fontsize=12, fontweight='bold')
        ax.set_title(f"Residual Analysis: {target_name.replace('_', ' ').title()} in {self.district}", fontsize=14, fontweight='bold')
        
        # Add the stats box
        stats_text = f"MAE: {mae:.2f}°C\nMean Bias: {mean_res:.2f}°C\nStd Dev: {std_res:.2f}°C"
        plt.text(0.95, 0.95, stats_text, transform=ax.transAxes, fontsize=11,
                 verticalalignment='top', horizontalalignment='right', 
                 bbox=dict(boxstyle='round', facecolor='black', alpha=0.8, edgecolor='white'))
                 
        ax.legend(loc='upper left')
        plt.tight_layout()
        
        # Save and display
        save_path = os.path.join(self.analysis_dir, f"{self.district}_{target_name}_residuals.png")
        plt.savefig(save_path, dpi=300)
        print(f" -> Residual chart saved successfully to: {save_path}")
        plt.show()

if __name__ == "__main__":
    analyzer = ResidualAnalyzer(state="Haryana", district="Rohtak")
    analyzer.analyze_residuals("temperature_2m_max")