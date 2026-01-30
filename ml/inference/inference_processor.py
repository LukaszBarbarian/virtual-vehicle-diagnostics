import collections
import numpy as np
import pandas as pd
import mlflow.sklearn
from ml.datasets.feature_config import FEATURE_COLUMNS

class AIInferenceEngine:
    def __init__(self, run_id):
        # Upewnij się, że tracking_uri jest ustawiony, jeśli wywala błąd
        model_uri = f"runs:/{run_id}/model"
        self.model = mlflow.sklearn.load_model(model_uri)
        self.buffer = collections.deque(maxlen=300) # 10s przy 30Hz

    def add_sample(self, rpm, throttle, load, speed, gear):
        """Dodaje pojedynczy tick danych do bufora."""
        self.buffer.append({
            "engine_rpm": rpm, "throttle": throttle, "load": load, 
            "speed_kmh": speed, "current_gear": gear
        })

    def get_prediction(self):
        if len(self.buffer) < 300: return None
        df = pd.DataFrame(list(self.buffer))
        
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

    def _predict(self, features_dict):
        """Metoda pomocnicza wykonująca samą predykcję na słowniku cech."""
        X = pd.DataFrame([features_dict])[FEATURE_COLUMNS]
        prob = self.model.predict_proba(X)[0]
        
        # Mapowanie klas modelu
        classes = list(self.model.classes_)
        agg_idx = classes.index("AGGRESSIVE")
        agg_prob = prob[agg_idx]
        
        return {
            "label": "AGGRESSIVE" if agg_prob > 0.5 else "NORMAL",
            "score": agg_prob * 100,
            "confidence": agg_prob if agg_prob > 0.5 else (1 - agg_prob)
        }