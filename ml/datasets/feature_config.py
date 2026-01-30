# ml/datasets/feature_config.py

META_COLUMNS = ["simulation_id", "step"]

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

TARGET_COLUMN = "driving_style"