from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
import os
from app.app_config import AppConfig

class SparkSessionFactory:
    """
    Factory responsible for creating and configuring SparkSession instances.
    Supports both local development and cloud integration with Delta Lake and Azure Storage.
    """

    @staticmethod
    def create(app_name: str) -> SparkSession:
        """
        Builds a SparkSession with Delta Lake extensions and required cloud storage configurations.
        Environment variable SPARK_MODE determines the execution context.
        """
        mode = os.getenv("SPARK_MODE", "local")
        builder = SparkSession.builder.appName(app_name)

        if mode == "local":
            builder = (
                builder
                .master("local[*]")
                .config("spark.jars", AppConfig.ALL_JARS)
                
                # Ensure Python environment consistency across Driver and Executors
                .config("spark.executorEnv.PYSPARK_PYTHON", AppConfig.PYTHON_EXEC)
                .config("spark.executorEnv.PYSPARK_DRIVER_PYTHON", AppConfig.PYTHON_EXEC)

                # Azure Data Lake Storage (ADLS) connectivity using Shared Key authentication
                .config(
                    f"fs.azure.account.key.{AppConfig.STORAGE_ACCOUNT}.dfs.core.windows.net",
                    AppConfig.STORAGE_ACCOUNT_KEY
                )
                .config(
                    f"spark.hadoop.fs.azure.account.auth.type.{AppConfig.STORAGE_ACCOUNT}.dfs.core.windows.net",
                    "SharedKey"
                )
            )

        # Apply common configurations for Delta Lake support
        builder = (
            builder
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        )

        # Finalize the session with Delta Lake pip dependencies
        spark = configure_spark_with_delta_pip(builder).getOrCreate()

        return spark