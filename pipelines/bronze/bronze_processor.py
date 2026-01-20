from pyspark.sql.functions import col
from app.app_config import AppConfig
from pipelines.base.processor import BaseProcessor


class BronzeProcessor(BaseProcessor):
    def read(self):
        return (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", AppConfig.KAFKA_BROKERS)
            .option("subscribe", AppConfig.TOPIC_SIMULATION_RAW)
            .option("startingOffsets", "earliest")
            .load()
        )
    
    def process(self, df):
        return super().process(df)

    def transform(self, df):
        return df.select(
            col("timestamp").alias("kafka_ts"),
            col("partition"),
            col("offset"),
            col("value").cast("string").alias("raw_event")
        )

    def write(self, df):
        (
            df.writeStream
            .format("json")
            .outputMode("append")
            .option("path", AppConfig.BRONZE_RAW_PATH)
            .option("checkpointLocation", AppConfig.BRONZE_CHECKPOINT)
            .start()
        )
