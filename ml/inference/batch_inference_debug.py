from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mlflow
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from app.app_config import AppConfig
from infra.spark.spark_session import SparkSessionFactory
from ml.datasets.feature_config import FEATURE_COLUMNS



# --------------------------------------------------
# 1. Spark
# --------------------------------------------------
spark = SparkSessionFactory.create("ml-batch-inference-debug")

# --------------------------------------------------
# 2. Load GOLD
# --------------------------------------------------
gold_df = (
    spark.read
    .format("delta")
    .load(AppConfig.GOLD_FEATURES_PATH)
)

# wybierz JEDNĄ symulację (bardzo ważne!)
simulation_id = (
    gold_df
    .select("simulation_id")
    .limit(1)
    .collect()[0][0]
)

df = (
    gold_df
    .filter(f"simulation_id = '{simulation_id}'")
    .orderBy("step")
    .select(
        "step",
        "engine_health_score",
        *FEATURE_COLUMNS
    )
)

# --------------------------------------------------
# 3. Collect to driver (DEBUG ONLY)
# --------------------------------------------------
rows = df.collect()

X = np.array(
    [[row[c] for c in FEATURE_COLUMNS] for row in rows],
    dtype=float
)

true_health = np.array(
    [row["engine_health_score"] for row in rows],
    dtype=float
)

steps = [row["step"] for row in rows]

# --------------------------------------------------
# 4. Load model from MLflow
# --------------------------------------------------
model = mlflow.sklearn.load_model(
    "runs:/3150a7503fef49519c3834fd5d926172/model"
)

predicted_health = model.predict(X)

# --------------------------------------------------
# 5. Plot (FUTURE-AWARE)
# --------------------------------------------------
N = 30  # MUSI być identyczne jak PREDICTION_HORIZON w GOLD

plt.figure(figsize=(14, 6))

# True health (t)
plt.plot(
    steps,
    true_health,
    label="True health (heuristic)",
    linewidth=2
)

# Predicted future health (t+N) — PRZESUNIĘCIE
plt.plot(
    steps[N:],                 # oś czasu przesunięta
    predicted_health[:-N],     # obcięty ogon
    label=f"Predicted health (t+{N})",
    linestyle="--",
    linewidth=2
)

# warning zones
plt.axhspan(70, 100, color="green", alpha=0.1)
plt.axhspan(40, 70, color="orange", alpha=0.1)
plt.axhspan(0, 40, color="red", alpha=0.1)

plt.xlabel("Simulation step")
plt.ylabel("Engine health score")
plt.title("Engine health: heuristic vs ML future prediction")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
