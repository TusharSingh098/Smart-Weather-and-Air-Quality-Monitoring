import os
import pandas as pd
import datetime

class PerformanceMonitor:
    def __init__(self, project_root):
        self.log_path = os.path.join(project_root, "logs", "prediction_audit.csv")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        # Initialize the CSV if it doesn't exist
        if not os.path.exists(self.log_path):
            df = pd.DataFrame(columns=[
                "timestamp_made", "target_date", "state", "district",
                "pred_max", "actual_max", "pred_min", "actual_min", "status"
            ])
            df.to_csv(self.log_path, index=False)

    def log_prediction(self, state, district, target_date, pred_max, pred_min):
        """Records a new prediction to be verified later."""
        new_entry = {
            "timestamp_made": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "target_date": target_date, # Format: YYYY-MM-DD
            "state": state,
            "district": district,
            "pred_max": round(pred_max, 2),
            "pred_min": round(pred_min, 2),
            "actual_max": None,
            "actual_min": None,
            "status": "Pending"
        }
        df = pd.read_csv(self.log_path)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(self.log_path, index=False)
        print(f" -> Prediction logged for audit: {target_date}")

    def calculate_mae(self):
        """Calculates the current scientific accuracy of the system."""
        df = pd.read_csv(self.log_path)
        completed = df[df['status'] == 'Verified']
        
        if completed.empty:
            return 0.0
            
        mae = (completed['actual_max'] - completed['pred_max']).abs().mean()
        return round(mae, 2)