# ml/datasets/feature_config.py

"""
Configuration file defining the schema for machine learning datasets.
Ensures consistency between GoldProcessor (feature engineering), 
MLTrainingProcessor (model training), and AIInferenceEngine (production).
"""

# Metadata used for identifying and ordering simulation snapshots
META_COLUMNS = [
    "simulation_id", 
    "step"
]

# Input features engineered from raw telemetry signals
# Includes rolling averages, standard deviations, and derived physical factors
FEATURE_COLUMNS = [
    "rpm_avg_10s",
    "rpm_std_10s",
    "throttle_avg_10s",
    "engine_load_avg_10s",
    "power_factor",
    "speed_kmh",
    "rpm_range_10s",
    "current_gear",
    "load_max_10s"
]

# The categorical classification target (e.g., NORMAL vs AGGRESSIVE)
TARGET_COLUMN = "driving_style"