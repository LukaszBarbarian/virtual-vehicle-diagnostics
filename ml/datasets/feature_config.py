# ml/datasets/feature_config.py

FEATURE_COLUMNS = [
    "rpm_avg_30s",
    "rpm_std_30s",
    "rpm_delta_30s",

    "coolant_temp_c_avg_30s",
    "coolant_temp_c_delta_30s",

    "throttle_avg_30s",
    "throttle_std_30s",

    "wear_engine_delta_60s",
]

#TARGET_COLUMN = "engine_health_score"
TARGET_COLUMN = "engine_health_score_future"

META_COLUMNS = [
    "simulation_id",
    "step"
]
