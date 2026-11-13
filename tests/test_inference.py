import numpy as np
import pandas as pd
import pytest

from ml.datasets.feature_config import FEATURE_COLUMNS, POSITIVE_CLASS, WINDOW_ROWS
from ml.inference.inference_processor import AIInferenceEngine, compute_window_features


class FixedModel:
    """Stand-in for the MLflow model: always 80% aggressive."""
    classes_ = np.array(["NORMAL", POSITIVE_CLASS])

    def predict_proba(self, X):
        assert list(X.columns) == FEATURE_COLUMNS
        return np.array([[0.2, 0.8]])


def fill(engine, n):
    for i in range(n):
        engine.add_sample(rpm=1000 + i, throttle=0.5, load=0.3, speed=50.0, gear=3, engine_wear=i * 1e-4)


def test_features_match_the_training_schema():
    window = pd.DataFrame({
        "engine_rpm": [1000.0, 2000.0, 3000.0],
        "throttle": [0.2, 0.4, 0.6],
        "load": [0.1, 0.5, 0.3],
        "speed_kmh": [10.0, 20.0, 30.0],
        "current_gear": [1, 2, 2],
    })
    features = compute_window_features(window)

    assert list(features) == FEATURE_COLUMNS
    assert features["rpm_avg_10s"] == pytest.approx(2000.0)
    assert features["rpm_std_10s"] == pytest.approx(1000.0)  # sample std, as Spark's stddev
    assert features["power_factor"] == pytest.approx(3000.0 * 0.3)  # current tick only
    assert features["rpm_range_10s"] == pytest.approx(2000.0)
    assert features["load_max_10s"] == pytest.approx(0.5)


def test_no_prediction_until_the_window_is_full():
    engine = AIInferenceEngine(model=FixedModel())
    fill(engine, WINDOW_ROWS - 1)

    assert engine.get_prediction() is None
    assert engine.warmup_progress < 1


def test_prediction_and_observed_wear_on_a_full_window():
    engine = AIInferenceEngine(model=FixedModel())
    fill(engine, WINDOW_ROWS + 20)

    prediction = engine.get_prediction()
    assert prediction["label"] == POSITIVE_CLASS
    assert prediction["score"] == pytest.approx(80.0)
    assert len(engine.buffer) == WINDOW_ROWS
    assert engine.observed_wear_delta() == pytest.approx((WINDOW_ROWS - 1) * 1e-4)

    engine.reset()
    assert engine.get_prediction() is None
