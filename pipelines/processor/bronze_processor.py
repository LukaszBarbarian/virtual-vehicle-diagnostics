from pyspark.sql.functions import col
from pyspark.sql import DataFrame
from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor

class BronzeProcessor(BaseProcessor):
    """
    Ingests raw telemetry data from Kafka and persists it to the Bronze layer.
    Focuses on data preservation and schema-on-read preparation.
    """
    def read(self) -> DataFrame:
        """
        Connects to the Kafka broker and subscribes to the raw simulation topic as a stream.
        """
        return (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", AppConfig.KAFKA_BROKERS)
            .option("subscribe", AppConfig.TOPIC_SIMULATION_RAW)
            .option("startingOffsets", "latest")
            .load()
        )
    
    def process(self, df: DataFrame) -> DataFrame:
        """
        Passes the data through without additional business logic at the Bronze stage.
        """
        return super().process(df)

    def transform(self, df: DataFrame) -> DataFrame:
        """
        Standardizes the metadata columns and casts the binary Kafka payload to a string.
        """
        return df.select(
            col("timestamp").alias("kafka_ts"),
            col("partition"),
            col("offset"),
            col("value").cast("string").alias("raw_event")
        )

    def write(self, df: DataFrame):
        """
        Saves the stream to the Bronze storage location in JSON format with checkpointing.
        """
        query = (
            df.writeStream
            .format("json")
            .outputMode("append")
            .option("path", AppConfig.BRONZE_RAW_PATH)
            .option("checkpointLocation", AppConfig.BRONZE_CHECKPOINT)
            .start()
        )
        return query