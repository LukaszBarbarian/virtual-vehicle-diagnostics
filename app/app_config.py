import os

class AppConfig:
    """
    Configuration class for Kafka, Azure Data Lake, and Spark settings.
    """
    # ========================
    # KAFKA
    # ========================
    KAFKA_BROKERS = "localhost:9092"
    TOPIC_SIMULATION_RAW = "simulation.raw"

    # ========================
    # AZURE DATA LAKE
    # ========================
    STORAGE_ACCOUNT = "lsvehicle" 
    STORAGE_ACCOUNT_KEY = "VzOELlri8y/gOfCS+OMMkTC+RSPQvz6pp7H7G+VPNWq2k+46tZ3UjGR0u0KTSqlg195mWKIz7wYM+AStGx6QZQ=="

    BRONZE_CONTAINER = "bronze"
    SILVER_CONTAINER = "silver"
    GOLD_CONTAINER = "gold"

    # ========================
    # SPARK JARS CONFIGURATION
    # ========================
    JAR_PATH = "C:/spark/jars"
    
    # Fix: We use a static method or a simple loop to avoid the scope issue in class definitions
    @staticmethod
    def get_all_jars(path):
        """
        Scans the directory for .jar files and returns them as a comma-separated string.
        """
        if not os.path.exists(path):
            return ""
        return ",".join([os.path.join(path, jar) for jar in os.listdir(path) if jar.endswith(".jar")])

    # Assigning the result to the class variable
    ALL_JARS = get_all_jars(JAR_PATH)

    # ========================
    # PATHS
    # ========================
    BRONZE_RAW_PATH = (
        f"abfss://{BRONZE_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/raw_events"
    )

    BRONZE_CHECKPOINT = (
        f"abfss://{BRONZE_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/checkpoints/bronze_raw"
    )

    SILVER_STATE_PATH = (
        f"abfss://{SILVER_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/vehicle_telemetry"
    )

    GOLD_FEATURES_PATH = (
        f"abfss://{GOLD_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/telemetry_features"
    )

    SILVER_QUARANTINE_PATH = f"abfss://{SILVER_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/silver_quarantine/vehicle_telemetry"
    DATA_QUALITY_METRICS_PATH = f"abfss://system@{STORAGE_ACCOUNT}.dfs.core.windows.net/data_quality_metrics"

    


    MAIN_PROFILES_PATH = "simulator/profiles"