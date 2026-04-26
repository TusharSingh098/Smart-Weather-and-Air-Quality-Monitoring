import os
import sys
import pickle
import numpy as np
import matplotlib.pyplot as plt

# ─── Environment Configuration ────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

class ModelEvaluator:
    def __init__(self, state: str, district: str, lag_hours: int = 72):
        self.district = district
        self.lag_hours = lag_hours
        self.model_dir = os.path.join(project_root, "weather_data", state, district)
        self.analysis_dir = os.path.join(project_root, "logs", "analysis")
        os.makedirs(self.analysis_dir, exist_ok=True)
        
        # The exact feature order your pipeline uses
        self.base_features = [
            'temperature_2m', 'relative_humidity_2m', 'rain', 
            'wind_speed_10m', 'pm10', 'pm2_5', 'wind_dir_sin', 'wind_dir_cos'
        ]
        self.time_features = ['target_hour_sin', 'target_hour_cos', 'target_day_sin', 'target_day_cos']

    def plot_grouped_importance(self, target="temperature_2m_max"):
        """Calculates Information Gain and groups it by base meteorological variables."""
        model_path = os.path.join(self.model_dir, f"{self.district}_{target}_model.pkl")
        
        if not os.path.exists(model_path):
            print(f"[!] Model not found at: {model_path}")
            return

        # Load the trained brain
        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        # Extract raw feature importances (Information Gain)
        raw_importances = model.feature_importances_
        
        # Dictionary to hold the aggregated importance of each base variable
        grouped_importance = {var: 0.0 for var in self.base_features}
        grouped_importance['time_cycles'] = 0.0

        # Mathematically map the 580 flat columns back to their base variables
        current_idx = 0
        for var in self.base_features:
            # Sum the importances of all 72 lagged hours for this specific variable
            grouped_importance[var] = np.sum(raw_importances[current_idx : current_idx + self.lag_hours])
            current_idx += self.lag_hours
            
        # Sum the cyclical time encodings (the last 4 columns)
        grouped_importance['time_cycles'] = np.sum(raw_importances[current_idx : current_idx + len(self.time_features)])

        # Normalize to percentages (0 to 100%)
        total_importance = sum(grouped_importance.values())
        for key in grouped_importance:
            grouped_importance[key] = (grouped_importance[key] / total_importance) * 100

        # Sort the data for plotting
        sorted_vars = sorted(grouped_importance.items(), key=lambda item: item[1], reverse=False)
        labels = [item[0].replace('_', ' ').title() for item in sorted_vars]
        values = [item[1] for item in sorted_vars]

        # ─── Matplotlib Rendering ───
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bars = ax.barh(labels, values, color='#00E400', edgecolor='white')
        ax.set_xlabel('Information Gain (%)', fontsize=12, fontweight='bold')
        ax.set_title(f"AI Decision Drivers: {target.replace('_', ' ').title()} in {self.district}", fontsize=14, fontweight='bold')
        
        # Add value labels to the end of each bar
        for bar in bars:
            width = bar.get_width()
            ax.annotate(f'{width:.1f}%',
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(3, 0),  # 3 points offset
                        textcoords="offset points",
                        ha='left', va='center', fontweight='bold')

        plt.tight_layout()
        
        # Save the graph to the logs folder
        save_path = os.path.join(self.analysis_dir, f"{self.district}_{target}_importance.png")
        plt.savefig(save_path, dpi=300)
        print(f" -> Feature Importance chart saved successfully to: {save_path}")
        
        # Display to the user immediately
        plt.show()

if __name__ == "__main__":
    # Test the evaluator on Rohtak
    evaluator = ModelEvaluator(state="Haryana", district="Rohtak")
    print("Analyzing Maximum Temperature Model...")
    evaluator.plot_grouped_importance("temperature_2m_max")
    
    print("\nAnalyzing Rain Classification Model...")
    evaluator.plot_grouped_importance("rain_probability")