import os
import mlflow.sklearn
from ml.datasets.feature_config import FEATURE_COLUMNS

class DriverCoachingEngine:
    """
    Inference engine that loads the ML model and predicts engine health.
    """
    def __init__(self, experiment_id="0"):
        self.model = None
        self.feature_columns = FEATURE_COLUMNS
        self._load_latest_model(experiment_id)

    def _load_latest_model(self, experiment_id):
        """Finds and loads the most recent model from the mlruns directory."""
        try:
            base_path = f"/{experiment_id}"
            if not os.path.exists(base_path):
                print(f"Error: Experiment path {base_path} not found.")
                return

            # Get all run directories and sort by creation time
            runs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
            if not runs:
                print("No runs found in mlruns.")
                return

            # Sort runs by folder modification time (latest first)
            latest_run = max(runs, key=lambda d: os.path.getmtime(os.path.join(base_path, d)))
            model_path = os.path.join(base_path, latest_run, "artifacts", "model")
            
            self.model = mlflow.sklearn.load_model(model_path)
            print(f"Successfully loaded LATEST model from run: {latest_run}")
        except Exception as e:
            print(f"Failed to load model: {e}")

    def predict_health(self, features_dict):
        """Returns the predicted health score based on input features."""
        if self.model is None:
            return 100.0
        
        import pandas as pd
        # Create DataFrame and ensure the order of columns matches training
        df = pd.DataFrame([features_dict])[self.feature_columns]
        
        # Get prediction (assuming it returns an array with one value)
        prediction = self.model.predict(df)
        return float(prediction[0])