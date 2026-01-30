from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
import os

from app.app_config import AppConfig


class SparkSessionFactory:

    @staticmethod
    def create(app_name: str) -> SparkSession:
        mode = os.getenv("SPARK_MODE", "local")

        builder = SparkSession.builder.appName(app_name)

        if mode == "local":
            builder = (
                builder
                .master("local[*]")
                .config("spark.jars", AppConfig.ALL_JARS)

                # # 🔑 PYTHON – DRIVER
                # .config("spark.pyspark.python", AppConfig.PYTHON_EXEC)
                # .config("spark.pyspark.driver.python", AppConfig.PYTHON_EXEC)

                # 🔑 PYTHON – EXECUTORS (BRAKUJĄCE!)
                .config("spark.executorEnv.PYSPARK_PYTHON", AppConfig.PYTHON_EXEC)
                .config("spark.executorEnv.PYSPARK_DRIVER_PYTHON", AppConfig.PYTHON_EXEC)

                # Azure ADLS
                .config(
                    f"fs.azure.account.key.{AppConfig.STORAGE_ACCOUNT}.dfs.core.windows.net",
                    AppConfig.STORAGE_ACCOUNT_KEY
                )
                .config(
                    "spark.hadoop.fs.azure.account.auth.type."
                    + AppConfig.STORAGE_ACCOUNT
                    + ".dfs.core.windows.net",
                    "SharedKey"
                )
            )

        # COMMON (local + cloud)
        builder = (
            builder
            .config(
                "spark.sql.extensions",
                "io.delta.sql.DeltaSparkSessionExtension"
            )
            .config(
                "spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog"
            )
        )

        spark = configure_spark_with_delta_pip(builder).getOrCreate()

        print(
            f"✅ SparkSession ready | mode={mode} | spark={spark.version}"
        )

        # 🔍 Debug – warto zostawić na chwilę
        print("Driver python:", spark.sparkContext.getConf().get("spark.pyspark.driver.python"))
        print("Executor python:", spark.sparkContext.getConf().get("spark.executorEnv.PYSPARK_PYTHON"))

        return spark
