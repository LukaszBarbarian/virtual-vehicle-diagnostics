import mlflow.sklearn
import pandas as pd
from ml.datasets.feature_config import FEATURE_COLUMNS


class DriverCoachingEngine:
    def __init__(self, model_uri: str):
        self.model = mlflow.sklearn.load_model(model_uri)
        self.has_proba = hasattr(self.model, "predict_proba")

    def evaluate(self, features_dict: dict):
        X = pd.DataFrame(
            [[features_dict[c] for c in FEATURE_COLUMNS]],
            columns=FEATURE_COLUMNS
        )

        # 🔥 predict() zwraca LABEL, nie ID
        label = self.model.predict(X)[0]

        if self.has_proba:
            confidence = float(self.model.predict_proba(X).max())
        else:
            confidence = 1.0

        # Normalizujemy label (na wszelki wypadek)
        label = str(label).upper()

        return label, confidence

