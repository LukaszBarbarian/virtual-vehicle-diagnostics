import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class AppConfig:
    """
    Configuration class for Kafka, Azure Data Lake, and Spark settings.
    Uses environment variables for sensitive data.
    """

    PYTHON_EXEC = os.getenv("PYTHON_INTERPRETER", "python")

    # ========================
    # KAFKA
    # ========================
    KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092")
    TOPIC_SIMULATION_RAW = "simulation.raw"

    # ========================
    # AZURE DATA LAKE
    # ========================
    STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
    STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_KEY")

    BRONZE_CONTAINER = "bronze"
    SILVER_CONTAINER = "silver"
    GOLD_CONTAINER = "gold"
    ML_CONTAINER = "mldatasets"

    # ========================
    # SPARK JARS CONFIGURATION
    # ========================
    JAR_PATH = os.getenv("SPARK_JARS_DIR", "C:/spark/jars")
    
    @staticmethod
    def get_all_jars(path):
        """Scans the directory for .jar files for Spark session."""
        if not os.path.exists(path):
            return ""
        return ",".join([os.path.join(path, jar) for jar in os.listdir(path) if jar.endswith(".jar")])

    ALL_JARS = get_all_jars(JAR_PATH)

    # ========================
    # DYNAMIC PATHS (ABFSS)
    # ========================
    BASE_URL = f"@{STORAGE_ACCOUNT}.dfs.core.windows.net"

    BRONZE_RAW_PATH = f"abfss://{BRONZE_CONTAINER}{BASE_URL}/raw_events"
    BRONZE_CHECKPOINT = f"abfss://{BRONZE_CONTAINER}{BASE_URL}/checkpoints/bronze_raw"

    SILVER_STATE_PATH = f"abfss://{SILVER_CONTAINER}{BASE_URL}/vehicle_telemetry"
    SILVER_QUARANTINE_PATH = f"abfss://{SILVER_CONTAINER}{BASE_URL}/silver_quarantine/vehicle_telemetry"

    GOLD_FEATURES_PATH = f"abfss://{GOLD_CONTAINER}{BASE_URL}/telemetry_features"

    ML_DATASETS_BASE_PATH = f"abfss://{ML_CONTAINER}{BASE_URL}/"
    ML_DATASET_FULL_PATH  = f"{ML_DATASETS_BASE_PATH}full"
    ML_DATASET_TRAIN_PATH = f"{ML_DATASETS_BASE_PATH}train"
    ML_DATASET_TEST_PATH  = f"{ML_DATASETS_BASE_PATH}test"
    ML_DATASET_META_PATH  = f"{ML_DATASETS_BASE_PATH}metadata"
    ML_TRAINING_METRICS_PATH = f"{ML_DATASETS_BASE_PATH}training/metrics"

    DATA_QUALITY_METRICS_PATH = f"abfss://system{BASE_URL}/data_quality_metrics"
    MAIN_PROFILES_PATH = "simulator/profiles"