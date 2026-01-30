import collections
import numpy as np
import pandas as pd
import mlflow.sklearn
from ml.datasets.feature_config import FEATURE_COLUMNS

class AIInferenceEngine:
    """
    Real-time inference engine that consumes simulation ticks and predicts 
    driving behavior using a loaded MLflow model.
    """
    def __init__(self, run_id: str):
        """
        Initializes the engine by loading a specific model version from MLflow 
        and setting up a sliding window buffer.
        """
        model_uri = f"runs:/{run_id}/model"
        self.model = mlflow.sklearn.load_model(model_uri)
        # Buffer stores 300 ticks (approx. 10s at 30Hz)
        self.buffer = collections.deque(maxlen=300)

    def add_sample(self, rpm: float, throttle: float, load: float, speed: float, gear: int):
        """
        Adds a single telemetry data point to the sliding window buffer.
        """
        self.buffer.append({
            "engine_rpm": rpm, 
            "throttle": throttle, 
            "load": load, 
            "speed_kmh": speed, 
            "current_gear": gear
        })

    def get_prediction(self):
        """
        Calculates window-based features and returns the model's prediction.
        Returns None if the buffer is not yet full.
        """
        if len(self.buffer) < 300:
            return None
            
        df = pd.DataFrame(list(self.buffer))
        
        # Feature Engineering: Replicating logic used during training in GoldProcessor
        features = {
            "rpm_avg_10s": float(df["engine_rpm"].mean()),
            "rpm_std_10s": float(df["engine_rpm"].std()),
            "throttle_avg_10s": float(df["throttle"].mean()),
            "engine_load_avg_10s": float(df["load"].mean()),
            "power_factor": float(df["engine_rpm"].iloc[-1] * df["load"].iloc[-1]),
            "speed_kmh": float(df["speed_kmh"].iloc[-1]),
            "rpm_range_10s": float(df["engine_rpm"].max() - df["engine_rpm"].min()),
            "current_gear": int(df["current_gear"].iloc[-1]),
            "load_max_10s": float(df["load"].max())
        }
        
        self.last_features = features
        return self._predict(features)

    def _predict(self, features_dict: dict):
        """
        Internal method to execute model prediction and format the result.
        """
        X = pd.DataFrame([features_dict])[FEATURE_COLUMNS]
        prob = self.model.predict_proba(X)[0]
        
        # Map model classes to human-readable output
        classes = list(self.model.classes_)
        agg_idx = classes.index("AGGRESSIVE")
        agg_prob = prob[agg_idx]
        
        return {
            "label": "AGGRESSIVE" if agg_prob > 0.5 else "NORMAL",
            "score": agg_prob * 100,
            "confidence": agg_prob if agg_prob > 0.5 else (1 - agg_prob)
        }