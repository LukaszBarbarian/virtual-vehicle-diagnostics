# ml/datasets/feature_config.py

"""
Single definition of the ML dataset schema and of the feature window.
Shared by GoldProcessor (training features), MLTrainingProcessor and AIInferenceEngine
(live features), so that both sides compute exactly the same inputs.
"""

# Simulation clock: the cockpit steps the physics every 0.1 s
TICKS_PER_SEC = 10
SIM_DT = 1.0 / TICKS_PER_SEC

# Rolling feature window: the current tick plus the previous 10 seconds
WINDOW_SEC = 10
WINDOW_LAG = WINDOW_SEC * TICKS_PER_SEC
WINDOW_ROWS = WINDOW_LAG + 1

# Share of ticks labelled AGGRESSIVE: ticks above this percentile of the engine wear rate
# accumulated over the same 10-second window the features describe
AGGRESSIVE_PERCENTILE = 0.75

# Metadata used for identifying and ordering simulation snapshots
META_COLUMNS = [
    "simulation_id",
    "step"
]

# Input features engineered from raw telemetry signals
FEATURE_COLUMNS = [
    "rpm_avg_10s",
    "rpm_std_10s",
    "throttle_avg_10s",
    "engine_load_avg_10s",
    "power_factor",
    "speed_kmh",
    "rpm_range_10s",
    "current_gear",
    "load_max_10s",
    "rpm_max_10s",
    "oil_temp_c"
]

# The categorical classification target (NORMAL vs AGGRESSIVE)
TARGET_COLUMN = "driving_style"
POSITIVE_CLASS = "AGGRESSIVE"

# Share of sessions used for training; the rest are test sessions
TRAIN_RATIO = 0.8


def split_simulation_ids(simulation_ids, train_ratio: float = TRAIN_RATIO) -> tuple[set, set]:
    """
    Deterministic group split: whole sessions go to train or test, never single rows,
    so no session leaks between the two sets. Shared by MLSplitProcessor and the dashboard.
    """
    ids = sorted(set(simulation_ids))
    if len(ids) < 2:
        return set(ids), set(ids)
    split_idx = max(1, int(len(ids) * train_ratio))
    return set(ids[:split_idx]), set(ids[split_idx:])
