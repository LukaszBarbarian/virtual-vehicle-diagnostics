import os

import pyspark
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

from app.app_config import AppConfig

# Spark 3.5 ships with Scala 2.12 and Hadoop 3.3.4
SCALA_VERSION = "2.12"
HADOOP_VERSION = "3.3.4"


class SparkSessionFactory:
    """
    Factory responsible for creating and configuring SparkSession instances with Delta Lake,
    the Kafka source and (in STORAGE_MODE=azure) Azure Data Lake Gen2 connectivity.
    """

    @staticmethod
    def create(app_name: str) -> SparkSession:
        """
        Builds a SparkSession. Connector jars are resolved from Maven on first start,
        or taken from SPARK_JARS_DIR when it is set.
        """
        # Driver and executors must use the same interpreter as the application
        os.environ.setdefault("PYSPARK_PYTHON", AppConfig.PYTHON_EXEC)
        os.environ.setdefault("PYSPARK_DRIVER_PYTHON", AppConfig.PYTHON_EXEC)

        builder = (
            SparkSession.builder
            .appName(app_name)
            .master(AppConfig.SPARK_MASTER)
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .config("spark.sql.session.timeZone", "UTC")
        )

        extra_packages = []
        if AppConfig.ALL_JARS:
            builder = builder.config("spark.jars", AppConfig.ALL_JARS)
        else:
            extra_packages.append(f"org.apache.spark:spark-sql-kafka-0-10_{SCALA_VERSION}:{pyspark.__version__}")
            if AppConfig.STORAGE_MODE == "azure":
                extra_packages.append(f"org.apache.hadoop:hadoop-azure:{HADOOP_VERSION}")

        if AppConfig.STORAGE_MODE == "azure":
            account_host = f"{AppConfig.STORAGE_ACCOUNT}.dfs.core.windows.net"
            builder = (
                builder
                .config(f"spark.hadoop.fs.azure.account.auth.type.{account_host}", "SharedKey")
                .config(f"spark.hadoop.fs.azure.account.key.{account_host}", AppConfig.STORAGE_ACCOUNT_KEY)
            )

        return configure_spark_with_delta_pip(builder, extra_packages=extra_packages).getOrCreate()
