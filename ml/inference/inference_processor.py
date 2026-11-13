import collections

import mlflow.sklearn
import pandas as pd

from app.app_config import AppConfig
from ml.datasets.feature_config import FEATURE_COLUMNS, POSITIVE_CLASS, WINDOW_ROWS
from ml.tracking.mlflow_setup import configure_mlflow


def compute_window_features(window: pd.DataFrame) -> dict:
    """
    Computes the model features from the last WINDOW_ROWS ticks.
    Mirrors the window functions in GoldProcessor (sample std, current-tick values).
    """
    last = window.iloc[-1]
    return {
        "rpm_avg_10s": float(window["engine_rpm"].mean()),
        "rpm_std_10s": float(window["engine_rpm"].std()),
        "throttle_avg_10s": float(window["throttle"].mean()),
        "engine_load_avg_10s": float(window["load"].mean()),
        "power_factor": float(last["engine_rpm"] * last["load"]),
        "speed_kmh": float(last["speed_kmh"]),
        "rpm_range_10s": float(window["engine_rpm"].max() - window["engine_rpm"].min()),
        "current_gear": int(last["current_gear"]),
        "load_max_10s": float(window["load"].max()),
    }


class AIInferenceEngine:
    """
    Real-time inference engine: keeps a sliding window of telemetry ticks and scores
    it with the driving-style model registered in MLflow.
    """

    def __init__(self, model_uri: str | None = None, model=None):
        """
        Loads the model from MLflow (or uses the one passed in, e.g. in tests).
        """
        if model is None:
            configure_mlflow()
            model = mlflow.sklearn.load_model(model_uri or AppConfig.MODEL_URI)
        self.model = model
        self.buffer = collections.deque(maxlen=WINDOW_ROWS)
        self.last_features = None

    @property
    def warmup_progress(self) -> float:
        """Share of the feature window already filled (0..1)."""
        return len(self.buffer) / WINDOW_ROWS

    def reset(self):
        """Clears the window, e.g. when a new session starts."""
        self.buffer.clear()
        self.last_features = None

    def add_sample(self, rpm: float, throttle: float, load: float, speed: float, gear: int, engine_wear: float = 0.0):
        """
        Adds one telemetry tick to the sliding window.
        """
        self.buffer.append({
            "engine_rpm": rpm,
            "throttle": throttle,
            "load": load,
            "speed_kmh": speed,
            "current_gear": gear,
            "engine_wear": engine_wear,
        })

    def observed_wear_delta(self) -> float:
        """
        Engine wear actually accumulated across the current window.
        """
        if len(self.buffer) < 2:
            return 0.0
        return self.buffer[-1]["engine_wear"] - self.buffer[0]["engine_wear"]

    def get_prediction(self):
        """
        Returns the prediction for the current window, or None until the window is full.
        """
        if len(self.buffer) < WINDOW_ROWS:
            return None

        features = compute_window_features(pd.DataFrame(list(self.buffer)))
        self.last_features = features
        return self._predict(features)

    def _predict(self, features_dict: dict):
        X = pd.DataFrame([features_dict])[FEATURE_COLUMNS]
        prob = self.model.predict_proba(X)[0]
        agg_prob = float(prob[list(self.model.classes_).index(POSITIVE_CLASS)])

        return {
            "label": POSITIVE_CLASS if agg_prob > 0.5 else "NORMAL",
            "score": agg_prob * 100,
            "confidence": agg_prob if agg_prob > 0.5 else (1 - agg_prob),
        }
