import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load variables from the project's .env file (if present), regardless of the working directory
load_dotenv(PROJECT_ROOT / ".env")


def _list_jars(path: str) -> str:
    """Returns a comma-separated list of .jar files in the directory (used for offline Spark setups)."""
    if not path or not os.path.isdir(path):
        return ""
    return ",".join(os.path.join(path, jar) for jar in os.listdir(path) if jar.endswith(".jar"))


class AppConfig:
    """
    Central configuration for Kafka, the data lake (local disk or Azure Data Lake Gen2), Spark and MLflow.
    Every value can be overridden with an environment variable (see .env.example).
    """

    PROJECT_ROOT = PROJECT_ROOT
    PYTHON_EXEC = os.getenv("PYTHON_INTERPRETER", sys.executable)

    # ========================
    # KAFKA
    # ========================
    KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092")
    TOPIC_SIMULATION_RAW = "simulation.raw"
    TOPIC_DRIVER_COMMANDS = "driver.commands"

    # ========================
    # DATA LAKE
    # ========================
    # "local" writes the medallion layers to LOCAL_LAKE_DIR; "azure" writes to ADLS Gen2 over abfss://
    STORAGE_MODE = os.getenv("STORAGE_MODE", "local").lower()
    LOCAL_LAKE_DIR = Path(os.getenv("LOCAL_LAKE_DIR", PROJECT_ROOT / "data" / "lake")).resolve()

    STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
    STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_KEY")

    BRONZE_CONTAINER = "bronze"
    SILVER_CONTAINER = "silver"
    GOLD_CONTAINER = "gold"
    ML_CONTAINER = "mldatasets"
    SYSTEM_CONTAINER = "system"

    # ========================
    # SPARK
    # ========================
    SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")
    # Optional: a directory of pre-downloaded jars for machines without internet access to Maven
    ALL_JARS = _list_jars(os.getenv("SPARK_JARS_DIR", ""))

    # ========================
    # MLFLOW
    # ========================
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}")
    MLFLOW_ARTIFACT_DIR = PROJECT_ROOT / "mlruns"
    MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "driving_style")
    MODEL_NAME = "driving_style_classifier"
    # Model served by the cockpit; defaults to the latest registered version
    MODEL_URI = os.getenv("MODEL_URI", f"models:/{MODEL_NAME}/latest")

    # ========================
    # SIMULATOR
    # ========================
    MAIN_PROFILES_PATH = PROJECT_ROOT / "simulator" / "profiles"
    DEFAULT_CAR_PROFILE = MAIN_PROFILES_PATH / "cars" / "ford_focus.yaml"
    DEFAULT_DRIVER_PROFILE = MAIN_PROFILES_PATH / "drivers" / "normal.yaml"
    WEAR_PROFILE = MAIN_PROFILES_PATH / "worlds" / "realistic_wear.yaml"
    ENVIRONMENT_PROFILE = MAIN_PROFILES_PATH / "worlds" / "summer.yaml"

    @classmethod
    def lake_root(cls, container: str) -> str:
        """Returns the root URI of a lake container for the configured storage mode."""
        if cls.STORAGE_MODE == "azure":
            if not cls.STORAGE_ACCOUNT:
                raise RuntimeError("STORAGE_MODE=azure requires AZURE_STORAGE_ACCOUNT and AZURE_STORAGE_KEY")
            return f"abfss://{container}@{cls.STORAGE_ACCOUNT}.dfs.core.windows.net"
        if cls.STORAGE_MODE != "local":
            raise RuntimeError(f"Unknown STORAGE_MODE '{cls.STORAGE_MODE}' (expected 'local' or 'azure')")
        return (cls.LOCAL_LAKE_DIR / container).as_uri()

    @classmethod
    def lake_path(cls, container: str, *parts: str) -> str:
        return "/".join([cls.lake_root(container), *parts])


class LakePaths:
    """Resolved storage locations of every medallion and ML dataset."""

    BRONZE_RAW_PATH = AppConfig.lake_path(AppConfig.BRONZE_CONTAINER, "raw_events")
    BRONZE_CHECKPOINT = AppConfig.lake_path(AppConfig.BRONZE_CONTAINER, "checkpoints", "bronze_raw")

    SILVER_STATE_PATH = AppConfig.lake_path(AppConfig.SILVER_CONTAINER, "vehicle_telemetry")
    SILVER_QUARANTINE_PATH = AppConfig.lake_path(AppConfig.SILVER_CONTAINER, "silver_quarantine", "vehicle_telemetry")

    GOLD_FEATURES_PATH = AppConfig.lake_path(AppConfig.GOLD_CONTAINER, "telemetry_features")

    ML_DATASET_FULL_PATH = AppConfig.lake_path(AppConfig.ML_CONTAINER, "full")
    ML_DATASET_TRAIN_PATH = AppConfig.lake_path(AppConfig.ML_CONTAINER, "train")
    ML_DATASET_TEST_PATH = AppConfig.lake_path(AppConfig.ML_CONTAINER, "test")

    DATA_QUALITY_METRICS_PATH = AppConfig.lake_path(AppConfig.SYSTEM_CONTAINER, "data_quality_metrics")
